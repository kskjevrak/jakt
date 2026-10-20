"""Compare the current data/grid.geojson with a previous copy and check named target areas.

  python scripts/compare_scores.py [raw/grid_prev.geojson]

Prints per-species area statistics before/after, the cells that changed most (with the
nearest N50 place name), and score summaries around named places from the brief.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer

from common import RAW, DATA, load_aoi

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252

ARTER = ["lirype", "orrfugl", "storfugl"]
N50_ZIP = next(iter((RAW / "n50").glob("*.zip")), None)
TO_WGS = Transformer.from_crs(25833, 4326, always_xy=True)


def load_grid(path: Path) -> pd.DataFrame:
    fc = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    for f in fc["features"]:
        p = f["properties"]
        ring = f["geometry"]["coordinates"][0]
        p["lon"] = sum(c[0] for c in ring[:4]) / 4
        p["lat"] = sum(c[1] for c in ring[:4]) / 4
        rows.append(p)
    df = pd.DataFrame(rows)
    meta = fc.get("metadata", {})
    ox, oy = meta.get("origo_utm33", [None, None])
    cs = meta.get("cellestorrelse_m", 50)
    if ox is not None:
        df["x"] = ox + (df["i"] + 0.5) * cs
        df["y"] = oy - (df["j"] + 0.5) * cs
    return df


def place_names(aoi) -> gpd.GeoDataFrame:
    g = f"zip://{N50_ZIP.as_posix()}!Basisdata_4220_Bygland_25833_N50Stedsnavn_GML.gml"
    d = gpd.read_file(g, layer="StedsnavnTekst", engine="pyogrio", bbox=(aoi["minx"], aoi["miny"], aoi["maxx"], aoi["maxy"]))
    d["navn"] = d["fulltekst"].astype(str)
    d["geometry"] = d.geometry.centroid
    return d[["navn", "geometry"]].drop_duplicates("navn").reset_index(drop=True)


def nearest_name(names: gpd.GeoDataFrame, x: float, y: float) -> str:
    dx = names.geometry.x.values - x
    dy = names.geometry.y.values - y
    dist = np.hypot(dx, dy)
    k = int(dist.argmin())
    bearing = (math.degrees(math.atan2(dx[k] * -1, dy[k] * -1)) + 360) % 360  # direction from place to cell
    dirs = ["N", "NØ", "Ø", "SØ", "S", "SV", "V", "NV"]
    return f"{dist[k] / 1000:.1f} km {dirs[int(((bearing + 22.5) % 360) // 45)]} for {names.navn[k]}"


def area_ha(df: pd.DataFrame, col: str, thr: float = 60, inside_min: float = 0.5) -> float:
    sel = df[(df["inn"] >= inside_min) & (df[col] >= thr)]
    return float(sel["inn"].sum() * 0.25)  # 50 m cell = 0.25 ha, weighted by inside fraction


def main(prev_path: str) -> None:
    aoi = load_aoi()
    cur = load_grid(DATA / "grid.geojson")
    prev = load_grid(prev_path)
    names = place_names(aoi)
    m = cur.merge(prev[["i", "j"] + [f"sc_{a}" for a in ARTER]], on=["i", "j"], suffixes=("", "_prev"))
    inside = m[m["inn"] >= 0.5]
    print("\n| Art | ha ≥ 60 før | ha ≥ 60 etter | middel før | middel etter | celler opp over 60 | celler ned under 60 |")
    print("|---|---|---|---|---|---|---|")
    for a in ARTER:
        c, p = inside[f"sc_{a}"], inside[f"sc_{a}_prev"]
        up = int(((p < 60) & (c >= 60)).sum()); down = int(((p >= 60) & (c < 60)).sum())
        print(f"| {a} | {area_ha(prev, f'sc_{a}'):.0f} | {area_ha(cur, f'sc_{a}'):.0f} | {p.mean():.1f} | {c.mean():.1f} | {up} | {down} |")
    print("\nStørste endringer (celler innenfor jaktfeltet):")
    for a in ARTER:
        d = (inside[f"sc_{a}"] - inside[f"sc_{a}_prev"])
        print(f"\n{a}: middel Δ {d.mean():+.1f}, 5/95-persentil {d.quantile(.05):+.0f}/{d.quantile(.95):+.0f}")
        for sign, lab in ((1, "opp"), (-1, "ned")):
            top = inside.assign(d=d)[np.sign(d) == sign].reindex((d * sign).sort_values(ascending=False).index).dropna(subset=["d"]).head(4)
            for _, r in top.iterrows():
                print(f"  {lab:3s} {r['d']:+4.0f} ({r[f'sc_{a}_prev']:.0f}→{r[f'sc_{a}']:.0f}) {r['h']:.0f} moh, "
                      f"{nearest_name(names, r['x'], r['y'])}  [{r['lat']:.4f}, {r['lon']:.4f}]")
    # named cores
    print("\nMålkontroll:")
    targets = {"Flyet": "orrfugl", "Litjønni": "orrfugl", "Gytjønn": "orrfugl", "Bergebekken": "orrfugl"}
    for navn, art in targets.items():
        row = names[names.navn == navn]
        if row.empty:
            print(f"  {navn}: ikke funnet i N50 stedsnavn"); continue
        px, py = row.geometry.iloc[0].x, row.geometry.iloc[0].y
        if navn == "Bergebekken":  # mires east of the stream, within 1.2 km
            sel = inside[(inside["x"] > px) & (np.hypot(inside["x"] - px, inside["y"] - py) < 1200) & (inside["at"] == 60)]
            lab = "myrceller inntil 1,2 km øst for Bergebekken"
        else:
            sel = inside[np.hypot(inside["x"] - px, inside["y"] - py) < 400]
            lab = "celler innen 400 m"
        if len(sel) == 0:
            print(f"  {navn}: ingen celler"); continue
        print(f"  {navn} ({lab}, n={len(sel)}): {art} middel {sel[f'sc_{art}'].mean():.0f} (før {sel[f'sc_{art}_prev'].mean():.0f}), "
              f"andel ≥ 60: {(sel[f'sc_{art}'] >= 60).mean() * 100:.0f} %, dominerende: "
              + ", ".join(f"{ARTER[k - 1]} {v}" for k, v in sel['dom'].value_counts().items() if k > 0))
    hk = names[names.navn == "Hakefjellet"]
    if not hk.empty:
        px, py = hk.geometry.iloc[0].x, hk.geometry.iloc[0].y
        dx, dy = inside["x"] - px, inside["y"] - py
        bearing = (np.degrees(np.arctan2(dx, dy)) + 360) % 360
        sel = inside[(np.hypot(dx, dy) < 1300) & (bearing > 190) & (bearing < 280)]
        print(f"  Hakefjellets sørvestli (n={len(sel)}): lirype middel {sel['sc_lirype'].mean():.0f} (før {sel['sc_lirype_prev'].mean():.0f}), "
              f"maks {sel['sc_lirype'].max():.0f}, andel ≥ 45: {(sel['sc_lirype'] >= 45).mean() * 100:.0f} %")
    # overall summit check: lirype around the three highest named summits
    for navn in ("Skjevraknuten", "Knutskronuten", "Gyfjell", "Krubba"):
        row = names[names.navn == navn]
        if row.empty:
            continue
        px, py = row.geometry.iloc[0].x, row.geometry.iloc[0].y
        sel = inside[np.hypot(inside["x"] - px, inside["y"] - py) < 300]
        if len(sel):
            print(f"  {navn} (300 m): lirype middel {sel['sc_lirype'].mean():.0f} (før {sel['sc_lirype_prev'].mean():.0f}), "
                  f"orrfugl {sel['sc_orrfugl'].mean():.0f}, høyde {sel['h'].mean():.0f} moh")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(RAW / "grid_prev.geojson"))
