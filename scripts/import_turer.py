"""Importer GPS-spor (GPX fra Garmin Connect eller andre) til data/turer.geojson, laget «Gått» i nettsiden.

  python scripts/import_turer.py                       # alle logg/turer/*.gpx -> data/turer.geojson
  python scripts/import_turer.py --tabell              # bare vis tabellen, ikke skriv
  python scripts/import_turer.py "logg/turer/*.gpx" --toleranse 6

Hvert spor blir én LineString i WGS84 med [lon, lat, høyde] per punkt, forenklet med Douglas–Peucker (standard 6 m)
så filen holder seg liten nok for repoet. Tidsstempel per beholdt punkt ligger i properties.tider_s (sekunder fra start),
slik at nettsiden kan foreslå dato og klokkeslett når du klikker inn en observasjon på sporet.
Km og høydemeter regnes på det fulle sporet før forenkling. Rådataene i logg/turer/ er gitignored; bare den
forenklede filen går i repoet. Scriptet bygger filen på nytt fra alle GPX-filene hver gang, så det er trygt å kjøre om igjen.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import re
import statistics as st
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OSLO = ZoneInfo("Europe/Oslo")
NS = {"g": "http://www.topografix.com/GPX/1/1"}
LAT0 = 58.785
KX, KY = 111320 * math.cos(math.radians(LAT0)), 110574  # metres per degree at the hunting ground


def les_gpx(fn: Path) -> list[dict]:
    """Return one dict per <trk> with name and the full point list [(lon, lat, ele, time), ...]."""
    root = ET.parse(fn).getroot()
    ut = []
    for trk in root.findall("g:trk", NS) or root.findall("trk"):
        navn = (trk.findtext("g:name", default="", namespaces=NS) or "").strip()
        pts = []
        for seg in trk.findall("g:trkseg", NS):
            for p in seg.findall("g:trkpt", NS):
                lat, lon = float(p.get("lat")), float(p.get("lon"))
                ele = p.findtext("g:ele", default=None, namespaces=NS)
                tid = p.findtext("g:time", default=None, namespaces=NS)
                t = datetime.fromisoformat(tid.replace("Z", "+00:00")) if tid else None
                pts.append((lon, lat, float(ele) if ele is not None else None, t))
        if len(pts) >= 2:
            ut.append({"navn": navn, "pts": pts})
    return ut


def xy(p):
    return (p[0] * KX, p[1] * KY)


def douglas_peucker(pts: list[tuple[float, float]], tol: float) -> list[int]:
    """Indices to keep, iterative so long tracks do not hit the recursion limit."""
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        best, bi = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if L2 == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
                d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if d > best:
                best, bi = d, i
        if best > tol:
            keep[bi] = True
            stack.append((a, bi))
            stack.append((bi, b))
    return [i for i, k in enumerate(keep) if k]


def hoydemeter(eles: list[float | None], terskel: float = 3.0) -> tuple[float, float]:
    """Ascent and descent with a 5-point median filter and a hysteresis threshold, so GPS noise does not add up."""
    e = [v for v in eles if v is not None]
    if len(e) < 3:
        return 0.0, 0.0
    glatt = [st.median(e[max(0, i - 2): i + 3]) for i in range(len(e))]
    opp = ned = 0.0
    ref = glatt[0]
    for v in glatt[1:]:
        if v - ref >= terskel:
            opp += v - ref
            ref = v
        elif ref - v >= terskel:
            ned += ref - v
            ref = v
    return opp, ned


def last_jaktfelt():
    try:
        from shapely.geometry import shape
        from shapely.ops import unary_union
        from shapely.prepared import prep
        fc = json.loads((DATA / "jaktfelt.geojson").read_text(encoding="utf-8"))
        return prep(unary_union([shape(f["geometry"]) for f in fc["features"]]))
    except Exception:  # noqa: BLE001 - shapely or the file missing only drops one column
        return None


def bygg_feature(fn: Path, trk: dict, tol: float, jaktfelt) -> dict:
    pts = trk["pts"]
    m = [xy(p) for p in pts]
    km = sum(math.hypot(m[i][0] - m[i - 1][0], m[i][1] - m[i - 1][1]) for i in range(1, len(m))) / 1000
    opp, ned = hoydemeter([p[2] for p in pts])
    tider = [p[3] for p in pts if p[3] is not None]
    t0, t1 = (tider[0], tider[-1]) if tider else (None, None)
    keep = douglas_peucker(m, tol)
    coords = []
    tider_s = []
    for i in keep:
        lon, lat, ele, t = pts[i]
        coords.append([round(lon, 5), round(lat, 5)] + ([round(ele)] if ele is not None else []))
        tider_s.append(round((t - t0).total_seconds()) if (t is not None and t0 is not None) else None)
    # elevation on every vertex or none, so the LineString stays uniform
    if any(len(c) == 2 for c in coords):
        coords = [c[:2] for c in coords]
    inne = None
    if jaktfelt is not None:
        from shapely.geometry import Point
        n_in = sum(1 for c in coords if jaktfelt.contains(Point(c[0], c[1])))
        inne = round(100 * n_in / len(coords))
    mid = re.search(r"activity_(\d+)", fn.name)
    eles = [p[2] for p in pts if p[2] is not None]
    lokal = lambda t: t.astimezone(OSLO) if t else None  # noqa: E731
    props = {
        "id": f"tur-{mid.group(1)}" if mid else f"tur-{fn.stem}",
        "navn": trk["navn"] or fn.stem,
        "dato": lokal(t0).strftime("%Y-%m-%d") if t0 else None,
        "start": lokal(t0).strftime("%H:%M") if t0 else None,
        "slutt": lokal(t1).strftime("%H:%M") if t1 else None,
        "varighet_min": round((t1 - t0).total_seconds() / 60) if t0 and t1 else None,
        "km": round(km, 1),
        "hoydemeter_opp": round(opp),
        "hoydemeter_ned": round(ned),
        "hoyde_min": round(min(eles)) if eles else None,
        "hoyde_maks": round(max(eles)) if eles else None,
        "punkter": len(pts),
        "punkter_forenklet": len(coords),
        "andel_i_jaktfelt_pst": inne,
        "kilde": "Garmin Connect" if "garmin" in fn.read_text(encoding="utf-8", errors="ignore")[:600].lower() else "GPX",
        "fil": fn.name,
        "tider_s": tider_s if all(t is not None for t in tider_s) else None,
    }
    return {"type": "Feature", "properties": props, "geometry": {"type": "LineString", "coordinates": coords}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("monster", nargs="?", default=str(ROOT / "logg" / "turer" / "*.gpx"), help="glob for GPX-filer")
    ap.add_argument("--ut", default=str(DATA / "turer.geojson"))
    ap.add_argument("--toleranse", type=float, default=6.0, help="Douglas–Peucker-toleranse i meter")
    ap.add_argument("--tabell", action="store_true", help="vis bare tabellen, ikke skriv filen")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    filer = sorted(Path(f) for f in glob.glob(a.monster))
    if not filer:
        print(f"Fant ingen GPX-filer for {a.monster}")
        return 1
    jaktfelt = last_jaktfelt()
    feats = []
    for fn in filer:
        try:
            for trk in les_gpx(fn):
                feats.append(bygg_feature(fn, trk, a.toleranse, jaktfelt))
        except ET.ParseError as e:
            print(f"Hopper over {fn.name}: kunne ikke lese XML ({e})")
    feats.sort(key=lambda f: ((f["properties"]["dato"] or ""), (f["properties"]["start"] or "")))

    print(f"{'dato':10} {'tid':11} {'km':>5} {'opp':>5} {'ned':>5} {'timer':>5} {'punkter':>13} {'i felt':>6}  navn")
    for f in feats:
        p = f["properties"]
        timer = f"{p['varighet_min'] / 60:.1f}" if p["varighet_min"] is not None else "-"
        print(f"{p['dato'] or '-':10} {(p['start'] or '-') + '–' + (p['slutt'] or '-'):11} {p['km']:5.1f} {p['hoydemeter_opp']:5d} {p['hoydemeter_ned']:5d} {timer:>5} "
              f"{p['punkter']:>6} → {p['punkter_forenklet']:<4} {str(p['andel_i_jaktfelt_pst']) + ' %' if p['andel_i_jaktfelt_pst'] is not None else '-':>6}  {p['navn']}")
    if a.tabell:
        return 0
    fc = {
        "type": "FeatureCollection",
        "metadata": {
            "_doc": [
                "Gåtte GPS-spor, laget «Gått» i nettsiden. Bygget av scripts/import_turer.py fra logg/turer/*.gpx (gitignored).",
                "Én LineString per tur i WGS84 med [lon, lat, høyde], forenklet med Douglas–Peucker. km og høydemeter er regnet på det fulle sporet.",
                "tider_s er sekunder fra start per punkt i sporet; nettsiden bruker det til å foreslå dato og klokkeslett for observasjoner som klikkes inn på sporet.",
            ],
            "generert": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "toleranse_m": a.toleranse,
            "antall": len(feats),
        },
        "features": feats,
    }
    ut = Path(a.ut)
    ut.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Skrev {ut.relative_to(ROOT) if ut.is_relative_to(ROOT) else ut} ({ut.stat().st_size // 1024} kB, {len(feats)} turer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
