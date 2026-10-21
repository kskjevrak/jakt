"""Koble jaktlogg (eksportert GeoJSON) til gridceller og sammenlign med habitatscore. Brukes av /tune.

  python scripts/tune_data.py [logg/*.geojson]

For hver registrering: cellens score for arten, høyde, helning, arealtype, treslag, kronedekning, avstander.
Oppsummerer per art: middelscore der fuglene faktisk var mot middelscore i jaktfeltet, og fordelingen
av variablene, slik at Claude kan foreslå justerte vekter i config/habitat.json. Ingen AI-kall her.
"""
from __future__ import annotations

import glob
import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA, CONFIG = ROOT / "data", ROOT / "config"
VARS = ["h", "s", "asp", "at", "tr", "bo", "gf", "st", "th", "kr", "dm", "dsm", "db", "dv", "ds", "dl"]


def main() -> int:
    monster = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "logg" / "*.geojson")
    grid = json.loads((DATA / "grid.geojson").read_text(encoding="utf-8"))
    celler = []
    for f in grid["features"]:
        r = f["geometry"]["coordinates"][0]; p = f["properties"]
        celler.append(((r[0][0] + r[2][0]) / 2, (r[0][1] + r[2][1]) / 2, p))
    kx = 111320 * math.cos(math.radians(58.785)); ky = 110574

    def naermeste(lon, lat):
        best, bd = None, 1e18
        for cx, cy, p in celler:
            d = ((cx - lon) * kx) ** 2 + ((cy - lat) * ky) ** 2
            if d < bd:
                bd, best = d, p
        return best, math.sqrt(bd)

    obs = []
    for fn in glob.glob(monster):
        for f in json.loads(Path(fn).read_text(encoding="utf-8")).get("features", []):
            p = f.get("properties", {}); lon, lat = f["geometry"]["coordinates"][:2]
            c, d = naermeste(lon, lat)
            obs.append({"art": p.get("art"), "type": p.get("type"), "antall": p.get("antall", 1), "tid": p.get("tid"), "avstand_celle_m": round(d), "celle": {k: c.get(k) for k in VARS}, "score": {a: c.get(f"sc_{a}") for a in ("lirype", "orrfugl", "storfugl")}})
    ut = {"antall_registreringer": len(obs), "per_art": {}}
    inne = [f["properties"] for f in grid["features"] if f["properties"].get("inn", 0) >= 0.5]
    for art in ("lirype", "orrfugl", "storfugl"):
        o = [x for x in obs if x["art"] == art]
        if not o:
            continue
        scores = [x["score"][art] for x in o if x["score"][art] is not None]
        middel_felt = st.mean(p[f"sc_{art}"] for p in inne if p.get(f"sc_{art}") is not None)
        ford = {}
        for v in VARS:
            vals = [x["celle"][v] for x in o if isinstance(x["celle"].get(v), (int, float))]
            if vals:
                ford[v] = {"median": st.median(vals), "min": min(vals), "maks": max(vals)}
        ut["per_art"][art] = {"n": len(o), "fugler": sum(x["antall"] or 1 for x in o), "score_ved_funn_middel": round(st.mean(scores), 1) if scores else None,
                              "score_ved_funn_min": min(scores) if scores else None, "middelscore_jaktfelt": round(middel_felt, 1),
                              "andel_funn_under_60": round(sum(1 for s in scores if s < 60) / len(scores), 2) if scores else None,
                              "fordeling": ford, "registreringer": o}
    hab = json.loads((CONFIG / "habitat.json").read_text(encoding="utf-8"))
    ut["habitat_versjon"] = hab.get("versjon"); ut["variabler"] = hab.get("variabler")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(ut, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
