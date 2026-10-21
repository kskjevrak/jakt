"""Samle grunnlaget for en kveldsbriefing som kompakt tekst/JSON. Brukes av /briefing.

  python scripts/briefing_data.py 2026-10-22 [--logg logg/*.geojson]

Skriver: værvarsel per punkt for felttimene (fra data/forecast.json, live fra MET hvis mulig), sol opp og ned,
de beste feltene per art fra data/grid.geojson, kjerneområder, og støkk/felt fra eksporterte logger.
Ingen AI-kall her; Claude leser utskriften og skriver briefingen.
"""
from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA, CONFIG = ROOT / "data", ROOT / "config"


def kompass(g: float) -> str:
    return ["N", "NØ", "Ø", "SØ", "S", "SV", "V", "NV"][round((g % 360) / 45) % 8]


def lokal_time(iso: str) -> tuple[str, int]:
    from zoneinfo import ZoneInfo
    t = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Oslo"))
    return t.strftime("%Y-%m-%d"), t.hour


def vaer(dato: str, h0: int, h1: int) -> dict:
    route = json.loads((CONFIG / "route.json").read_text(encoding="utf-8"))
    fc = None
    try:
        import requests
        s = requests.Session(); s.headers["User-Agent"] = "jakt-bygland/0.1 (+https://github.com/kskjevrak/jakt)"
        fc = {"punkter": {}}
        for p in route["vaer"]["punkter"]:
            r = s.get("https://api.met.no/weatherapi/locationforecast/2.0/compact", params={"lat": f"{p['lat']:.4f}", "lon": f"{p['lon']:.4f}", "altitude": p["hoyde_moh"]}, timeout=30)
            r.raise_for_status(); fc["punkter"][p["id"]] = {"navn": p["navn"], "hoyde_moh": p["hoyde_moh"], "data": r.json()}
        fc["kilde"] = "MET live"
    except Exception:  # noqa: BLE001
        fc = json.loads((DATA / "forecast.json").read_text(encoding="utf-8")); fc["kilde"] = f"fallback hentet {fc.get('hentet')}"
    ut = {"kilde": fc["kilde"], "punkter": {}}
    terskel = route["vaer"]["vind_unngaa_snaufjell_ms"]
    for pid, p in fc["punkter"].items():
        rader = []
        for ts in p["data"]["properties"]["timeseries"]:
            d, h = lokal_time(ts["time"])
            if d != dato or not (h0 <= h <= h1):
                continue
            det = ts["data"]["instant"]["details"]; n1 = ts["data"].get("next_1_hours", {}).get("details", {})
            rader.append({"kl": h, "vind": det.get("wind_speed"), "fra": kompass(det.get("wind_from_direction", 0)), "temp": det.get("air_temperature"), "nedbor": n1.get("precipitation_amount"), "sky": det.get("cloud_area_fraction")})
        if rader:
            ut["punkter"][pid] = {"navn": p.get("navn", pid), "hoyde_moh": p.get("hoyde_moh"), "timer": rader,
                                  "vind_maks": max(r["vind"] for r in rader), "unngaa_snaufjell_kl": [r["kl"] for r in rader if (r["vind"] or 0) >= terskel]}
    sun = json.loads((DATA / "sun.json").read_text(encoding="utf-8")).get("dager", {}).get(dato)
    ut["sol"] = sun
    return ut


def felter(dato: str) -> dict:
    grid = json.loads((DATA / "grid.geojson").read_text(encoding="utf-8"))
    ut = {}
    for art in ("lirype", "orrfugl", "storfugl"):
        celler = [f["properties"] for f in grid["features"] if f["properties"].get("inn", 0) >= 0.5 and f["properties"].get(f"sc_{art}") is not None]
        celler.sort(key=lambda p: -p[f"sc_{art}"])
        topp = celler[:40]
        ut[art] = {"ha_over_60": round(sum(p["inn"] * 0.25 for p in celler if p[f"sc_{art}"] >= 60)),
                   "middel": round(sum(p[f"sc_{art}"] for p in celler) / max(1, len(celler)), 1),
                   "topp_hoyde_moh": [round(sum(p["h"] for p in topp) / len(topp))] if topp else [],
                   "topp_celler": [{"i": p["i"], "j": p["j"], "score": p[f"sc_{art}"], "h": p["h"], "at": p["at"]} for p in topp[:8]]}
    return ut


def logg(monster: str) -> dict:
    ut = defaultdict(list)
    for fn in glob.glob(monster):
        try:
            for f in json.loads(Path(fn).read_text(encoding="utf-8")).get("features", []):
                p = f.get("properties", {}); ut[p.get("art", "ukjent")].append({"type": p.get("type"), "antall": p.get("antall"), "tid": p.get("tid"), "lonlat": f.get("geometry", {}).get("coordinates"), "notat": p.get("notat")})
        except Exception:  # noqa: BLE001
            pass
    return dict(ut)


def main() -> int:
    dato = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else datetime.now().strftime("%Y-%m-%d")
    logg_m = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--logg=")), str(ROOT / "logg" / "*.geojson"))
    h0, h1 = 8, 15
    ut = {"dato": dato, "felttimer": [h0, h1], "vaer": vaer(dato, h0, h1), "habitat": felter(dato),
          "kjerner": json.loads((CONFIG / "kjerner.geojson").read_text(encoding="utf-8")).get("features", []),
          "logg": logg(logg_m), "steder": json.loads((CONFIG / "steder.json").read_text(encoding="utf-8"))["steder"],
          "standard_per_art": json.loads((CONFIG / "route.json").read_text(encoding="utf-8")).get("standard_per_art", {}),
          "generert": datetime.now(timezone.utc).isoformat()}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(ut, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
