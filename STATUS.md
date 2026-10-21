# STATUS

Versjon: v1.0, frosset 2026-10-21. Neste iterasjon etter tre jaktdager med logg (`/tune`).

## Hva som finnes
- Nettsiden på https://kskjevrak.github.io/jakt/ : kart og lag, oppsett per dag, vær, ruter i begge retninger med «Snu retning», rotasjon, observasjonsbonus, logg, kjerneområder, eksport, offline
- Data og konfig: `data/` bygges av `scripts/download.py` og `scripts/build.py`; regler i `config/habitat.json`, `config/route.json`, `config/steder.json`, `config/start.json`; observasjoner i `data/observasjoner.geojson`; kjerneområder i `config/kjerner.geojson`
- Automatikk: `forecast.yml` hver 6. time, `matrikkel.yml` ukentlig
- Verktøy: `scripts/screenshot.py`, `scripts/plan_cli.js`, `scripts/compare_scores.py`, `scripts/obs_add.py`, `scripts/briefing_data.py`, `scripts/tune_data.py`; kommandoer `/briefing`, `/tune`, `/obs`
- Dokumentasjon: `README.md` (oppdateringsrutine, schema), `DESIGN.md`, `PLAN.md`, `CHANGELOG.md`, `data/SOURCES.md`

## Kjente begrensninger
- FKB-AR5 vektor krever Norge digitalt-rolle; AR5 er rasterisert fra NIBIO sin WMS i 5 m. AR5 er ikke detaljkartlagt over skoggrensa, så myr på platået kommer fra N50
- Blåbærmark finnes ikke som datasett; storfugl-faktoren `blabaermark_proxy` bruker AR5 grunnforhold
- Artskart har bare 4 funn siste 15 år i området
- Overlappmålet under 10 prosent nås ikke der adkomsten er en trang li; samme-dag-straffen er ×3 fordi høyere gir absurde omveier
- Gangtiden (Tobler, 3 km/t flatt, terrengfaktorer) gjør at 7 timer binder før 12 km; justeres i `route.json` under `gange`
- Storfugldagen fra Mele er bratt (400–800 høydemeter på 9–10 km) og Mele–Troddebakken er for kort til gjennomgang; standard er Mele–Enden av vegen med to biler
- Mobiltesten er ikke gjort; strukturen (ark, slicer, GPS-logg) er på plass
- Eksporterte logger og briefinger i `logg/` er gitignored fordi repoet er offentlig
- Ingen nettleser i utviklingsmiljøet; verifisering skjer med `scripts/screenshot.py` (Playwright) og Node-kjøringer
