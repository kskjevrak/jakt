"""Build data/jaktfelt.geojson and data/naboteiger.geojson from raw/teig/teiger_bbox.geojson.

Also writes raw/aoi.json – the processing extent (jaktfelt bounds + 1000 m, EPSG:25833)
used by every other fetch/build script – and data/aoi.geojson for the map.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from common import RAW, DATA, MATRIKKEL, KOMMUNE, log, now_iso

BUFFER_NABO_M = 500     # neighbours within this distance are kept
CLIP_NABO_M = 1200      # neighbour polygons are clipped to this distance to keep the file small
AOI_MARGIN_M = 1000     # 500 m habitat buffer + 500 m safety for raster edges
GRID_SNAP = 10


def _is_ours(me: dict) -> bool:
    return (me["gnr"], me["bnr"]) in MATRIKKEL


def main() -> dict:
    src = RAW / "teig" / "teiger_bbox.geojson"
    fc = json.loads(src.read_text(encoding="utf-8"))
    pts = json.loads((RAW / "teig" / "eiendom_punkter.json").read_text(encoding="utf-8"))

    own, feste, nabo = [], [], []
    for f in fc["features"]:
        p = f["properties"]
        geom = shape(f["geometry"])
        ours = [m for m in p["matrikkelenheter"] if _is_ours(m)]
        if ours:
            kind = "feste" if all(m["fnr"] > 0 for m in ours) else "grunneiendom"
            rec = {**p, "geometry": geom, "kind": kind,
                   "gnr_bnr": sorted({f"{m['gnr']}/{m['bnr']}" + (f"/{m['fnr']}" if m['fnr'] else "") for m in ours})}
            (feste if kind == "feste" else own).append(rec)
        else:
            nabo.append({**p, "geometry": geom})

    if not own:
        raise SystemExit("Ingen teiger matchet matrikkelenhetene – sjekk raw/teig/teiger_bbox.geojson")

    jakt_geoms = [r["geometry"] for r in own + feste]
    jaktfelt = unary_union(jakt_geoms).buffer(0)
    areal_ha = jaktfelt.area / 10_000

    # cross-check: every REST teig point (fnr 0) should fall inside the dissolved polygon
    missing = [p for p in pts if p["fnr"] == 0 and p["snr"] == 0 and not jaktfelt.buffer(5).contains(
        gpd.points_from_xy([p["x"]], [p["y"]])[0])]
    # Teiger shared by several matrikkelenheter (e.g. 49/3,5) are ordinary hunting ground per Knut 2026-10-20;
    # only disputes and unregistered commons are flagged.
    flagged = sorted({f"{r['matrikkelnummer']} ({'tvist' if r['tvist'] else 'uregistrert jordsameie'})"
                      for r in own + feste if r["tvist"] or r["uregistrert_jordsameie"]})

    # neighbours within 500 m, clipped to 1200 m
    ring = jaktfelt.buffer(BUFFER_NABO_M)
    clipbox = jaktfelt.buffer(CLIP_NABO_M)
    nabo_sel = []
    for r in nabo:
        if r["geometry"].intersects(ring) and not r["geometry"].within(jaktfelt):
            g = r["geometry"].intersection(clipbox)
            if not g.is_empty:
                nabo_sel.append({**r, "geometry": g})

    def to_gdf(recs, keep):
        if not recs:
            return gpd.GeoDataFrame({k: [] for k in keep}, geometry=[], crs="EPSG:25833")
        rows = [{k: r.get(k) for k in keep} for r in recs]
        return gpd.GeoDataFrame(rows, geometry=[r["geometry"] for r in recs], crs="EPSG:25833")

    keep = ["teig_id", "matrikkelnummer", "bruksnavn", "areal_m2", "flere_matrikkelenheter", "oppdatert"]
    teiger = to_gdf(own + feste, keep + ["kind", "gnr_bnr"])
    teiger["gnr_bnr"] = teiger["gnr_bnr"].apply(lambda v: ", ".join(v))
    nabo_gdf = to_gdf(nabo_sel, keep)
    for g in (teiger, nabo_gdf):
        g["areal_ha"] = (g.geometry.area / 10_000).round(1)

    jf = gpd.GeoDataFrame(
        [{
            "navn": "Jaktfelt Bygland 49/1, 49/2, 49/3, 49/4, 50/1",
            "kommunenummer": KOMMUNE,
            "matrikkelenheter": ", ".join(f"{g}/{b}" for g, b in MATRIKKEL),
            "antall_teiger": len(own) + len(feste),
            "antall_festeteiger": len(feste),
            "areal_ha": round(areal_ha, 1),
            "bygget": now_iso(),
            "merknad": "; ".join(flagged) if flagged else "",
        }],
        geometry=[jaktfelt], crs="EPSG:25833",
    )

    DATA.mkdir(exist_ok=True)
    jf.to_crs(4326).to_file(DATA / "jaktfelt.geojson", driver="GeoJSON")
    teiger.to_crs(4326).to_file(DATA / "teiger.geojson", driver="GeoJSON")
    nabo_gdf.to_crs(4326).to_file(DATA / "naboteiger.geojson", driver="GeoJSON")

    minx, miny, maxx, maxy = jaktfelt.bounds
    aoi = {
        "minx": math.floor((minx - AOI_MARGIN_M) / GRID_SNAP) * GRID_SNAP,
        "miny": math.floor((miny - AOI_MARGIN_M) / GRID_SNAP) * GRID_SNAP,
        "maxx": math.ceil((maxx + AOI_MARGIN_M) / GRID_SNAP) * GRID_SNAP,
        "maxy": math.ceil((maxy + AOI_MARGIN_M) / GRID_SNAP) * GRID_SNAP,
        "crs": "EPSG:25833",
        "margin_m": AOI_MARGIN_M,
    }
    aoi_wgs = gpd.GeoSeries([box(aoi["minx"], aoi["miny"], aoi["maxx"], aoi["maxy"])], crs="EPSG:25833").to_crs(4326)
    aoi["wgs84"] = [round(v, 5) for v in aoi_wgs.total_bounds]
    (RAW / "aoi.json").write_text(json.dumps(aoi, indent=1), encoding="utf-8")
    gpd.GeoDataFrame([{"navn": "AOI", **{k: aoi[k] for k in ("minx", "miny", "maxx", "maxy")}}],
                     geometry=aoi_wgs, crs=4326).to_file(DATA / "aoi.geojson", driver="GeoJSON")

    summary = {
        "areal_ha": round(areal_ha, 1),
        "teiger": len(own), "festeteiger": len(feste), "naboteiger": len(nabo_sel),
        "mangler_rest_punkt_i_polygon": [p["tekst"] for p in missing],
        "flagget": flagged,
        "aoi": aoi,
        "per_matrikkelenhet": {f"{g}/{b}": round(sum(r["geometry"].area for r in own if (g, b) in
                                                   [(m["gnr"], m["bnr"]) for m in r["matrikkelenheter"]]) / 10_000, 1)
                               for g, b in MATRIKKEL},
    }
    (RAW / "jaktfelt_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"jaktfelt: {areal_ha:.0f} ha, {len(own)} teiger + {len(feste)} festeteiger, {len(nabo_sel)} naboteiger, "
        f"AOI {aoi['maxx'] - aoi['minx']:.0f} x {aoi['maxy'] - aoi['miny']:.0f} m")
    if missing:
        log(f"ADVARSEL: REST-punkter utenfor jaktfelt: {[p['tekst'] for p in missing]}")
    return summary


if __name__ == "__main__":
    print(json.dumps(main(), indent=1, ensure_ascii=False))
