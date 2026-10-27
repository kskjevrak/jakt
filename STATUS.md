# STATUS

Versjon: v1.1, 2026-10-27: gåtte GPS-spor og negativ bonus i kjerneområder. Neste iterasjon etter tre jaktdager med logg (`/tune`).

## Hva som finnes
- Nettsiden på https://kskjevrak.github.io/jakt/ : kart og lag, oppsett per dag, vær, ruter i begge retninger med «Snu retning», rotasjon, observasjonsbonus, logg med datofelt, kjerneområder som løfter eller trekker ned, laget «Gått» med dato og klokkeslett foreslått fra sporet, eksport, offline
- Gåtte turer: `scripts/import_turer.py` leser GPX fra `logg/turer/` og skriver `data/turer.geojson` (to turer 24. og 25. oktober 2026 importert)
- Data og konfig: `data/` bygges av `scripts/download.py` og `scripts/build.py`; regler i `config/habitat.json`, `config/route.json`, `config/steder.json`, `config/start.json`; observasjoner i `data/observasjoner.geojson`; kjerneområder i `config/kjerner.geojson`
- Automatikk: `forecast.yml` hver 6. time, `matrikkel.yml` ukentlig
- Verktøy: `scripts/screenshot.py`, `scripts/plan_cli.js`, `scripts/compare_scores.py`, `scripts/obs_add.py`, `scripts/import_turer.py`, `scripts/briefing_data.py`, `scripts/tune_data.py`; kommandoer `/briefing`, `/tune`, `/obs`
- Dokumentasjon: `README.md` (oppdateringsrutine, schema), `DESIGN.md`, `PLAN.md`, `CHANGELOG.md`, `data/SOURCES.md`

## Kjente begrensninger
- FKB-AR5 vektor krever Norge digitalt-rolle; AR5 er rasterisert fra NIBIO sin WMS i 5 m. AR5 er ikke detaljkartlagt over skoggrensa, så myr på platået kommer fra N50
- Blåbærmark finnes ikke som datasett; storfugl-faktoren `blabaermark_proxy` bruker AR5 grunnforhold
- Artskart har bare 4 funn siste 15 år i området
- Overlappmålet under 10 prosent nås ikke der adkomsten er en trang li; samme-dag-straffen er ×3 fordi høyere gir absurde omveier
- Gangtiden (Tobler, 3 km/t flatt, terrengfaktorer) gjør at 7 timer binder før 12 km; justeres i `route.json` under `gange`
- Storfugldagen fra Mele er bratt (400–800 høydemeter på 9–10 km) og Mele–Troddebakken er for kort til gjennomgang; standard er Mele–Enden av vegen med to biler
- Mobiltesten er ikke gjort; strukturen (ark, slicer, GPS-logg) er på plass
- Eksporterte logger, briefinger og rå GPX i `logg/` er gitignored fordi repoet er offentlig; det forenklede sporet i `data/turer.geojson` er derimot offentlig
- Gåtte spor påvirker ikke rotasjonen i planleggeren ennå; bare planlagte ruter straffer celler neste dag

## Til neste `/tune`
- Orrfugl-sitteplass o-20261025-01 (25.10.2026) ligger på 773 moh i åpen fastmark i overgang lyng og bjørkekratt. Modellen gir orrfugl 23 der, og høydesonen i `config/habitat.json` slutter på 700–760 moh. Ett funn er ikke nok alene, men peker mot høyere øvre grense for orrfugl. Kjerneområdet «Sitteplass orrfugl» (150 m, bonus 0,5) dekker det inntil videre
- Ingen nettleser i utviklingsmiljøet; verifisering skjer med `scripts/screenshot.py` (Playwright) og Node-kjøringer
