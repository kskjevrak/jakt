"""Build the 10 m analysis rasters (raw/derived/*.tif) and N50 vector layers (data/*.geojson).

Inputs (from scripts/download.py):
  raw/aoi.json, raw/dtm/tiles/*.tif (2 m), raw/ar5/ar5_*_5m.tif, raw/ar5/bonitet_mapping.json,
  raw/sr16/aoi_*.tif (16 m), raw/n50/*.zip, data/jaktfelt.geojson
Outputs:
  raw/derived/<variabel>.tif – one float32/uint8 GeoTIFF per variable in config/habitat.json "variabler"
  data/vann.geojson, data/bekker.geojson, data/stier.geojson, data/myr_n50.geojson (WGS84, klippet til AOI)
The 50 m grid is written by build_scores.write_grid() once scores exist.
"""
from __future__ import annotations

import json
import math
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features
from rasterio.enums import Resampling
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import reproject
from scipy import ndimage
from shapely.geometry import box

from common import RAW, DATA, load_aoi, log

DERIVED = RAW / "derived"
RES = 10
N50_ZIP = next(iter((RAW / "n50").glob("*.zip")), None)

# AR5 WMS style code (grvanlig) -> AR5 arskogbon; the first three were verified with GetFeatureInfo
BONITET_FALLBACK = {6: 15, 7: 14, 8: 13, 9: 12, 10: 11}


class Grid:
    def __init__(self, aoi: dict):
        self.minx, self.miny, self.maxx, self.maxy = aoi["minx"], aoi["miny"], aoi["maxx"], aoi["maxy"]
        self.width = int(round((self.maxx - self.minx) / RES))
        self.height = int(round((self.maxy - self.miny) / RES))
        self.transform = from_origin(self.minx, self.maxy, RES, RES)
        self.crs = "EPSG:25833"
        self.bounds = (self.minx, self.miny, self.maxx, self.maxy)

    def save(self, name: str, arr: np.ndarray, nodata=None) -> Path:
        DERIVED.mkdir(parents=True, exist_ok=True)
        p = DERIVED / f"{name}.tif"
        dtype = "uint8" if arr.dtype == np.uint8 else "int16" if arr.dtype == np.int16 else "float32"
        with rasterio.open(p, "w", driver="GTiff", width=self.width, height=self.height, count=1, dtype=dtype,
                           crs=self.crs, transform=self.transform, nodata=nodata, compress="deflate") as dst:
            dst.write(arr.astype(dtype), 1)
        return p

    def rasterize(self, geoms, all_touched=True) -> np.ndarray:
        geoms = [g for g in geoms if g is not None and not g.is_empty]
        if not geoms:
            return np.zeros((self.height, self.width), dtype=np.uint8)
        return features.rasterize(((g, 1) for g in geoms), out_shape=(self.height, self.width),
                                  transform=self.transform, all_touched=all_touched, dtype="uint8")

    def distance(self, mask: np.ndarray) -> np.ndarray:
        if not mask.any():
            return np.full(mask.shape, 9999, dtype=np.float32)
        return (ndimage.distance_transform_edt(~mask.astype(bool)) * RES).astype(np.float32)


def load(name: str) -> np.ndarray:
    with rasterio.open(DERIVED / f"{name}.tif") as s:
        return s.read(1)


# ------------------------------------------------------------------ DTM
def build_dtm(g: Grid) -> dict[str, np.ndarray]:
    tiles = sorted((RAW / "dtm" / "tiles").glob("*.tif"))
    srcs = [rasterio.open(t) for t in tiles]
    mosaic, tr = merge(srcs, bounds=g.bounds, res=(2, 2), nodata=-9999.0)
    for s in srcs:
        s.close()
    z2 = mosaic[0].astype(np.float32)
    z2[z2 <= -9000] = np.nan
    # 2 m -> 10 m block mean (5x5); the mosaic may be one pixel larger than needed, crop to multiples
    H, W = g.height * 5, g.width * 5
    z2 = z2[:H, :W]
    z10 = np.nanmean(z2.reshape(g.height, 5, g.width, 5), axis=(1, 3)).astype(np.float32)
    log(f"DTM 10 m: {z10.shape}, {np.nanmin(z10):.0f}–{np.nanmax(z10):.0f} m, nan={np.isnan(z10).sum()}")
    gy, gx = np.gradient(z10, RES)  # gy: along rows (southward), gx: along cols (eastward)
    gy_north = -gy
    slope = np.degrees(np.arctan(np.hypot(gx, gy_north))).astype(np.float32)
    aspect = (np.degrees(np.arctan2(-gx, -gy_north)) % 360).astype(np.float32)
    aspect[slope < 2] = -1

    def tpi(radius_m: int) -> np.ndarray:
        size = int(2 * radius_m / RES) + 1
        filled = np.where(np.isnan(z10), np.nanmean(z10), z10)
        return (z10 - ndimage.uniform_filter(filled, size=size, mode="nearest")).astype(np.float32)

    # hillshade for previews
    az, alt = np.radians(315), np.radians(45)
    sl = np.arctan(np.hypot(gx, gy_north))
    asp = np.arctan2(-gx, -gy_north)
    hs = (np.sin(alt) * np.cos(sl) + np.cos(alt) * np.sin(sl) * np.cos(az - asp))
    hs = np.clip(hs * 255, 0, 255).astype(np.uint8)
    out = {"hoyde_moh": z10, "helning_grader": slope, "eksposisjon_grader": aspect,
           "tpi150_m": tpi(150), "tpi500_m": tpi(500), "hillshade": hs}
    for k, v in out.items():
        g.save(k, v, nodata=None if v.dtype == np.uint8 else -9999)
    return out


# ------------------------------------------------------------------ AR5
def block_mode(a: np.ndarray, f: int) -> np.ndarray:
    """Mode of f x f blocks of a categorical uint8 raster (ties -> smallest code; 0 only if all 0)."""
    H, W = a.shape[0] // f, a.shape[1] // f
    b = a[:H * f, :W * f].reshape(H, f, W, f).transpose(0, 2, 1, 3).reshape(H, W, f * f)
    codes = np.unique(b)
    best = np.zeros((H, W), dtype=np.uint8)
    bestn = np.zeros((H, W), dtype=np.int16)
    for c in codes:
        n = (b == c).sum(axis=2).astype(np.int16)
        if c == 0:
            n = n - 100  # never prefer "unknown" if any real class is present
        upd = n > bestn
        best[upd] = c
        bestn[upd] = n[upd]
    return best


def build_ar5(g: Grid) -> dict[str, np.ndarray]:
    out = {}
    mapping = BONITET_FALLBACK.copy()
    mp = RAW / "ar5" / "bonitet_mapping.json"
    if mp.exists():
        mapping.update({int(k): int(v) for k, v in json.loads(mp.read_text()).items()})
    for layer, var in [("arealtype", "ar5_arealtype"), ("treslag", "ar5_treslag"),
                       ("skogbonitet", "ar5_bonitet"), ("grunnforhold", "ar5_grunnforhold")]:
        with rasterio.open(RAW / "ar5" / f"ar5_{layer}_5m.tif") as s:
            a5 = s.read(1)
            assert abs(s.transform.c - g.minx) < 1e-6 and abs(s.transform.f - g.maxy) < 1e-6, "AR5 raster er ikke AOI-justert"
        a10 = block_mode(a5, 2)
        if var == "ar5_bonitet":
            lut = np.zeros(256, dtype=np.uint8)
            for k, v in mapping.items():
                lut[k] = v
            a10 = lut[a10]
        out[var] = a10
        g.save(var, a10, nodata=0)
        vals, cnt = np.unique(a10, return_counts=True)
        log(f"{var}: " + ", ".join(f"{v}:{c}" for v, c in zip(vals, cnt)))
    return out


# ------------------------------------------------------------------ SR16
def build_sr16(g: Grid) -> dict[str, np.ndarray]:
    out = {}
    spec = {  # file key -> (variable, scale, dtype)
        "treslag": ("sr16_treslag", 1.0, np.uint8),
        "hoyde": ("sr16_hoyde_m", 0.1, np.float32),
        "kronedekning": ("sr16_kronedekning_pst", 1.0, np.float32),
        "alder": ("sr16_alder_aar", 1.0, np.float32),
        "bonitet": ("sr16_bonitet_h40", 1.0, np.float32),
        "volum": ("sr16_volum_m3ha", 1.0, np.float32),
    }
    for key, (var, scale, dtype) in spec.items():
        p = RAW / "sr16" / f"aoi_{key}.tif"
        if not p.exists():
            log(f"SR16 {key} mangler, hopper over")
            continue
        with rasterio.open(p) as s:
            src = s.read(1).astype(np.float32)
            nd = s.nodata if s.nodata is not None else -9999
            src[src == nd] = np.nan
            dst = np.full((g.height, g.width), np.nan, dtype=np.float32)
            reproject(src, dst, src_transform=s.transform, src_crs=s.crs, dst_transform=g.transform, dst_crs=g.crs,
                      resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
        dst = dst * scale
        if dtype == np.uint8:
            a = np.where(np.isnan(dst), 0, dst).astype(np.uint8)
            g.save(var, a, nodata=0)
            out[var] = a
        else:
            a = np.where(np.isnan(dst), -9999, dst).astype(np.float32)
            g.save(var, a, nodata=-9999)
            out[var] = a
    return out


# ------------------------------------------------------------------ N50
def read_n50(theme: str, layer: str, g: Grid) -> gpd.GeoDataFrame:
    member = f"Basisdata_4220_Bygland_25833_N50{theme}_GML.gml"
    try:
        d = gpd.read_file(f"zip://{N50_ZIP.as_posix()}!{member}", layer=layer, engine="pyogrio", bbox=g.bounds)
    except Exception as e:  # noqa: BLE001
        log(f"N50 {layer}: {e}")
        return gpd.GeoDataFrame(geometry=[], crs=g.crs)
    if d.crs is None:
        d = d.set_crs(g.crs)
    return d


def export(gdf: gpd.GeoDataFrame, name: str, g: Grid, keep: list[str]) -> int:
    if len(gdf) == 0:
        (DATA / f"{name}.geojson").write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
        return 0
    clip = gdf.clip(box(*g.bounds))
    clip = clip[~clip.geometry.is_empty]
    clip["geometry"] = clip.geometry.simplify(2, preserve_topology=True)
    cols = [c for c in keep if c in clip.columns]
    clip[cols + ["geometry"]].to_crs(4326).to_file(DATA / f"{name}.geojson", driver="GeoJSON",
                                                  COORDINATE_PRECISION=5)
    return len(clip)


def build_n50(g: Grid) -> dict[str, np.ndarray]:
    out = {}
    vann = gpd.GeoDataFrame(geometry=[], crs=g.crs)
    parts = [read_n50("Arealdekke", l, g) for l in ("Innsjø", "InnsjøRegulert", "Elv")]
    parts = [p for p in parts if len(p)]
    if parts:
        for p, lyr in zip(parts, ("Innsjø", "InnsjøRegulert", "Elv")):
            p["n50type"] = lyr
        vann = gpd.GeoDataFrame(gpd.pd.concat(parts, ignore_index=True), crs=g.crs)
    bekk = read_n50("Arealdekke", "ElvBekk", g)
    myr = read_n50("Arealdekke", "Myr", g)
    veg = read_n50("Samferdsel", "Veglenke", g)
    tcol = next((c for c in veg.columns if c.lower() == "typeveg"), None)
    if tcol:
        veg = veg.rename(columns={tcol: "typeveg"})
        veg["typeveg"] = veg["typeveg"].astype(str)
        log(f"N50 Veglenke typer: {sorted(veg['typeveg'].unique())}")
    else:
        veg["typeveg"] = "ukjent"
    n = {
        "vann": export(vann, "vann", g, ["n50type", "navn", "høyde"]),
        "bekker": export(bekk, "bekker", g, ["navn"]),
        "stier": export(veg, "stier", g, ["typeveg", "vegkategori", "vegnummer"]),
        "myr_n50": export(myr, "myr_n50", g, []),
    }
    log(f"N50 eksportert: {n}")
    out["mask_myr_n50"] = g.rasterize(list(myr.geometry), all_touched=False)
    g.save("mask_myr_n50", out["mask_myr_n50"].astype(np.uint8))
    out["mask_vann"] = g.rasterize(list(vann.geometry))
    out["mask_bekk"] = g.rasterize(list(bekk.geometry)) | g.rasterize(list(vann[vann["n50type"] == "Elv"].geometry) if len(vann) else [])
    sti_mask = g.rasterize(list(veg[veg["typeveg"].str.contains("sti|traktor", case=False, regex=True)].geometry)) if len(veg) else np.zeros((g.height, g.width), np.uint8)
    out["mask_sti"] = sti_mask
    out["mask_veg"] = g.rasterize(list(veg.geometry)) if len(veg) else sti_mask
    out["dist_bekk_m"] = g.distance(out["mask_bekk"])
    out["dist_vann_m"] = g.distance(out["mask_vann"])
    for k in ("mask_vann", "mask_bekk", "mask_sti", "mask_veg"):
        g.save(k, out[k].astype(np.uint8))
    g.save("dist_bekk_m", out["dist_bekk_m"])
    g.save("dist_vann_m", out["dist_vann_m"])
    return out


# ------------------------------------------------------------------ derived distances and flags
def build_derived(g: Grid, ar5: dict, sr16: dict, n50: dict) -> None:
    at = ar5["ar5_arealtype"]
    tr = ar5["ar5_treslag"]
    # AR5 is not mapped in detail above the tree line (plateau mires show as "åpen fastmark"),
    # so mires are the union of AR5 myr (60) and N50 Myr polygons. arealtype_komb carries that override.
    myr_n50 = n50["mask_myr_n50"].astype(bool)
    myr = (at == 60) | myr_n50
    komb = at.copy()
    komb[(at == 50) & myr_n50] = 60
    g.save("arealtype_komb", komb, nodata=0)
    skog = at == 30
    apent = (komb == 50) | (komb == 60)
    log(f"myr: AR5 {int((at == 60).sum()) * RES * RES / 1e4:.0f} ha, N50 {int(myr_n50.sum()) * RES * RES / 1e4:.0f} ha, "
        f"union {int(myr.sum()) * RES * RES / 1e4:.0f} ha")
    g.save("mask_myr", myr.astype(np.uint8))
    g.save("dist_myr_m", g.distance(myr))
    g.save("dist_lauv_m", g.distance((tr == 32) | (tr == 33)))
    # forest edge: forest pixels touching open land or vice versa
    edge = (skog & ndimage.binary_dilation(apent)) | (apent & ndimage.binary_dilation(skog))
    g.save("dist_skoggrense_m", g.distance(edge))
    g.save("mask_skoggrense", edge.astype(np.uint8))

    # mires >= 1 ha with forest on at least two of four sides
    lab, n = ndimage.label(myr)
    areas = ndimage.sum(myr, lab, index=np.arange(1, n + 1)) * RES * RES / 10_000
    big = [i + 1 for i, a in enumerate(areas) if a >= 1.0]
    stormyr = np.zeros_like(myr)
    centers = ndimage.center_of_mass(myr, lab, index=big) if big else []
    rows, cols = np.indices(myr.shape)
    sides_of: dict[int, int] = {}
    for comp, (cy, cx) in zip(big, centers):
        m = lab == comp
        ring = ndimage.binary_dilation(m, iterations=6) & ~m  # ~60 m collar
        ang = (np.degrees(np.arctan2(cols - cx, -(rows - cy))) + 360) % 360  # 0 = north
        sides = 0
        for a0 in (315, 45, 135, 225):  # N, E, S, W sectors of 90 degrees
            sec = ring & (((ang - a0) % 360) < 90)
            if sec.sum() > 0 and skog[sec].mean() >= 0.4:
                sides += 1
        sides_of[comp] = sides
        if sides >= 2:
            stormyr |= m
    g.save("mask_stormyr", stormyr.astype(np.uint8))
    g.save("dist_stormyr_m", g.distance(stormyr))
    myr_areal = np.zeros(myr.shape, dtype=np.float32)
    for i, a in enumerate(areas):
        myr_areal[lab == i + 1] = a
    g.save("myr_areal_ha", myr_areal)
    log(f"myr: {n} polygoner, {len(big)} over 1 ha, {sum(1 for s in sides_of.values() if s >= 2)} med skog på >= 2 sider")

    h = sr16.get("sr16_hoyde_m")
    kr = sr16.get("sr16_kronedekning_pst")
    al = sr16.get("sr16_alder_aar")
    st = sr16.get("sr16_treslag")
    if h is not None and kr is not None:
        hv, kv = h > -9000, kr > -9000
        hogst = skog & ((hv & (h < 4)) | (kv & (kr < 15)))
        ung = skog & hv & (h < 8)
        g.save("flagg_hogstflate", hogst.astype(np.uint8))
        g.save("flagg_ungskog", ung.astype(np.uint8))
    if st is not None and kr is not None and al is not None:
        tett = (st == 1) & (kr > 70) & (al > -9000) & (al < 70)
        g.save("flagg_tett_gran", tett.astype(np.uint8))


def build_masks(g: Grid) -> None:
    jf = gpd.read_file(DATA / "jaktfelt.geojson").to_crs(g.crs)
    geom = jf.geometry.iloc[0]
    g.save("mask_jaktfelt", g.rasterize([geom], all_touched=False))
    g.save("mask_buffer500", g.rasterize([geom.buffer(500)], all_touched=False))


def main() -> None:
    aoi = load_aoi()
    g = Grid(aoi)
    log(f"grid {g.width} x {g.height} @ {RES} m")
    build_dtm(g)
    ar5 = build_ar5(g)
    sr16 = build_sr16(g)
    n50 = build_n50(g)
    build_derived(g, ar5, sr16, n50)
    build_masks(g)
    (DERIVED / "grid.json").write_text(json.dumps({"minx": g.minx, "miny": g.miny, "maxx": g.maxx, "maxy": g.maxy,
                                                   "res": RES, "width": g.width, "height": g.height, "crs": g.crs}),
                                       encoding="utf-8")
    log("build_grid ferdig: " + ", ".join(sorted(p.stem for p in DERIVED.glob("*.tif"))))


if __name__ == "__main__":
    main()
