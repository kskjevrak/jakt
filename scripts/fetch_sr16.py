"""Fetch NIBIO SR16 forest resource raster (16 m) for Agder and clip to the AOI.

Route order:
  1. WCS – NIBIO has no SR16 WCS (wcs.nibio.no does not resolve; wms.nibio.no/cgi-bin/sr16
     answers SERVICE=WCS with a ServiceException).
  2. Atom – no Atom feed is registered for the SR16 raster dataset in Geonorge metadata.
  3. NIBIO kartkatalog nedlastings-API (same protocol as Geonorge, no login):
     can-download -> order -> downloadUrl (county file, ~1.85 GB). <- used
After download the needed bands are clipped to the AOI with rasterio reading
straight from the zip (/vsizip/), so the county-wide files are never extracted.
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import rasterio
from rasterio.windows import from_bounds

from common import RAW, SESSION, SourceReport, download_file, load_aoi, log, parse_args, DAY

UUID = "5de45872-f534-4e97-840e-3cfd8db04398"
API = "https://kartkatalog.nibio.no/api"
AREA = {"code": "42", "type": "fylke", "name": "Agder"}
PROJ = "25833"
FORMAT = "RASTER"
OUT = RAW / "sr16"
# SR16 variable names (band files) we want, matched case-insensitively against member names
WANTED = {
    "treslag": r"srrtreslag",        # 1 gran, 2 furu, 3 lauv
    "hoyde": r"srrmhoyde",           # middelhøyde (Lorey), dm – units checked in build
    "overhoyde": r"srrohoyde",       # overhøyde, dm
    "volum": r"srrvolmb",            # volum med bark, m3/ha
    "bonitet": r"srrbonitet",        # H40 bonitet
    "kronedekning": r"srrkronedek",  # %
    "grunnflate": r"srrgrflate",     # m2/ha
    "diameter": r"srrdiammiddel(?!_)",
    "treantall": r"srrtreantall(?!_)",
    "alder": r"srrtrealder",
}


def order_download_url(report: SourceReport) -> str:
    cd = SESSION.post(f"{API}/v2/can-download", json={"metadataUuid": UUID, "area": AREA["code"],
                                                       "projection": PROJ, "format": FORMAT}, timeout=60)
    cd.raise_for_status()
    report.attempt("Nedlastings-API", f"{API}/v2/can-download", cd.json().get("canDownload", False), cd.text[:100])
    body = {"email": "", "orderLines": [{"metadataUuid": UUID, "areas": [AREA], "projections": [{"code": PROJ}],
                                         "formats": [{"name": FORMAT}]}]}
    o = SESSION.post(f"{API}/v2/order", json=body, timeout=120)
    o.raise_for_status()
    d = o.json()
    (OUT / "order.json").write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    f = d["files"][0]
    report.attempt("Nedlastings-API", f"{API}/v2/order", True,
                   f"ordre {d.get('referenceNumber')}, fil {f['name']} status {f['status']}")
    return f["downloadUrl"]


def clip_bands(zip_path: Path, aoi, report: SourceReport) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    (OUT / "zip_listing.txt").write_text("\n".join(names), encoding="utf-8")
    tifs = [n for n in names if n.lower().endswith((".tif", ".tiff"))]
    found = []
    for key, pat in WANTED.items():
        cands = [n for n in tifs if re.search(pat, Path(n).name, re.I)]
        if not cands:
            report.notes.append(f"SR16-variabel '{key}' ({pat}) ikke funnet i zip")
            continue
        src_name = cands[0]
        dest = OUT / f"aoi_{key}.tif"
        if dest.exists() and dest.stat().st_mtime > zip_path.stat().st_mtime:
            found.append(key)
            report.add_file(dest)
            continue
        vsi = f"/vsizip/{zip_path.as_posix()}/{src_name}"
        with rasterio.open(vsi) as src:
            win = from_bounds(aoi["minx"], aoi["miny"], aoi["maxx"], aoi["maxy"], src.transform)
            win = win.round_offsets().round_lengths()
            data = src.read(window=win, boundless=True, fill_value=src.nodata if src.nodata is not None else 0)
            prof = src.profile.copy()
            prof.update(height=data.shape[1], width=data.shape[2], transform=src.window_transform(win),
                        compress="deflate", tiled=False, driver="GTiff")
            prof.pop("blockxsize", None); prof.pop("blockysize", None)
            with rasterio.open(dest, "w", **prof) as dst:
                dst.write(data)
                dst.update_tags(source=src_name, zip=zip_path.name)
        log(f"klippet {key}: {src_name} -> {dest.name} {data.shape}")
        found.append(key)
        report.add_file(dest)
    return found


def main(force: bool = False) -> SourceReport:
    OUT.mkdir(parents=True, exist_ok=True)
    aoi = load_aoi()
    r = SourceReport(name="SR16 Skogressurskart raster (16 m)", dataset=f"NIBIO, uuid {UUID}", license="CC BY 4.0 (NLOD)")
    r.attempt("WCS", "https://wcs.nibio.no/cgi-bin/sr16", False, "vertsnavn finnes ikke; wms.nibio.no/cgi-bin/sr16 gir ServiceException for SERVICE=WCS")
    r.attempt("Atom", "https://kartkatalog.geonorge.no/api/getdata/" + UUID, False, "ingen Atom-feed registrert for datasettet")
    url = order_download_url(r)
    zip_path = OUT / url.rsplit("/", 1)[-1]
    download_file(url, zip_path, max_age=60 * DAY, force=force, timeout=3600)
    r.add_file(zip_path, url=url)
    found = clip_bands(zip_path, aoi, r)
    r.route_used = "NIBIO nedlastings-API (fylkesfil) + klipp til AOI"
    r.notes.append(f"Klippet til AOI: {', '.join(found)}")
    r.ok = bool(found)
    return r


if __name__ == "__main__":
    print(json.dumps(main(parse_args()["force"]).to_dict(), indent=1, ensure_ascii=False)[:3000])
