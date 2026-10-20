"""Compute habitat scores 0–100 per species from config/habitat.json and the 10 m rasters.

Outputs:
  data/score_<art>.tif   Cloud Optimized GeoTIFF, uint8, 255 = ukjent, EPSG:25833
  data/score_<art>.png   RGBA overlay in EPSG:3857 for MapLibre image source (+ .json with corner coordinates)
  raw/preview/score_<art>.png   Kartverket topo + overlay + jaktfelt outline, for eyeballing (not committed)
  data/grid.geojson      50 m cells with all attributes and scores (via write_grid)
  data/score_stats.json  summary numbers per species
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin, array_bounds
from rasterio.warp import reproject, Resampling, transform as warp_transform
from shapely.geometry import box, mapping, Polygon

from common import CONFIG, DATA, RAW, download_file, log, now_iso, DAY
from build_grid import DERIVED, RES, load

PREVIEW = RAW / "preview"  # contains stitched Kartverket tiles -> stays out of the repo
WMTS = "https://cache.kartverket.no/v1/wmts/1.0.0/topo/default/webmercator/{z}/{y}/{x}.png"
EARTH = 6378137.0
ORIGIN = math.pi * EARTH


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ------------------------------------------------------------------ rule evaluation
def trapes(x: np.ndarray, pts: list[float]) -> np.ndarray:
    a, b, c, d = [float(v) for v in pts]
    xp, fp = [], []
    if b > a:
        xp += [a, b]; fp += [0.0, 1.0]
    else:
        xp += [b]; fp += [1.0]
    if d > c:
        xp += [c, d]; fp += [1.0, 0.0]
    else:
        xp += [c]; fp += [1.0]
    # np.interp needs increasing xp; collapse duplicates
    xs, fs = [], []
    for xv, fv in zip(xp, fp):
        if xs and xv <= xs[-1]:
            xv = xs[-1] + 1e-6
        xs.append(xv); fs.append(fv)
    left = 0.0 if b > a else 1.0
    right = 0.0 if d > c else 1.0
    return np.interp(x, xs, fs, left=left, right=right).astype(np.float32)


def evaluate(rule: dict, var: np.ndarray, unknown_mask: np.ndarray | None, neutral: float) -> np.ndarray:
    t = rule["type"]
    if t == "trapes":
        f = trapes(var.astype(np.float32), rule["punkter"])
        if "flatt_verdi" in rule:
            f = np.where(var < 0, rule["flatt_verdi"], f)
    elif t == "klasser":
        lut = np.full(256, float(rule.get("ellers", 0.0)), dtype=np.float32)
        for k, v in rule["klasser"].items():
            lut[int(k)] = v
        f = lut[np.clip(var, 0, 255).astype(np.uint8)]
    elif t == "flagg":
        f = np.where(var > 0, rule.get("sann", 1.0), rule.get("usann", 0.0)).astype(np.float32)
    else:
        raise ValueError(f"ukjent faktortype {t}")
    if unknown_mask is not None:
        f = np.where(unknown_mask, neutral, f)
    return f


def score_species(cfg: dict, art: dict, rasters: dict[str, np.ndarray]) -> tuple[np.ndarray, dict]:
    neutral = cfg["globalt"]["ukjent"]["noytral_verdi"]
    ar5_unknown = rasters["ar5_arealtype"] == 0
    num = np.zeros_like(rasters["hoyde_moh"], dtype=np.float32)
    den = 0.0
    contrib = {}
    def is_ar5(kilde: str) -> bool:
        return kilde.startswith("ar5_") or kilde == "arealtype_komb"

    for name, rule in art["faktorer"].items():
        var = rasters[rule["kilde"]]
        unk = ar5_unknown if is_ar5(rule["kilde"]) else None
        f = evaluate(rule, var, unk, neutral)
        w = float(rule["vekt"])
        num += w * f
        den += w
        contrib[name] = float(np.nanmean(f))
    score = num / den
    pen_total = np.ones_like(score)
    for name, rule in art.get("straff", {}).items():
        var = rasters[rule["kilde"]]
        unk = ar5_unknown if is_ar5(rule["kilde"]) else None
        f = evaluate(rule, var, unk, 1.0)
        mn = float(rule.get("min", 0.0))
        pen = mn + (1 - mn) * f
        pen_total *= pen
        contrib["straff_" + name] = float(np.nanmean(pen))
    score = 100 * score * pen_total
    bad = np.isin(rasters["ar5_arealtype"], cfg["globalt"]["ikke_habitat"]["ar5_arealtype"])
    score[bad] = 0
    score[np.isnan(rasters["hoyde_moh"]) | (rasters["hoyde_moh"] < -9000)] = np.nan
    return score.astype(np.float32), contrib


# ------------------------------------------------------------------ outputs
def write_cog(path: Path, score: np.ndarray, grid: dict) -> None:
    a = np.where(np.isnan(score), 255, np.clip(np.round(score), 0, 100)).astype(np.uint8)
    tr = from_origin(grid["minx"], grid["maxy"], RES, RES)
    with rasterio.open(path, "w", driver="COG", width=grid["width"], height=grid["height"], count=1, dtype="uint8",
                       crs=grid["crs"], transform=tr, nodata=255, compress="DEFLATE", overviews="AUTO") as dst:
        dst.write(a, 1)


def mercator_grid(grid: dict, z: int = 13):
    """Web-mercator pixel grid aligned with WMTS zoom z covering the AOI; returns transform, width, height, tile range."""
    res = 2 * ORIGIN / (256 * 2 ** z)
    xs, ys = warp_transform(grid["crs"], "EPSG:3857",
                            [grid["minx"], grid["maxx"], grid["minx"], grid["maxx"]],
                            [grid["miny"], grid["miny"], grid["maxy"], grid["maxy"]])
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    tile = 256 * res
    tx0, tx1 = int((minx + ORIGIN) // tile), int((maxx + ORIGIN) // tile)
    ty0, ty1 = int((ORIGIN - maxy) // tile), int((ORIGIN - miny) // tile)
    x0 = -ORIGIN + tx0 * tile
    y0 = ORIGIN - ty0 * tile
    width = (tx1 - tx0 + 1) * 256
    height = (ty1 - ty0 + 1) * 256
    return from_origin(x0, y0, res, res), width, height, (tx0, tx1, ty0, ty1), z


def warp_to(arr: np.ndarray, grid: dict, dst_transform, width, height, nodata, resampling) -> np.ndarray:
    src_tr = from_origin(grid["minx"], grid["maxy"], RES, RES)
    dst = np.full((height, width), nodata, dtype=arr.dtype)
    reproject(arr, dst, src_transform=src_tr, src_crs=grid["crs"], dst_transform=dst_transform, dst_crs="EPSG:3857",
              src_nodata=nodata, dst_nodata=nodata, resampling=resampling)
    return dst


def colorize(score: np.ndarray, vis: dict, inside: np.ndarray, buffer: np.ndarray) -> np.ndarray:
    stops = vis["stopp"]
    xs = [s[0] for s in stops]
    rgb = np.array([hex_rgb(s[1]) for s in stops], dtype=np.float32)
    al = np.array([s[2] for s in stops], dtype=np.float32)
    s = np.nan_to_num(score, nan=-1.0)
    out = np.zeros((4, *score.shape), dtype=np.uint8)
    for i in range(3):
        out[i] = np.clip(np.interp(s, xs, rgb[:, i]), 0, 255).astype(np.uint8)
    alpha = np.interp(s, xs, al)
    alpha = np.where(s < vis["min_vist"], 0.0, alpha)
    alpha = np.where(inside > 0, alpha, np.where(buffer > 0, alpha * vis["utenfor_jaktfelt_alpha"], 0.0))
    out[3] = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    return out


def save_png(path: Path, rgba: np.ndarray) -> None:
    from PIL import Image
    Image.fromarray(np.moveaxis(rgba, 0, -1), "RGBA").save(path, optimize=True)


def topo_mosaic(mt, width, height, tiles, z) -> np.ndarray:
    from PIL import Image
    tx0, tx1, ty0, ty1 = tiles
    mosaic = np.zeros((height, width, 3), dtype=np.uint8)
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            p = download_file(WMTS.format(z=z, x=tx, y=ty), RAW / "tiles" / "topo" / str(z) / f"{tx}_{ty}.png",
                              max_age=365 * DAY, resume=False)
            im = np.asarray(Image.open(p).convert("RGB"))
            r0, c0 = (ty - ty0) * 256, (tx - tx0) * 256
            mosaic[r0:r0 + 256, c0:c0 + 256] = im
    return mosaic


def preview(name: str, rgba: np.ndarray, topo: np.ndarray, mt, jaktfelt_3857, legend: list, title: str, foot: str) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    H, W = rgba.shape[1:]
    fig = plt.figure(figsize=(W / 100, H / 100 + 1.1), dpi=100)
    ax = fig.add_axes([0, 110 / (H + 110), 1, H / (H + 110)])
    ax.imshow(topo)
    ax.imshow(np.moveaxis(rgba, 0, -1))
    inv = ~mt
    for poly in getattr(jaktfelt_3857, "geoms", [jaktfelt_3857]):
        xs, ys = zip(*[inv * (x, y) for x, y in poly.exterior.coords])
        ax.plot(xs, ys, color="#0b3d0b", linewidth=2.2)
        for ring in poly.interiors:
            xs, ys = zip(*[inv * (x, y) for x, y in ring.coords])
            ax.plot(xs, ys, color="#0b3d0b", linewidth=1.2)
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    fig.legend(handles=legend, loc="lower left", ncol=len(legend), frameon=False, bbox_to_anchor=(0.01, 0.0),
               title=title, title_fontsize=11)
    fig.text(0.99, 0.02, foot, ha="right", fontsize=8, color="#555")
    PREVIEW.mkdir(parents=True, exist_ok=True)
    out = PREVIEW / f"{name}.png"
    fig.savefig(out, dpi=100)
    plt.close(fig)
    return out


def dominant_layer(scores: dict[str, np.ndarray], cfg: dict, grid: dict, mt, mw, mh, inside_m, buffer_m, topo, jf,
                   mask_in: np.ndarray) -> dict:
    """Species with the highest score where that score exceeds the threshold; 0 elsewhere, 255 unknown."""
    from matplotlib.patches import Patch

    arts = list(scores)
    vis = cfg["visning"]["dominerende"]
    stack = np.stack([np.nan_to_num(scores[a], nan=-1.0) for a in arts])
    mx = stack.max(axis=0)
    am = stack.argmax(axis=0)
    dom = np.where(mx > vis["terskel"], am + 1, 0).astype(np.uint8)
    dom[np.isnan(scores[arts[0]])] = 255
    tr = from_origin(grid["minx"], grid["maxy"], RES, RES)
    with rasterio.open(DATA / "dominant.tif", "w", driver="COG", width=grid["width"], height=grid["height"], count=1,
                       dtype="uint8", crs=grid["crs"], transform=tr, nodata=255, compress="DEFLATE") as dst:
        dst.write(dom, 1)
        dst.update_tags(klasser=json.dumps({str(i + 1): a for i, a in enumerate(arts)}), terskel=vis["terskel"])
    dm = warp_to(dom, grid, mt, mw, mh, 255, Resampling.nearest)
    rgba = np.zeros((4, mh, mw), dtype=np.uint8)
    for i, a in enumerate(arts):
        r, g, b = hex_rgb(cfg["arter"][a]["farge"])
        sel = dm == i + 1
        rgba[0][sel], rgba[1][sel], rgba[2][sel] = r, g, b
    alpha = np.where((dm > 0) & (dm < 255), vis["alpha"], 0.0)
    alpha = np.where(inside_m > 0, alpha, np.where(buffer_m > 0, alpha * cfg["visning"]["utenfor_jaktfelt_alpha"], 0.0))
    rgba[3] = (alpha * 255).astype(np.uint8)
    save_png(DATA / "dominant.png", rgba)
    ha = {a: float(((dom == i + 1) & mask_in).sum() * RES * RES / 1e4) for i, a in enumerate(arts)}
    none_ha = float(((dom == 0) & mask_in).sum() * RES * RES / 1e4)
    legend = [Patch(facecolor=cfg["arter"][a]["farge"], alpha=0.85, label=f"{cfg['arter'][a]['navn']} ({ha[a]:.0f} ha)") for a in arts]
    preview("dominant", rgba, topo, mt, jf, legend,
            f"Dominerende art der høyeste score > {vis['terskel']}. Ingen art over terskel: {none_ha:.0f} ha av jaktfeltet",
            "Bakgrunn: Kartverket topografisk (WMTS).")
    return {"ha_per_art_jaktfelt": ha, "ha_ingen": none_ha, "terskel": vis["terskel"]}


# ------------------------------------------------------------------ 50 m grid
def write_grid(scores: dict[str, np.ndarray], rasters: dict[str, np.ndarray], grid: dict, dom_terskel: float = 50) -> dict:
    f = 5  # 10 m -> 50 m
    H, W = grid["height"] // f, grid["width"] // f

    def blocks(a):
        return a[:H * f, :W * f].reshape(H, f, W, f).transpose(0, 2, 1, 3).reshape(H, W, f * f)

    def bmean(a, nd=-9000):
        b = blocks(a.astype(np.float32))
        b = np.where(b <= nd, np.nan, b) if nd is not None else b
        with np.errstate(all="ignore"):
            return np.nanmean(b, axis=2)

    def bmode(a):
        b = blocks(a)
        codes = np.unique(b)
        best = np.zeros((H, W), dtype=np.uint8); bestn = np.full((H, W), -1)
        for c in codes:
            n = (b == c).sum(axis=2) - (100 if c == 0 else 0)
            upd = n > bestn; best[upd] = c; bestn[upd] = n[upd]
        return best

    def circ_mean(a):
        b = blocks(a.astype(np.float32))
        valid = b >= 0
        rad = np.radians(b)
        s = np.where(valid, np.sin(rad), 0).sum(axis=2); c = np.where(valid, np.cos(rad), 0).sum(axis=2)
        m = (np.degrees(np.arctan2(s, c)) + 360) % 360
        return np.where(valid.sum(axis=2) >= f * f // 2, m, -1)

    inside = bmean(rasters["mask_jaktfelt"], nd=None)
    buf = bmean(rasters["mask_buffer500"], nd=None)
    keep = buf > 0
    hoyde = bmean(rasters["hoyde_moh"])
    hb = blocks(rasters["hoyde_moh"])
    attrs = {
        "h": np.round(hoyde).astype(np.float32), "hmin": np.nanmin(np.where(hb <= -9000, np.nan, hb), axis=2),
        "hmax": np.nanmax(np.where(hb <= -9000, np.nan, hb), axis=2),
        "s": np.round(bmean(rasters["helning_grader"]), 1), "asp": np.round(circ_mean(rasters["eksposisjon_grader"])),
        "tpi": np.round(bmean(rasters["tpi150_m"])), "tpi5": np.round(bmean(rasters["tpi500_m"])),
        "at": bmode(rasters["arealtype_komb"]), "tr": bmode(rasters["ar5_treslag"]), "bo": bmode(rasters["ar5_bonitet"]),
        "gf": bmode(rasters["ar5_grunnforhold"]), "st": bmode(rasters["sr16_treslag"]),
        "th": np.round(bmean(rasters["sr16_hoyde_m"]), 1), "kr": np.round(bmean(rasters["sr16_kronedekning_pst"])),
        "dm": np.round(bmean(rasters["dist_myr_m"])), "dsm": np.round(bmean(rasters["dist_stormyr_m"])),
        "db": np.round(bmean(rasters["dist_bekk_m"])), "dv": np.round(bmean(rasters["dist_vann_m"])),
        "ds": np.round(bmean(rasters["dist_skoggrense_m"])), "dl": np.round(bmean(rasters["dist_lauv_m"])),
        "inn": np.round(inside, 2), "vann": np.round(bmean(rasters["mask_vann"], nd=None), 2),
        "sti": (bmean(rasters["mask_sti"], nd=None) > 0).astype(np.uint8),
        "uk": (bmean((rasters["ar5_arealtype"] == 0).astype(np.float32), nd=None) > 0.5).astype(np.uint8),
    }
    for art, sc in scores.items():
        attrs["sc_" + art] = np.round(bmean(sc, nd=None))
    sc_stack = np.stack([np.nan_to_num(attrs["sc_" + a], nan=-1.0) for a in scores])
    attrs["dom"] = np.where(sc_stack.max(axis=0) > dom_terskel, sc_stack.argmax(axis=0) + 1, 0).astype(np.uint8)
    # geometry in WGS84
    xs = grid["minx"] + (np.arange(W) + 0.5) * f * RES
    ys = grid["maxy"] - (np.arange(H) + 0.5) * f * RES
    rows, cols = np.nonzero(keep)
    cx, cy = xs[cols], ys[rows]
    half = f * RES / 2
    corners_x = np.stack([cx - half, cx + half, cx + half, cx - half], axis=1).ravel()
    corners_y = np.stack([cy - half, cy - half, cy + half, cy + half], axis=1).ravel()
    lon, lat = warp_transform(grid["crs"], "EPSG:4326", corners_x.tolist(), corners_y.tolist())
    lon = np.array(lon).reshape(-1, 4); lat = np.array(lat).reshape(-1, 4)
    feats = []
    for k in range(len(rows)):
        r, c = rows[k], cols[k]
        props = {"i": int(c), "j": int(r)}
        for name, arr in attrs.items():
            v = arr[r, c]
            if isinstance(v, (np.floating, float)):
                props[name] = None if np.isnan(v) else (int(v) if float(v).is_integer() else float(v))
            else:
                props[name] = int(v)
        ring = [[round(float(lon[k, m]), 5), round(float(lat[k, m]), 5)] for m in range(4)]
        ring.append(ring[0])
        feats.append({"type": "Feature", "properties": props, "geometry": {"type": "Polygon", "coordinates": [ring]}})
    meta = {
        "bygget": now_iso(), "cellestorrelse_m": f * RES, "crs_kilde": grid["crs"],
        "origo_utm33": [grid["minx"], grid["maxy"]], "antall": len(feats),
        "felter": {"i,j": "kolonne, rad i 50 m-gitteret fra nordvestre hjørne av AOI", "h": "middelhøyde moh", "hmin/hmax": "min/maks høyde i cellen",
                   "s": "middelhelning grader", "asp": "eksposisjon grader (-1 flatt)", "tpi": "TPI 150 m", "tpi5": "TPI 500 m",
                   "at": "AR5 arealtype", "tr": "AR5 treslag", "bo": "AR5 bonitet", "gf": "AR5 grunnforhold", "st": "SR16 treslag",
                   "th": "SR16 middelhøyde m", "kr": "SR16 kronedekning %", "dm": "avstand myr m", "dsm": "avstand stor myr m",
                   "db": "avstand bekk m", "dv": "avstand vann m", "ds": "avstand skoggrense m", "dl": "avstand lauvskog m",
                   "inn": "andel av cellen innenfor jaktfeltet", "vann": "andel vann", "sti": "sti/traktorveg i cellen", "uk": "AR5 ukjent",
                   "sc_<art>": "habitatscore 0–100 (null = ukjent)",
                   "dom": f"dominerende art der høyeste score > {dom_terskel}: 0 ingen, 1 lirype, 2 orrfugl, 3 storfugl"},
        "koder": json.loads((CONFIG / "habitat.json").read_text(encoding="utf-8"))["variabler"],
    }
    fc = {"type": "FeatureCollection", "metadata": meta, "features": feats}
    out = DATA / "grid.geojson"
    out.write_text(json.dumps(fc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    log(f"grid.geojson: {len(feats)} celler, {out.stat().st_size / 1e6:.1f} MB")
    return {"celler": len(feats), "mb": round(out.stat().st_size / 1e6, 2)}


def main() -> dict:
    cfg = json.loads((CONFIG / "habitat.json").read_text(encoding="utf-8"))
    grid = json.loads((DERIVED / "grid.json").read_text(encoding="utf-8"))
    names = [p.stem for p in DERIVED.glob("*.tif")]
    rasters = {n: load(n) for n in names}
    rasters["hoyde_moh"] = np.where(rasters["hoyde_moh"] <= -9000, np.nan, rasters["hoyde_moh"])
    for k in list(rasters):
        if k.startswith("sr16_") and rasters[k].dtype != np.uint8:
            rasters[k] = np.where(rasters[k] <= -9000, np.nan, rasters[k])
    # trapes on NaN -> treat sr16 NaN as 0 (not forest) for continuous variables
    for k in ("sr16_hoyde_m", "sr16_kronedekning_pst", "sr16_alder_aar", "sr16_bonitet_h40", "sr16_volum_m3ha"):
        if k in rasters:
            rasters[k] = np.nan_to_num(rasters[k], nan=0.0)

    jf = gpd.read_file(DATA / "jaktfelt.geojson").to_crs(3857).geometry.iloc[0]
    mt, mw, mh, tiles, z = mercator_grid(grid)
    inside_m = warp_to(rasters["mask_jaktfelt"], grid, mt, mw, mh, 0, Resampling.nearest)
    buffer_m = warp_to(rasters["mask_buffer500"], grid, mt, mw, mh, 0, Resampling.nearest)
    topo = topo_mosaic(mt, mw, mh, tiles, z)
    bounds = array_bounds(mh, mw, mt)
    lon, lat = warp_transform("EPSG:3857", "EPSG:4326", [bounds[0], bounds[2]], [bounds[3], bounds[1]])
    corners = [[lon[0], lat[0]], [lon[1], lat[0]], [lon[1], lat[1]], [lon[0], lat[1]]]  # TL, TR, BR, BL

    stats, scores = {}, {}
    mask_in = rasters["mask_jaktfelt"] > 0
    for art_id, art in cfg["arter"].items():
        score, contrib = score_species(cfg, art, rasters)
        scores[art_id] = score
        inside_vals = score[mask_in & ~np.isnan(score)]
        st = {
            "middel_jaktfelt": float(inside_vals.mean()), "median_jaktfelt": float(np.median(inside_vals)),
            "andel_over_60_pst": float((inside_vals >= 60).mean() * 100), "ha_over_60": float((inside_vals >= 60).sum() * RES * RES / 1e4),
            "andel_over_75_pst": float((inside_vals >= 75).mean() * 100), "maks": float(inside_vals.max()),
            "middel_faktorer_jaktfelt": contrib,
        }
        stats[art_id] = st
        write_cog(DATA / f"score_{art_id}.tif", score, grid)
        sm = warp_to(np.nan_to_num(score, nan=-1).astype(np.float32), grid, mt, mw, mh, -1.0, Resampling.bilinear)
        sm[sm < 0] = np.nan
        rgba = colorize(sm, cfg["visning"], inside_m, buffer_m)
        png = DATA / f"score_{art_id}.png"
        save_png(png, rgba)
        (DATA / f"score_{art_id}.json").write_text(json.dumps({"coordinates": corners, "crs": "EPSG:4326",
                                                               "kilde_crs": "EPSG:3857", "px": [mw, mh],
                                                               "bygget": now_iso()}), encoding="utf-8")
        from matplotlib.patches import Patch
        legend = [Patch(facecolor=s[1], alpha=min(1, s[2] + 0.1), label=f"≥ {s[0]}") for s in cfg["visning"]["stopp"]]
        pv = preview(f"score_{art_id}", rgba, topo, mt, jf, legend,
                     f"Habitatscore {art['navn'].lower()} (0–100). Innenfor jaktfelt: middel {st['middel_jaktfelt']:.0f}, "
                     f"{st['andel_over_60_pst']:.0f} % av arealet ≥ 60 ({st['ha_over_60']:.0f} ha)",
                     "Bakgrunn: Kartverket topografisk (WMTS). Score < %d vises ikke." % cfg["visning"]["min_vist"])
        log(f"{art_id}: middel {st['middel_jaktfelt']:.1f}, >=60: {st['andel_over_60_pst']:.0f} % ({st['ha_over_60']:.0f} ha), "
            f"png {png.stat().st_size / 1e6:.2f} MB, preview {pv.name}")
    stats["_dominerende"] = dominant_layer(scores, cfg, grid, mt, mw, mh, inside_m, buffer_m, topo, jf, mask_in)
    (DATA / "dominant.json").write_text(json.dumps({"coordinates": corners, "crs": "EPSG:4326", "kilde_crs": "EPSG:3857",
                                                    "px": [mw, mh], "klasser": {str(i + 1): a for i, a in enumerate(cfg["arter"])},
                                                    "terskel": cfg["visning"]["dominerende"]["terskel"], "bygget": now_iso()}),
                                        encoding="utf-8")
    g = write_grid(scores, rasters, grid, cfg["visning"]["dominerende"]["terskel"])
    stats["_grid"] = g
    stats["_bygget"] = now_iso()
    (DATA / "score_stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf-8")
    return stats


if __name__ == "__main__":
    s = main()
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "middel_faktorer_jaktfelt"} if isinstance(v, dict) else v
                      for k, v in s.items()}, indent=1, ensure_ascii=False))
