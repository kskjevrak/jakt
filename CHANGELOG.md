# Endringslogg

## v1.1, 2026-10-27

- Gåtte turer: `scripts/import_turer.py` leser GPX fra `logg/turer/` (Garmin Connect), forenkler og skriver `data/turer.geojson`. Laget «Gått» i kartet med popup. Loggdialogen har fått datofelt, og et klikk på sporet foreslår dato og klokkeslett derfra
- Kjerneområder kan trekke ned: `bonus` eller `bonus_faktor` under 0, eller notat med «ingen fugl», gir score + faktor × score. Grå i kartet, «kjerner −12» i cellepopupen, avkrysning «Ingen fugl her» i tegnedialogen. `standard_trekk`, `maks_trekk` og `trekk_notat` i `config/habitat.json`. `scripts/plan_cli.js` bruker nå kjernene som nettsiden
- Service worker v4 cacher også `data/turer.geojson` og `data/observasjoner.geojson`
- Observasjonsschema: `kjonn` kan være `hann` eller `hunn` for orrfugl og rype. Første oppføring med spor-type fra felt: sitteplass orrfugl 25.10, og første kjerneområde i `config/kjerner.geojson` (150 m rundt sitteplassen, bonus 0,5)
- Planleggeren lar celler som et kjerneområde løfter for arten slippe gjennom høydeporten (`krev_hoydesone`), så lokalkunnskap kan gi målfelt utenfor modellens høydesone
- `/tune` og `scripts/tune_data.py` leser også punktene i `data/observasjoner.geojson`

## v1.0, 2026-10-21

Første frosne versjon av fugledashboardet for Bygland.

- Data: Matrikkel Teig (WFS), N50 (Atom), NHM DTM (WCS), AR5 (NIBIO WMS rasterisert), SR16 (NIBIO nedlastings-API), Artskart (REST). Alt hentet maskinelt med cache og dokumentert i `data/SOURCES.md`. Jaktfelt 2139 ha på 49/1–4 og 50/1
- Habitatmodell v3b per art i `config/habitat.json`, 10 m-rastere og 50 m-grid, score-PNG og COG, dominerende art
- Nettside i ett dokument: Kartverket topo, score-lag, N50-lag, sannhetslag fra NIBIO og Kartverket, oppsett per dag med standard per art, MET-vær med vindpiler og «unngå snaufjell», ruteplanlegger med felt og parallelle drag, samme-dag-straff, rotasjon mellom dager, begge retninger vurdert mot vind i dragene og overlapp med «Snu retning», automatisk alternativ når opplegget ikke gir rute, jaktlogg med GPS, kjerneområder tegnet i kartet, observasjonsdatabase med aldersvektet bonus, GPX og PNG, offline med service worker, lys og mørk modus
- Observasjonsdatabase `data/observasjoner.geojson` med schema, `/obs`, `scripts/obs_add.py`
- Automatikk: værfallback hver 6. time, ukentlig matrikkelsjekk
- Verktøy: `scripts/screenshot.py` (Playwright), `scripts/plan_cli.js` (planlegger uten nettleser), `/briefing`, `/tune`
