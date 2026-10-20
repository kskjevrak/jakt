"""Fetch property parcels (Matrikkelen – Eiendomskart Teig) for the hunting ground.

Route order:
  1. Kartverket "Eiendom REST-API for lokalisering" to validate every gnr/bnr and
     get the representation point of every teig (also detached ones).
  2. Kartverket WFS "Matrikkelen - Eiendomskart Teig WFS" (WFS 2.0.0, GML 3.2),
     bbox around all teig points + margin, kommune 4220.
  3. Fallback: Geonorge Atom feed (kommune file for Bygland, EPSG:25833).

Output: raw/teig/teiger_bbox.geojson (EPSG:25833) with one feature per teig and
attributes kommunenummer, matrikkelnummer, gnr, bnr, fnr list, bruksnavn,
flere_matrikkelenheter, teig_id, areal_m2.
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import unary_union

from common import (
    RAW, KOMMUNE, KOMMUNENAVN, MATRIKKEL, SourceReport, download_file, http_get_json, log, parse_args, DAY,
)

WFS = "https://wfs.geonorge.no/skwms1/wfs.matrikkelen-eiendomskart-teig"
REST = "https://api.kartverket.no/eiendom/v1/geokoding"
ATOM = "https://nedlasting.geonorge.no/geonorge/ATOM-feeds/MatrikkelenEiendomskartTeig_AtomFeedGML.xml"
ATOM_ZIP = (
    "https://nedlasting.geonorge.no/geonorge/Basisdata/MatrikkelenEiendomskartTeig/GML/"
    f"Basisdata_{KOMMUNE}_{KOMMUNENAVN}_25833_MatrikkelenEiendomskartTeig_GML.zip"
)
OUT = RAW / "teig"
MARGIN_M = 2500  # around the union of all teig points; must exceed 500 m neighbour buffer

GML = "{http://www.opengis.net/gml/3.2}"


def rest_points(report: SourceReport, force: bool) -> list[dict]:
    """Validate gnr/bnr via REST and return all teig points (EPSG:25833)."""
    pts: list[dict] = []
    for gnr, bnr in MATRIKKEL:
        mnr = f"{KOMMUNE}-{gnr}/{bnr}"
        dest = OUT / f"eiendom_{gnr}_{bnr}.json"
        try:
            download_file(REST, dest, params={"matrikkelnummer": mnr, "omrade": "false", "utkoordsys": "25833"},
                          max_age=1 * DAY, force=force, resume=False)
            d = json.loads(dest.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            report.attempt("REST", f"{REST}?matrikkelnummer={mnr}", False, str(e))
            raise SystemExit(f"STOPP: Eiendom REST-API feilet for {mnr}: {e}")
        feats = d.get("features", [])
        own = [f for f in feats if f["properties"].get("festenummer", 0) == 0 and f["properties"].get("seksjonsnummer", 0) == 0]
        if not own:
            report.attempt("REST", f"{REST}?matrikkelnummer={mnr}", False, "ingen teig funnet")
            raise SystemExit(f"STOPP: {mnr} finnes ikke i matrikkelen (ingen teig returnert). Sjekk gnr/bnr.")
        report.attempt("REST", f"{REST}?matrikkelnummer={mnr}", True,
                       f"{len(own)} teig(er) for {gnr}/{bnr}, {len(feats) - len(own)} feste/seksjon-teig(er)")
        for f in feats:
            p = f["properties"]
            x, y = f["geometry"]["coordinates"]
            pts.append({"gnr": p["gardsnummer"], "bnr": p["bruksnummer"], "fnr": p.get("festenummer", 0),
                        "snr": p.get("seksjonsnummer", 0), "x": x, "y": y, "lokalid": p.get("lokalid"),
                        "hovedomrade": p.get("hovedområde"), "tekst": p.get("matrikkelnummertekst"),
                        "oppdatert": p.get("oppdateringsdato")})
    (OUT / "eiendom_punkter.json").write_text(json.dumps(pts, indent=1, ensure_ascii=False), encoding="utf-8")
    return pts


def bbox_of(pts: list[dict], margin: float) -> tuple[float, float, float, float]:
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    return min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin


# ---------------------------------------------------------------- GML parsing
def _ring_coords(ring: ET.Element) -> list[tuple[float, float]]:
    txt = " ".join(e.text or "" for e in ring.iter() if e.tag in (GML + "posList", GML + "pos"))
    vals = [float(v) for v in txt.split()]
    coords = list(zip(vals[0::2], vals[1::2]))
    # deegree serves easting first for EPSG:25833, but guard against N,E order
    if coords and coords[0][0] > 1_000_000 and coords[0][1] < 1_000_000:
        coords = [(y, x) for x, y in coords]
    return coords


def _polygons(elem: ET.Element) -> list[Polygon]:
    polys = []
    for patch in list(elem.iter(GML + "PolygonPatch")) + list(elem.iter(GML + "Polygon")):
        ext = patch.find(GML + "exterior")
        if ext is None:
            continue
        shell = _ring_coords(ext)
        holes = [_ring_coords(i) for i in patch.findall(GML + "interior")]
        if len(shell) >= 4:
            polys.append(Polygon(shell, [h for h in holes if len(h) >= 4]))
    return polys


def parse_teig_gml(path: Path) -> list[dict]:
    """Parse deegree/Geonorge Teig GML (3.2) into feature dicts with shapely geometry."""
    feats = []
    with open(path, "rb") as fh:
        for _, el in ET.iterparse(fh, events=("end",)):
            if not el.tag.endswith("}Teig"):
                continue
            ns = el.tag[: el.tag.index("}") + 1]
            g = lambda name, e=el: (e.findtext(f".//{ns}{name}") or "").strip()  # noqa: E731
            omr = el.find(f"{ns}område")
            polys = _polygons(omr) if omr is not None else []
            if not polys:
                el.clear()
                continue
            geom = polys[0] if len(polys) == 1 else MultiPolygon(polys)
            me = []
            for m in el.iter(f"{ns}Matrikkelenhet"):
                try:
                    me.append({
                        "gnr": int(m.findtext(f"{ns}gardsnummer") or 0),
                        "bnr": int(m.findtext(f"{ns}bruksnummer") or 0),
                        "fnr": int(m.findtext(f"{ns}festenummer") or 0),
                        "snr": int(m.findtext(f"{ns}seksjonsnummer") or 0),
                        "bruksnavn": (m.findtext(f"{ns}bruksnavn") or "").strip(),
                        "type": (m.findtext(f"{ns}matrikkelenhetstype") or "").strip(),
                    })
                except ValueError:
                    pass
            areal = g("lagretBeregnetAreal")
            feats.append({
                "geometry": geom,
                "teig_id": g("teigId") or el.get(GML + "id"),
                "kommunenummer": g("kommunenummer"),
                "matrikkelnummer": g("matrikkelnummerTekst"),
                "flere_matrikkelenheter": g("teigMedFlereMatrikkelenheter") == "true",
                "tvist": g("tvist") == "true",
                "uregistrert_jordsameie": g("uregistrertJordsameie") == "true",
                "matrikkelenheter": me,
                "bruksnavn": me[0]["bruksnavn"] if me else "",
                "areal_m2": float(areal) if areal else None,
                "oppdatert": g("oppdateringsdato"),
            })
            el.clear()
    return feats


def write_geojson(feats: list[dict], dest: Path) -> None:
    fc = {"type": "FeatureCollection",
          "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::25833"}},
          "features": []}
    for f in feats:
        props = {k: v for k, v in f.items() if k != "geometry"}
        fc["features"].append({"type": "Feature", "properties": props, "geometry": mapping(f["geometry"])})
    dest.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")


def fetch_wfs(bbox, report: SourceReport, force: bool) -> list[dict]:
    dest = OUT / "teig_wfs.gml"
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "app:Teig",
        "srsName": "urn:ogc:def:crs:EPSG::25833",
        "bbox": f"{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f},urn:ogc:def:crs:EPSG::25833",
    }
    download_file(WFS, dest, params=params, max_age=1 * DAY, force=force, resume=False, timeout=600)
    head = dest.read_bytes()[:400]
    if b"ExceptionReport" in head:
        raise RuntimeError(dest.read_text(encoding="utf-8")[:300])
    feats = [f for f in parse_teig_gml(dest) if f["kommunenummer"] == KOMMUNE]
    if not feats:
        raise RuntimeError("WFS returnerte ingen teiger i bbox")
    report.attempt("WFS", WFS + "?service=WFS&version=2.0.0&request=GetFeature&typeNames=app:Teig&bbox=...", True,
                   f"{len(feats)} teiger i bbox {tuple(round(v) for v in bbox)}")
    report.add_file(dest)
    return feats


def fetch_atom(bbox, report: SourceReport, force: bool) -> list[dict]:
    feed = download_file(ATOM, OUT / "atom_feed.xml", max_age=1 * DAY, force=force, resume=False)
    if ATOM_ZIP not in feed.read_text(encoding="utf-8", errors="replace"):
        raise RuntimeError("fant ikke kommunefil for 4220/25833 i Atom-feeden")
    z = download_file(ATOM_ZIP, OUT / ATOM_ZIP.rsplit("/", 1)[-1], max_age=7 * DAY, force=force)
    with zipfile.ZipFile(z) as zf:
        gml_name = next(n for n in zf.namelist() if n.lower().endswith(".gml"))
        gml_path = OUT / "teig_atom.gml"
        gml_path.write_bytes(zf.read(gml_name))
    from shapely.geometry import box
    b = box(*bbox)
    feats = [f for f in parse_teig_gml(gml_path) if f["geometry"].intersects(b)]
    report.attempt("Atom", ATOM_ZIP, True, f"{len(feats)} teiger i bbox fra kommunefil")
    report.add_file(z)
    return feats


def main(force: bool = False) -> SourceReport:
    OUT.mkdir(parents=True, exist_ok=True)
    report = SourceReport(
        name="Matrikkelen – Eiendomskart Teig",
        dataset="Kartverket, uuid 74340c24-1c8a-4454-b813-bfe498e80f16 (daglig oppdatert)",
        license="CC BY 4.0",
    )
    pts = rest_points(report, force)
    bbox = bbox_of(pts, MARGIN_M)
    feats: list[dict] = []
    try:
        feats = fetch_wfs(bbox, report, force)
        report.route_used = "WFS (Kartverket) + REST-validering"
    except Exception as e:  # noqa: BLE001
        report.attempt("WFS", WFS, False, str(e)[:200])
        log(f"WFS feilet ({e}); prøver Atom-feed")
        feats = fetch_atom(bbox, report, force)
        report.route_used = "Atom feed (kommunefil) + REST-validering"
    write_geojson(feats, OUT / "teiger_bbox.geojson")
    (OUT / "bbox.json").write_text(json.dumps({"minx": bbox[0], "miny": bbox[1], "maxx": bbox[2], "maxy": bbox[3],
                                              "crs": "EPSG:25833"}), encoding="utf-8")
    report.version = max((f["oppdatert"] for f in feats if f["oppdatert"]), default="")
    report.notes.append(f"{len(pts)} teigpunkter fra REST for {len(MATRIKKEL)} matrikkelenheter; "
                        f"{len(feats)} teiger lastet i bbox med {MARGIN_M} m margin.")
    report.ok = True
    return report


if __name__ == "__main__":
    a = parse_args()
    r = main(force=a["force"])
    print(json.dumps(r.to_dict(), indent=1, ensure_ascii=False, default=str)[:3000])
