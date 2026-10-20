"""Fetch the national detailed elevation model (NHM DTM) for the AOI.

Route order:
  1. Kartverket WCS "Høyde – Nasjonal detaljert høydemodell, DTM" (ArcGIS WCS 1.0.0,
     coverage nhm_dtm_topo_25833, native 1 m). Fetched as 2 km tiles at 2 m
     (WIDTH/HEIGHT resampling) -> raw/dtm/tiles/dtm2m_<x>_<y>.tif.
     WCS 1.1.2 refuses GeoTIFF for this data type and WCS 2.0.1 returns HTTP 400
     on every GetCoverage (both documented in SOURCES.md).
  2. Geonorge nedlastings-API, DTM 10 (uuid dddbb667-1303-4ac5-8640-7ec04c0e3918) – fallback only.
Also checks known summits against Kartverket's point elevation API (ws.geonorge.no/hoydedata).
"""
from __future__ import annotations

import json
import math

from common import RAW, SourceReport, download_file, http_get_json, load_aoi, log, parse_args, DAY

WCS = "https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833"
COVERAGE = "nhm_dtm_topo_25833"
HOYDE_API = "https://ws.geonorge.no/hoydedata/v1/punkt"
OUT = RAW / "dtm"
TILE_M = 2000
RES_M = 2
PEAKS = [  # name, lon, lat, expected m (from brief)
    ("Hakefjellet", 7.63833, 58.77743, 873),
    ("Skjevraknuten", 7.73044, 58.79225, 786),
    ("Hukebuvatnet", 7.68927, 58.78639, 584),
]


def tiles(aoi):
    x0 = math.floor(aoi["minx"] / TILE_M) * TILE_M
    y0 = math.floor(aoi["miny"] / TILE_M) * TILE_M
    x = x0
    while x < aoi["maxx"]:
        y = y0
        while y < aoi["maxy"]:
            yield x, y
            y += TILE_M
        x += TILE_M


def main(force: bool = False) -> SourceReport:
    (OUT / "tiles").mkdir(parents=True, exist_ok=True)
    aoi = load_aoi()
    r = SourceReport(name="Høyde – NHM DTM (1 m, hentet som 2 m)",
                     dataset="Kartverket, Nasjonal detaljert høydemodell DTM, WCS coverage nhm_dtm_topo_25833",
                     license="CC BY 4.0")
    n = 0
    px = TILE_M // RES_M
    for x, y in tiles(aoi):
        dest = OUT / "tiles" / f"dtm{RES_M}m_{x}_{y}.tif"
        params = {"service": "WCS", "version": "1.0.0", "request": "GetCoverage", "coverage": COVERAGE,
                  "crs": "EPSG:25833", "bbox": f"{x},{y},{x + TILE_M},{y + TILE_M}",
                  "width": px, "height": px, "format": "GeoTIFF"}
        download_file(WCS, dest, params=params, max_age=90 * DAY, force=force, resume=False, timeout=600)
        if dest.read_bytes()[:2] not in (b"II", b"MM"):
            r.attempt("WCS", WCS, False, f"tile {x},{y}: ikke TIFF: {dest.read_text(errors='replace')[:200]}")
            dest.unlink()
            raise RuntimeError("WCS GetCoverage returnerte ikke GeoTIFF")
        r.add_file(dest)
        n += 1
    r.attempt("WCS 1.0.0", WCS + "?service=WCS&version=1.0.0&request=GetCoverage&coverage=" + COVERAGE, True,
              f"{n} fliser à {TILE_M} m / {RES_M} m oppløsning")
    r.attempt("WCS 1.1.2", WCS + "?version=1.1.2", False,
              "UnSupportedCombination: image/GeoTIFF does not support the coverage data type")
    r.attempt("WCS 2.0.1", WCS + "?version=2.0.1", False, "ArcGIS Server http.400 på alle GetCoverage-varianter")
    r.route_used = "WCS 1.0.0 (Kartverket NHM DTM)"

    # summit check against the point API
    checks = []
    for name, lon, lat, exp in PEAKS:
        try:
            d = http_get_json(HOYDE_API, {"koordsys": 4258, "nord": lat, "ost": lon, "geojson": "false"})
            z = d["punkter"][0]["z"]
            src = d["punkter"][0].get("datakilde")
            checks.append({"navn": name, "lon": lon, "lat": lat, "forventet": exp, "api_z": z, "datakilde": src,
                           "avvik": round(z - exp, 1)})
        except Exception as e:  # noqa: BLE001
            checks.append({"navn": name, "feil": str(e)})
    (OUT / "hoydedata_check.json").write_text(json.dumps(checks, indent=1, ensure_ascii=False), encoding="utf-8")
    for c in checks:
        if "api_z" in c:
            r.notes.append(f"{c['navn']}: høyde-API {c['api_z']:.1f} m ({c['datakilde']}), forventet {c['forventet']} m, "
                           f"avvik {c['avvik']:+.1f} m (stedsnavnpunktet er ikke nødvendigvis toppunktet)")
    r.attempt("REST", HOYDE_API, all("api_z" in c for c in checks), "punkthøyder for kjente topper")
    r.notes.append("Fallback dokumentert, ikke brukt: Geonorge nedlastings-API, DTM 10 UTM33 "
                   "uuid dddbb667-1303-4ac5-8640-7ec04c0e3918.")
    r.ok = True
    return r


if __name__ == "__main__":
    print(json.dumps(main(parse_args()["force"]).to_dict(), indent=1, ensure_ascii=False)[:3000])
