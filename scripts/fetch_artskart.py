"""Fetch Artskart observations of lirype, orrfugl and storfugl for the last 15 years.

API: https://artskart.artsdatabanken.no/publicapi/api/observations/list
  * filter.taxons = Artsdatabanken TaxonId (lirype 3987, orrfugl 203489, storfugl 203484)
  * filter.wktPolygon = POLYGON in lon/lat (WGS84) – the only coordinate form that
    actually restricts results (UTM33 and gmWktPolygon are silently ignored)
  * filter.fromDate / filter.toDate, crs=EPSG:4326, pageSize/pageIndex

Output: data/artskart.geojson with art, dato, antall, presisjon_m, kilde (institusjon +
datasett), basis, id. Observer names are deliberately not stored.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, timedelta

from common import RAW, DATA, SESSION, SourceReport, load_aoi, log, now_iso, parse_args

API = "https://artskart.artsdatabanken.no/publicapi/api/observations/list"
TAXA = {  # TaxonId: (norsk, vitenskapelig)
    3987: ("lirype", "Lagopus lagopus"),
    203489: ("orrfugl", "Lyrurus tetrix"),
    203484: ("storfugl", "Tetrao urogallus"),
}
YEARS = 15
MARGIN_DEG = 0.02  # ~1–2 km around the AOI
OUT = RAW / "artskart"


def parse_count(v) -> int | None:
    if v is None:
        return None
    nums = [int(n) for n in re.findall(r"\d+", str(v))]
    return sum(nums) if nums else None


def parse_date(v: str | None) -> str | None:
    if not v:
        return None
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", v)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else v


def fetch_taxon(taxon_id: int, poly: str, since: str, until: str) -> list[dict]:
    """Page through all observations of one taxon inside the polygon.

    The server-side date filter (filter.fromDate/toDate) makes the API time out
    (HTTP 504), so dates are filtered client-side in main().
    """
    obs, page = [], 0
    while True:
        params = {"pageIndex": page, "pageSize": 100, "crs": "EPSG:4326", "filter.taxons": taxon_id,
                  "filter.wktPolygon": poly}
        for attempt in range(4):
            try:
                r = SESSION.get(API, params=params, timeout=300)
                r.raise_for_status()
                d = r.json()
                break
            except Exception as ex:  # noqa: BLE001
                if attempt == 3:
                    raise
                log(f"  Artskart forsøk {attempt + 1} feilet ({str(ex)[:80]}), prøver igjen")
                time.sleep(10 * (attempt + 1))
        obs += d.get("Observations") or []
        if page + 1 >= (d.get("TotalPages") or 1):
            break
        page += 1
    return obs


def in_range(o: dict, since: str, until: str) -> bool:
    d = parse_date(o.get("CollectedDate"))
    return bool(d) and since[:10] <= d[:10] <= until[:10]


def main(force: bool = False) -> SourceReport:
    OUT.mkdir(parents=True, exist_ok=True)
    aoi = load_aoi()
    w, s, e, n = aoi["wgs84"]
    w, s, e, n = w - MARGIN_DEG, s - MARGIN_DEG / 2, e + MARGIN_DEG, n + MARGIN_DEG / 2
    poly = f"POLYGON(({w:.5f} {s:.5f},{e:.5f} {s:.5f},{e:.5f} {n:.5f},{w:.5f} {n:.5f},{w:.5f} {s:.5f}))"
    today = date.today()
    since = (today - timedelta(days=365 * YEARS)).strftime("%Y-%m-%dT00:00:00")
    until = today.strftime("%Y-%m-%dT23:59:59")
    r = SourceReport(name="Artskart funn (lirype, orrfugl, storfugl)",
                     dataset="Artsdatabanken Artskart public API, observations/list", license="CC BY 4.0 (per datasett)")
    feats = []
    for tid, (navn, sci) in TAXA.items():
        try:
            obs = fetch_taxon(tid, poly, since, until)
        except Exception as ex:  # noqa: BLE001
            r.attempt("REST", f"{API}?filter.taxons={tid}", False, str(ex)[:150])
            continue
        (OUT / f"obs_{navn}.json").write_text(json.dumps(obs, ensure_ascii=False, indent=1), encoding="utf-8")
        total = len(obs)
        obs = [o for o in obs if in_range(o, since, until)]
        r.attempt("REST", f"{API}?filter.taxons={tid}&filter.wktPolygon=...", True,
                  f"{total} funn av {navn} totalt i polygonet, {len(obs)} siste {YEARS} år")
        for o in obs:
            try:
                lat = float(str(o.get("Latitude")).replace(",", "."))
                lon = float(str(o.get("Longitude")).replace(",", "."))
            except (TypeError, ValueError):
                continue
            feats.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
                "properties": {
                    "art": navn, "vitenskapelig": o.get("ScientificName") or sci, "taxon_id": tid,
                    "dato": parse_date(o.get("CollectedDate")), "antall": parse_count(o.get("Count")),
                    "antall_tekst": o.get("Count"), "presisjon_m": parse_count(o.get("Precision")),
                    "kilde": " / ".join(x for x in (o.get("Institution"), o.get("DatasetName") or o.get("Collection")) if x),
                    "basis": o.get("BasisOfRecord"), "atferd": o.get("Behavior"), "kjonn": o.get("Sex"),
                    "lokalitet": o.get("Locality"), "id": o.get("Id"), "url": o.get("DetailUrl") or o.get("ObsUrl"),
                },
            })
    fc = {"type": "FeatureCollection", "features": feats,
          "metadata": {"hentet": now_iso(), "fra": since[:10], "til": until[:10], "polygon_wgs84": poly,
                       "kilde": "Artsdatabanken Artskart", "api": API, "taxa": {str(k): v[0] for k, v in TAXA.items()}}}
    DATA.mkdir(exist_ok=True)
    dest = DATA / "artskart.geojson"
    dest.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    r.files.append({"path": "data/artskart.geojson", "size": dest.stat().st_size, "last_modified": "",
                    "fetched_at": now_iso(), "url": API})
    r.route_used = "REST (Artskart public API)"
    r.version = f"{since[:10]} – {until[:10]}"
    r.notes.append(f"{len(feats)} funn totalt. Observatørnavn lagres ikke.")
    r.ok = True
    log(f"Artskart: {len(feats)} funn -> data/artskart.geojson")
    return r


if __name__ == "__main__":
    print(json.dumps(main(parse_args()["force"]).to_dict(), indent=1, ensure_ascii=False)[:3000])
