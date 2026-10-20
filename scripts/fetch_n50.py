"""Fetch N50 Kartdata for Bygland (water, streams, trails).

Route order:
  1. WFS – Kartverket publishes no N50 WFS in Geonorge (checked via kartkatalog search API).
  2. Atom feed – kommune file 4220 in EPSG:25833 GML. <- used
  3. Geonorge nedlastings-API – available (no login) but not needed.
"""
from __future__ import annotations

import json

from common import RAW, KOMMUNE, KOMMUNENAVN, SourceReport, download_file, http_get_json, parse_args, DAY

ATOM = "https://nedlasting.geonorge.no/geonorge/ATOM-feeds/N50Kartdata_AtomFeedGML.xml"
ZIP = (
    "https://nedlasting.geonorge.no/geonorge/Basisdata/N50Kartdata/GML/"
    f"Basisdata_{KOMMUNE}_{KOMMUNENAVN}_25833_N50Kartdata_GML.zip"
)
SEARCH = "https://kartkatalog.geonorge.no/api/search"
OUT = RAW / "n50"


def main(force: bool = False) -> SourceReport:
    OUT.mkdir(parents=True, exist_ok=True)
    r = SourceReport(name="N50 Kartdata", dataset="Kartverket, uuid ea192681-d039-42ec-b1bc-f3ce04c189ac",
                     license="CC BY 4.0")
    # 1. WFS?
    try:
        hits = http_get_json(SEARCH, {"text": "N50 Kartdata WFS", "limit": 10}).get("Results", [])
        wfs = [h for h in hits if h.get("DistributionProtocol") == "OGC:WFS" and "N50" in (h.get("Title") or "")]
        r.attempt("WFS", SEARCH + "?text=N50 Kartdata WFS", bool(wfs),
                  "ingen N50 WFS registrert i Geonorge" if not wfs else f"{wfs[0]['DistributionUrl']}")
    except Exception as e:  # noqa: BLE001
        r.attempt("WFS", SEARCH, False, f"søk feilet: {e}")
    # 2. Atom
    feed = download_file(ATOM, OUT / "atom_feed.xml", max_age=1 * DAY, force=force, resume=False)
    if ZIP not in feed.read_text(encoding="utf-8", errors="replace"):
        r.attempt("Atom", ATOM, False, "kommunefil 4220/25833 ikke i feed")
        raise RuntimeError("N50 Atom: kommunefil mangler")
    z = download_file(ZIP, OUT / ZIP.rsplit("/", 1)[-1], max_age=7 * DAY, force=force)
    r.attempt("Atom", ZIP, True, "kommunefil GML EPSG:25833")
    r.add_file(z)
    r.route_used = "Atom feed (kommunefil GML)"
    r.ok = True
    return r


if __name__ == "__main__":
    print(json.dumps(main(parse_args()["force"]).to_dict(), indent=1, ensure_ascii=False)[:2000])
