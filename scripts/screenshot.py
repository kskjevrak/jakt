"""Ta skjermbilde av dashboardet med et gitt oppsett, slik det faktisk tegnes i Chromium.

  python scripts/screenshot.py --navn dag1 --dag 1
  python scripts/screenshot.py --navn dag3 --dag 3 --url http://127.0.0.1:8765/
  python scripts/screenshot.py --navn test --hash "dato=2026-10-22&dager=3&arter=lirype,orrfugl,storfugl&d1=troddebakken:samme:0&d2=troddebakken:samme:0&d3=auto:auto:&auto=1&dag=1"

Standardoppsettet er tre dager fra dagens dato i rekkefølgen fra config/route.json: storfugl gjennomgang
Mele–Enden av vegen (snudd ved sørlig morgenvind), så rype og orrfugl fra Troddebakken. `auto=1` i hashen får siden til å legge rutene selv.
Scriptet venter til window.__jakt.klar og window.__jakt.ruterKlare er sanne og kartet er ferdig tegnet,
skriver eventuelle konsollfeil, og lagrer PNG til raw/preview/<navn>.png. Kan brukes som visuell regresjonstest.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "raw" / "preview"


def standard_hash(dag: int, dato: str | None) -> str:
    d = dato or date.today().isoformat()
    # standard order from config/route.json standard_dager: storfugl through-route first, then rype and orrfugl from Troddebakken
    return (f"dato={d}&dager=3&jegere=2&form=normal&tid=08:00&timer=7&arter=storfugl,lirype,orrfugl"
            f"&d1=auto:auto:&d2=auto:auto:&d3=auto:auto:&auto=1&dag={dag}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://kskjevrak.github.io/jakt/")
    ap.add_argument("--hash", dest="hash_", default=None, help="URL-hash uten #; erstatter standardoppsettet")
    ap.add_argument("--dag", type=int, default=1)
    ap.add_argument("--dato", default=None, help="første jaktdag, standard i dag")
    ap.add_argument("--navn", default=None, help="filnavn uten .png, standard skjermbilde_dag<N>")
    ap.add_argument("--bredde", type=int, default=1440)
    ap.add_argument("--hoyde", type=int, default=900)
    ap.add_argument("--mork", action="store_true", help="mørk modus")
    ap.add_argument("--ventetid", type=int, default=180, help="maks sekunder å vente på ruter")
    a = ap.parse_args()
    h = a.hash_ or standard_hash(a.dag, a.dato)
    url = a.url.rstrip("/") + "/#" + h
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{a.navn or f'skjermbilde_dag{a.dag}'}.png"
    feil: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": a.bredde, "height": a.hoyde}, device_scale_factor=1,
                                  color_scheme="dark" if a.mork else "light", locale="nb-NO")
        page = ctx.new_page()
        page.on("console", lambda m: feil.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: feil.append(f"pageerror: {e}"))
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_function("window.__jakt && window.__jakt.klar && window.__jakt.ruterKlare", timeout=a.ventetid * 1000)
        page.evaluate("new Promise(r => { if (map.loaded() && !map.isMoving()) r(1); else map.once('idle', () => r(1)); })")
        page.wait_for_timeout(900)  # rutetegningen tar 600 ms
        page.screenshot(path=str(out))
        stats = page.evaluate("(() => { const r = RUTE.dager[state.dag]; return r ? { dag: r.dag, art: r.art, feil: r.feil || null, km: r.stats && r.stats.m / 1000, hm: r.stats && r.stats.up, t: r.stats && r.stats.t / 3600, over60: r.stats && r.stats.andelOver60, overlapp: r.stats && r.stats.overlapp, forslag: r.forslag || null } : null; })()")
        browser.close()
    print(f"lagret {out}")
    if stats:
        print(f"dag {stats['dag']} {stats['art']}: " + (stats['feil'] or f"{stats['km']:.1f} km, {stats['hm']:.0f} hm, {stats['t']:.1f} t, {stats['over60'] * 100:.0f} % over 60, overlapp {stats['overlapp']:.1f} %") + (f" | forslag: {stats['forslag']}" if stats['forslag'] else ""))
    for f in feil:
        print("  ", f[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
