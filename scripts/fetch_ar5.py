"""Fetch FKB-AR5 land resource classes for the AOI.

Route order and result (2026-10-20):
  1. WFS   – NIBIO's AR5 WFS (wfs.nibio.no/cgi-bin/ar5 and variants) answers
             "msLoadMap(): Unable to access file" – broken server side.
  2. Atom  – Geonorge feed lists Bygland but the entry is tagged
             "Norge digitalt-begrenset" and the download returns HTTP 403.
  3. API   – Geonorge nedlastings-API capabilities require role
             nd.filnedlasting.fkb (login). Not available for open download.
  1b. WMS  – NIBIO AR5 WMS is open. We request the classified layers Arealtype,
             Treslag, Skogbonitet, Grunnforhold as 5 m GetMap images in EPSG:25833,
             fetch the SLD (GetStyles) to map legend colours to AR5 codes, and
             decode each pixel to its class code. Mapping is cross-checked with
             GetFeatureInfo at sample points. <- used
  Also fetched: AR50 (NIBIO, open vector, 1:50 000) via NIBIO nedlastings-API as a
  coarse vector reference for mires.
  Manual last resort if you have a Norge digitalt login: download FKB-AR5 for
  Bygland (GML, EPSG:25833) from Geonorge and place the zip in raw/ar5/manual/ –
  fetch_ar5.py will prefer it.

Output: raw/ar5/ar5_<layer>_5m.tif (uint8 class codes, 0 = ukjent) + ar5_palette.json
"""
from __future__ import annotations

import json
import math
import re
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from common import RAW, SESSION, SourceReport, download_file, http_get_text, load_aoi, log, parse_args, DAY

WMS = "https://wms.nibio.no/cgi-bin/ar5"
WFS_CANDIDATES = ["https://wfs.nibio.no/cgi-bin/ar5", "https://wfs.nibio.no/cgi-bin/ar5_2"]
ATOM = "https://nedlasting.geonorge.no/geonorge/ATOM-feeds/FKB-AR5_AtomFeedGML.xml"
GEONORGE_CAP = "https://nedlasting.geonorge.no/api/capabilities/166382b4-82d6-4ea9-a68e-6fd0c87bf788"
AR50_UUID = "4bc2d1e0-f693-4bf2-820d-c11830d849a3"
NIBIO_API = "https://kartkatalog.nibio.no/api"
OUT = RAW / "ar5"
RES_M = 5
MAX_PX = 4000
LAYERS = {  # wms layer -> (property in SLD, output name)
    "Arealtype": ("artype", "arealtype"),
    "Treslag": ("artreslag", "treslag"),
    "Skogbonitet": ("grvanlig", "skogbonitet"),
    "Grunnforhold": ("argrunnf", "grunnforhold"),
}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def fetch_palette(report: SourceReport, force: bool) -> dict:
    dest = OUT / "ar5_styles.sld"
    download_file(WMS, dest, params={"SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetStyles",
                                     "LAYERS": ",".join(LAYERS)}, max_age=30 * DAY, force=force, resume=False)
    x = dest.read_text(encoding="utf-8", errors="replace")
    pal = {}
    for layer in re.findall(r"<NamedLayer>(.*?)</NamedLayer>", x, re.S):
        name = re.search(r"<Name>([^<]*)</Name>", layer).group(1)
        rules = []
        for rule in re.findall(r"<Rule>(.*?)</Rule>", layer, re.S):
            fill = re.search(r'name="fill">([^<]*)<', rule)
            lits = re.findall(r"<ogc:Literal>([^<]*)</ogc:Literal>", rule)
            prop = re.findall(r"<ogc:PropertyName>([^<]*)</ogc:PropertyName>", rule)
            if fill and lits:
                rules.append({"code": int(lits[0]), "rgb": hex_to_rgb(fill.group(1)), "prop": prop[0] if prop else ""})
        pal[name] = rules
    (OUT / "ar5_palette.json").write_text(json.dumps(pal, indent=1), encoding="utf-8")
    report.attempt("WMS GetStyles", WMS + "?REQUEST=GetStyles", bool(pal),
                   ", ".join(f"{k}: {len(v)} klasser" for k, v in pal.items()))
    return pal


def decode(png: Path, rules: list[dict]) -> np.ndarray:
    with rasterio.open(png) as src:
        a = src.read()
    if a.shape[0] == 1 and src.colormap(1):
        cm = src.colormap(1)
        rgba = np.stack([np.vectorize(lambda i, k=k: cm[int(i)][k])(a[0]) for k in range(4)])
    else:
        rgba = a if a.shape[0] == 4 else np.concatenate([a[:3], np.full_like(a[:1], 255)])
    rgb = rgba[:3].astype(np.int32)
    alpha = rgba[3]
    cols = np.array([r["rgb"] for r in rules], dtype=np.int32)  # (k,3)
    codes = np.array([r["code"] for r in rules], dtype=np.uint8)
    d = ((rgb[None, :, :, :] - cols[:, :, None, None]) ** 2).sum(axis=1)  # (k,h,w)
    best = d.argmin(axis=0)
    out = codes[best]
    out[alpha < 128] = 0  # transparent = utenfor dekning / ukjent
    return out


def fetch_layers(aoi, pal, report: SourceReport, force: bool) -> list[Path]:
    w_m = aoi["maxx"] - aoi["minx"]
    h_m = aoi["maxy"] - aoi["miny"]
    W = int(round(w_m / RES_M))
    H = int(round(h_m / RES_M))
    nx = math.ceil(W / MAX_PX)
    ny = math.ceil(H / MAX_PX)
    outs = []
    for layer, (prop, outname) in LAYERS.items():
        rules = pal.get(layer, [])
        if not rules:
            report.notes.append(f"Ingen SLD-regler for {layer}; hoppet over")
            continue
        full = np.zeros((H, W), dtype=np.uint8)
        for ix in range(nx):
            for iy in range(ny):
                c0, c1 = ix * MAX_PX, min(W, (ix + 1) * MAX_PX)
                r0, r1 = iy * MAX_PX, min(H, (iy + 1) * MAX_PX)
                minx = aoi["minx"] + c0 * RES_M
                maxx = aoi["minx"] + c1 * RES_M
                maxy = aoi["maxy"] - r0 * RES_M
                miny = aoi["maxy"] - r1 * RES_M
                png = OUT / "wms" / f"{outname}_{ix}_{iy}.png"
                params = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layer, "STYLES": "",
                          "CRS": "EPSG:25833", "BBOX": f"{minx},{miny},{maxx},{maxy}", "WIDTH": c1 - c0,
                          "HEIGHT": r1 - r0, "FORMAT": "image/png", "TRANSPARENT": "TRUE"}
                download_file(WMS, png, params=params, max_age=30 * DAY, force=force, resume=False, timeout=600)
                if png.read_bytes()[:4] != b"\x89PNG":
                    raise RuntimeError(f"WMS GetMap {layer}: ikke PNG: {png.read_text(errors='replace')[:200]}")
                full[r0:r1, c0:c1] = decode(png, rules)
        dest = OUT / f"ar5_{outname}_{RES_M}m.tif"
        with rasterio.open(dest, "w", driver="GTiff", height=H, width=W, count=1, dtype="uint8", crs="EPSG:25833",
                           transform=from_origin(aoi["minx"], aoi["maxy"], RES_M, RES_M), nodata=0,
                           compress="deflate") as dst:
            dst.write(full, 1)
            dst.update_tags(source="NIBIO AR5 WMS GetMap, decoded via GetStyles SLD", layer=layer, property=prop)
        vals, cnt = np.unique(full, return_counts=True)
        log(f"AR5 {outname}: {dict(zip(vals.tolist(), cnt.tolist()))}")
        report.add_file(dest, url=WMS)
        outs.append(dest)
    report.attempt("WMS GetMap", WMS + "?REQUEST=GetMap&CRS=EPSG:25833&LAYERS=...", True,
                   f"{len(outs)} lag à {W}x{H} px, {RES_M} m")
    return outs


def crosscheck(aoi, pal, report: SourceReport) -> None:
    """GetFeatureInfo at a few interior points to verify colour->code decoding."""
    checks = []
    rng = np.random.default_rng(42)
    tifs = {k: OUT / f"ar5_{v[1]}_{RES_M}m.tif" for k, v in LAYERS.items()}
    if not all(t.exists() for t in tifs.values()):
        return
    arrs = {}
    for k, t in tifs.items():
        with rasterio.open(t) as src:
            arrs[k] = src.read(1)
            ref = src
            H, W = arrs[k].shape
    with rasterio.open(tifs["Arealtype"]) as src:
        tries = 0
        while len(checks) < 12 and tries < 60:
            tries += 1
            r, c = int(rng.integers(5, H - 5)), int(rng.integers(5, W - 5))
            # prefer forest pixels so that the bonitet mapping gets exercised
            if arrs["Arealtype"][r, c] not in (30, 60, 50) or (tries < 40 and arrs["Arealtype"][r, c] != 30):
                continue
            x, y = src.xy(r, c)
            params = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetFeatureInfo", "LAYERS": "Arealtype",
                      "QUERY_LAYERS": "Arealtype", "CRS": "EPSG:25833",
                      "BBOX": f"{x - 25},{y - 25},{x + 25},{y + 25}", "WIDTH": 50, "HEIGHT": 50, "I": 25, "J": 25,
                      "INFO_FORMAT": "application/vnd.ogc.gml", "FEATURE_COUNT": 1}
            try:
                txt = http_get_text(WMS, params, timeout=60)
            except Exception as e:  # noqa: BLE001
                checks.append({"x": x, "y": y, "feil": str(e)})
                continue
            tag = lambda n: (lambda m: int(m.group(1)) if m else None)(re.search(rf"<{n}>(\d+)</{n}>", txt))  # noqa: E731
            checks.append({"x": round(x), "y": round(y),
                           "decoded": {"artype": int(arrs["Arealtype"][r, c]), "artreslag": int(arrs["Treslag"][r, c]),
                                       "grvanlig": int(arrs["Skogbonitet"][r, c]), "argrunnf": int(arrs["Grunnforhold"][r, c])},
                           "gfi": {"artype": tag("artype"), "artreslag": tag("artreslag"), "arskogbon": tag("arskogbon"),
                                   "argrunnf": tag("argrunnf"), "grvanlig": tag("grvanlig")}})
    (OUT / "gfi_crosscheck.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
    ok = [c for c in checks if c.get("gfi", {}).get("artype") is not None]
    agree = sum(1 for c in ok if c["decoded"]["artype"] == c["gfi"]["artype"]
                and c["decoded"]["artreslag"] == c["gfi"]["artreslag"]
                and c["decoded"]["argrunnf"] == c["gfi"]["argrunnf"])
    report.attempt("WMS GetFeatureInfo", WMS + "?REQUEST=GetFeatureInfo&INFO_FORMAT=application/vnd.ogc.gml", bool(ok),
                   f"{agree}/{len(ok)} stikkprøver: dekodet artype/treslag/grunnforhold = attributter fra GetFeatureInfo")
    bon = sorted({(c["decoded"]["grvanlig"], c["gfi"]["arskogbon"]) for c in ok
                  if c["decoded"]["grvanlig"] and c["gfi"].get("arskogbon") is not None})
    if bon:
        report.notes.append(f"Skogbonitet-dekoding: (WMS-stilkode grvanlig, AR5 arskogbon) observert: {bon}. "
                            "AR5 arskogbon: 11 impediment, 12 lav, 13 middels, 14 høg, 15 særs høg.")
        (OUT / "bonitet_mapping.json").write_text(json.dumps({str(g): a for g, a in bon}, indent=1), encoding="utf-8")


def fetch_ar50(report: SourceReport, force: bool) -> None:
    try:
        areas = SESSION.get(f"{NIBIO_API}/v2/codelists/area/{AR50_UUID}", timeout=60).json()
        a = next(x for x in areas if x.get("code") == "4220")
        fmt = next((f["name"] for f in a["formats"] if f["name"].lower() in ("gml", "geojson", "gdb", "fgdb", "sosi")),
                   a["formats"][0]["name"])
        proj = next((p["code"] for p in a["projections"] if p["code"] in ("25833", "25832", "4258")), a["projections"][0]["code"])
        body = {"email": "", "orderLines": [{"metadataUuid": AR50_UUID, "areas": [{"code": "4220", "type": "kommune", "name": "Bygland"}],
                                             "projections": [{"code": proj}], "formats": [{"name": fmt}]}]}
        o = SESSION.post(f"{NIBIO_API}/v2/order", json=body, timeout=120)
        o.raise_for_status()
        f = o.json()["files"][0]
        dest = download_file(f["downloadUrl"], OUT / "ar50" / f["name"], max_age=60 * DAY, force=force)
        report.attempt("Nedlastings-API (AR50, NIBIO)", f"{NIBIO_API}/v2/order", True, f"{f['name']} {fmt} EPSG:{proj}")
        report.add_file(dest, url=f["downloadUrl"])
    except Exception as e:  # noqa: BLE001
        report.attempt("Nedlastings-API (AR50, NIBIO)", f"{NIBIO_API}/v2/order", False, str(e)[:200])


def main(force: bool = False) -> SourceReport:
    (OUT / "wms").mkdir(parents=True, exist_ok=True)
    aoi = load_aoi()
    r = SourceReport(name="FKB-AR5 arealressurs", dataset="Geovekst/NIBIO FKB-AR5, uuid 166382b4-82d6-4ea9-a68e-6fd0c87bf788",
                     license="FKB-AR5 vektor: Norge digitalt-begrenset. AR5 WMS og AR50: NLOD/CC BY 4.0")
    manual = sorted((OUT / "manual").glob("*.zip")) if (OUT / "manual").exists() else []
    # 1. WFS
    for u in WFS_CANDIDATES:
        try:
            t = http_get_text(u, {"service": "WFS", "request": "GetCapabilities"}, timeout=60)
            ok = "<WFS_Capabilities" in t or "wfs:WFS_Capabilities" in t
            r.attempt("WFS", u, ok, "" if ok else re.sub(r"<[^>]+>", " ", t).strip()[:120])
        except Exception as e:  # noqa: BLE001
            r.attempt("WFS", u, False, str(e)[:120])
    # 2. Atom
    try:
        feed = download_file(ATOM, OUT / "atom_feed.xml", max_age=1 * DAY, force=force, resume=False)
        x = feed.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"<entry>(?:(?!</entry>).)*?Bygland(?:(?!</entry>).)*?</entry>", x, re.S)
        link = re.search(r'href="(https://nedlasting\.geonorge\.no/api/download/file[^"]+)"', m.group(0)) if m else None
        restricted = m is not None and "restricted" in m.group(0)
        if link:
            resp = SESSION.get(link.group(1), stream=True, timeout=60, allow_redirects=True)
            code = resp.status_code
            resp.close()
            r.attempt("Atom", link.group(1), code == 200,
                      f"HTTP {code}; feed-kategori: {'Norge digitalt-begrenset' if restricted else 'åpen'}")
            if code == 200:
                r.notes.append("Atom-nedlasting svarte 200 – vurder å bytte til vektorfilen (ikke implementert).")
        else:
            r.attempt("Atom", ATOM, False, "ingen Bygland-oppføring")
    except Exception as e:  # noqa: BLE001
        r.attempt("Atom", ATOM, False, str(e)[:120])
    # 3. Geonorge API
    try:
        cap = SESSION.get(GEONORGE_CAP, timeout=60).json()
        role = cap.get("accessConstraintRequiredRole")
        r.attempt("Nedlastings-API (Geonorge)", GEONORGE_CAP, not role, f"krever rolle: {role}" if role else "åpen")
    except Exception as e:  # noqa: BLE001
        r.attempt("Nedlastings-API (Geonorge)", GEONORGE_CAP, False, str(e)[:120])
    if manual:
        r.notes.append(f"Manuell FKB-AR5-fil funnet: {manual[0].name} (brukes i build hvis støttet)")
        r.add_file(manual[0])
    # 1b. WMS raster
    pal = fetch_palette(r, force)
    fetch_layers(aoi, pal, r, force)
    crosscheck(aoi, pal, r)
    fetch_ar50(r, force)
    r.route_used = "WMS GetMap 5 m dekodet via SLD (vektor er Norge digitalt-begrenset)"
    r.notes.append("Vektor-AR5 er ikke åpen; klassene er rasterisert fra NIBIO sin AR5 WMS i 5 m og aggregeres til 10 m i build. "
                   "Kantpiksler mellom to klasser kan få nærmeste legendefarge.")
    r.ok = True
    return r


if __name__ == "__main__":
    print(json.dumps(main(parse_args()["force"]).to_dict(), indent=1, ensure_ascii=False)[:4000])
