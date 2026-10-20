"""Fetch every data source machine-readably, in the order required by the brief.

Usage:
  python scripts/download.py                 # everything (cached)
  python scripts/download.py --only teig,n50 # subset
  python scripts/download.py --skip sr16     # skip the 1.85 GB county raster
  python scripts/download.py --force         # ignore cache

Order: teig -> build_jaktfelt (AOI) -> n50 -> artskart -> dtm -> ar5 -> sr16
Writes data/SOURCES.md and data/sources.json, prints a per-source report.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, SourceReport, human, log, write_reports  # noqa: E402

ORDER = ["teig", "n50", "artskart", "dtm", "ar5", "sr16"]


def run(name: str, force: bool) -> SourceReport:
    import importlib

    mod = importlib.import_module(f"fetch_{name}")
    t0 = time.time()
    try:
        rep = mod.main(force=force)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        rep = SourceReport(name=name, dataset="", license="")
        rep.notes.append(f"UNNTAK: {e}")
        rep.notes.append(traceback.format_exc()[-1500:])
        rep.ok = False
    rep.notes.append(f"Kjøretid {time.time() - t0:.0f} s")
    if name == "teig" and rep.ok:
        import build_jaktfelt

        s = build_jaktfelt.main()
        rep.notes.append(f"Jaktfelt {s['areal_ha']} ha, {s['teiger']} teiger + {s['festeteiger']} festeteiger, "
                         f"{s['naboteiger']} naboteiger innen 500 m")
        if s["mangler_rest_punkt_i_polygon"]:
            rep.notes.append(f"ADVARSEL: REST-teigpunkter utenfor polygon: {s['mangler_rest_punkt_i_polygon']}")
        if s["flagget"]:
            rep.notes.append(f"Flagget: {s['flagget']}")
    return rep


def main(argv: list[str]) -> int:
    force = "--force" in argv
    only = next((a.split("=", 1)[1] for a in argv if a.startswith("--only=")), None)
    skip = next((a.split("=", 1)[1] for a in argv if a.startswith("--skip=")), "")
    names = [n for n in ORDER if (not only or n in only.split(",")) and n not in skip.split(",")]
    reports: list[SourceReport] = []
    for n in names:
        log(f"==== {n} ====")
        reports.append(run(n, force))
    # keep previous reports for sources not run this time (read late so parallel runs merge)
    prev = []
    if (DATA / "sources.json").exists():
        try:
            prev = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = []
    done = {r.name for r in reports}
    merged = reports + [SourceReport(**{k: v for k, v in p.items() if k != "attempts"},
                                     attempts=[]) for p in prev if p["name"] not in done and
                        not any(p["name"].lower().startswith(n) for n in names)]
    for p in prev:
        if p["name"] not in done:
            for r in merged:
                if r.name == p["name"]:
                    from common import Attempt
                    r.attempts = [Attempt(**a) for a in p.get("attempts", [])]
    write_reports(merged)
    print("\n| Kilde | Vei | Størrelse | Datert | OK |")
    print("|---|---|---|---|---|")
    for r in merged:
        dated = ", ".join(sorted({f["last_modified"] for f in r.files if f["last_modified"]})) or r.version or "–"
        print(f"| {r.name} | {r.route_used or 'INGEN'} | {human(r.total_size())} | {dated} | {'ja' if r.ok else 'NEI'} |")
    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
