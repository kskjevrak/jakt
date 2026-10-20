"""Fetch MET Locationforecast (compact) for the three weather points and MET Sunrise for the next days.

Writes data/forecast.json and data/sun.json. Used by .github/workflows/forecast.yml every 6 hours as
a fallback for the browser, which normally calls api.met.no directly. Only needs `requests`.
Respects MET's terms: identifying User-Agent, If-Modified-Since via the cached Last-Modified.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "config"
UA = "jakt-bygland/0.1 (+https://github.com/kskjevrak/jakt)"
LF = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
SUN = "https://api.met.no/weatherapi/sunrise/3.0/sun"
DAYS_SUN = 10


def oslo_offset(d: date) -> str:
    off = datetime(d.year, d.month, d.day, 12, tzinfo=ZoneInfo("Europe/Oslo")).utcoffset() or timedelta(0)
    s = int(off.total_seconds()); sign = "+" if s >= 0 else "-"; s = abs(s)
    return f"{sign}{s // 3600:02d}:{(s % 3600) // 60:02d}"


def main() -> int:
    route = json.loads((CONFIG / "route.json").read_text(encoding="utf-8"))
    pts = route["vaer"]["punkter"]
    s = requests.Session(); s.headers["User-Agent"] = UA
    prev = {}
    fp = DATA / "forecast.json"
    if fp.exists():
        try:
            prev = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
    out = {"hentet": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "kilde": "MET Norge Locationforecast 2.0 compact",
           "lisens": "NLOD 2.0 / CC BY 4.0", "punkter": {}}
    changed = False
    for p in pts:
        params = {"lat": f"{p['lat']:.4f}", "lon": f"{p['lon']:.4f}", "altitude": int(p["hoyde_moh"])}
        headers = {}
        old = (prev.get("punkter") or {}).get(p["id"])
        if old and old.get("last_modified"):
            headers["If-Modified-Since"] = old["last_modified"]
        r = s.get(LF, params=params, headers=headers, timeout=60)
        if r.status_code == 304 and old:
            out["punkter"][p["id"]] = old
            continue
        r.raise_for_status()
        out["punkter"][p["id"]] = {"navn": p["navn"], "lat": p["lat"], "lon": p["lon"], "hoyde_moh": p["hoyde_moh"],
                                   "expires": r.headers.get("Expires"), "last_modified": r.headers.get("Last-Modified"),
                                   "data": r.json()}
        changed = True
    if changed or not fp.exists():
        fp.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print("forecast.json oppdatert")
    else:
        print("forecast.json uendret (304 for alle punkter)")

    # sun times for the central point, next DAYS_SUN days
    c = next((p for p in pts if p["id"] == "litjonni"), pts[0])
    sun = {"hentet": out["hentet"], "kilde": "MET Norge Sunrise 3.0", "punkt": {"lat": c["lat"], "lon": c["lon"]}, "dager": {}}
    today = date.today()
    sp = DATA / "sun.json"
    old_sun = {}
    if sp.exists():
        try:
            old_sun = json.loads(sp.read_text(encoding="utf-8")).get("dager", {})
        except json.JSONDecodeError:
            old_sun = {}
    for i in range(DAYS_SUN):
        d = today + timedelta(days=i)
        key = d.isoformat()
        if key in old_sun:
            sun["dager"][key] = old_sun[key]
            continue
        r = s.get(SUN, params={"lat": f"{c['lat']:.4f}", "lon": f"{c['lon']:.4f}", "date": key, "offset": oslo_offset(d)}, timeout=60)
        if r.ok:
            pr = r.json().get("properties", {})
            sun["dager"][key] = {"soloppgang": pr.get("sunrise", {}).get("time"), "solnedgang": pr.get("sunset", {}).get("time"),
                                 "solhoyde_middag": pr.get("solarnoon", {}).get("disc_centre_elevation")}
    sp.write_text(json.dumps(sun, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"sun.json: {len(sun['dager'])} dager")
    return 0


if __name__ == "__main__":
    sys.exit(main())
