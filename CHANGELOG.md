# Endringslogg

## v1.0, 2026-10-21

Første frosne versjon av fugledashboardet for Bygland.

- Data: Matrikkel Teig (WFS), N50 (Atom), NHM DTM (WCS), AR5 (NIBIO WMS rasterisert), SR16 (NIBIO nedlastings-API), Artskart (REST). Alt hentet maskinelt med cache og dokumentert i `data/SOURCES.md`. Jaktfelt 2139 ha på 49/1–4 og 50/1
- Habitatmodell v3b per art i `config/habitat.json`, 10 m-rastere og 50 m-grid, score-PNG og COG, dominerende art
- Nettside i ett dokument: Kartverket topo, score-lag, N50-lag, sannhetslag fra NIBIO og Kartverket, oppsett per dag med standard per art, MET-vær med vindpiler og «unngå snaufjell», ruteplanlegger med felt og parallelle drag, samme-dag-straff, rotasjon mellom dager, begge retninger vurdert mot vind i dragene og overlapp med «Snu retning», automatisk alternativ når opplegget ikke gir rute, jaktlogg med GPS, kjerneområder tegnet i kartet, observasjonsdatabase med aldersvektet bonus, GPX og PNG, offline med service worker, lys og mørk modus
- Observasjonsdatabase `data/observasjoner.geojson` med schema, `/obs`, `scripts/obs_add.py`
- Automatikk: værfallback hver 6. time, ukentlig matrikkelsjekk
- Verktøy: `scripts/screenshot.py` (Playwright), `scripts/plan_cli.js` (planlegger uten nettleser), `/briefing`, `/tune`
