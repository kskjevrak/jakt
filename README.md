# Fugledashboard Bygland

Statisk, klientside dashboard for støkkjakt på rype, orrfugl og storfugl på eiendommene 49/1, 49/2, 49/3, 49/4 og 50/1 i Bygland (kommune 4220). Alt kjører som én nettside på GitHub Pages: https://kskjevrak.github.io/jakt/

Tung geoprosessering gjøres lokalt i Python og commites som ferdige, klippede filer i `data/`. Nettsiden leser disse pluss åpne live-tjenester fra Kartverket, NIBIO, MET og Artsdatabanken. Ingen backend, ingen nøkler, ingen analyse­verktøy.

## Innhold

| Mappe eller fil | Hva |
|---|---|
| `index.html` | Hele appen i ett dokument: kart, oppsett, vær, ruter, rotasjon, logg, eksport. `sw.js` gir offline-støtte, `manifest.webmanifest` gjør den installerbar |
| `kontroll.html` | Enkel kontrollside for jaktfelt, score-lag og myr |
| `config/habitat.json` | Habitatregler: høydesoner, terskler, klasser, vekter og straffer per art. Fargeskala. Regel for kjerneområder |
| `config/route.json` | Rutebudsjetter per form, gangfart, feltvalg, samme-dag-straff, rotasjon, loggbonus, støkk-kalibrering, værpunkter, standard start og slutt per art |
| `config/start.json`, `config/steder.json` | Startpunkter og faste steder (Hukebu) |
| `config/kjerner.geojson` | Kjerneområder fra lokalkunnskap. Fylles fra nettsiden («Tegn kjerneområde» → «Last ned kjerner.geojson»). Positiv bonus løfter, negativ bonus eller notat «ingen fugl» trekker ned |
| `data/` | Ferdige filer nettsiden leser: jaktfelt, teiger, naboteiger, N50-lag, Artskart-funn, score-rastere (COG + PNG), `grid.geojson` med 50 m-celler, værfallback, `observasjoner.geojson`, `turer.geojson` med gåtte GPS-spor. `SOURCES.md` dokumenterer hver kilde |
| `scripts/` | Henting og bygging, se under |
| `raw/` | Rådata og mellomprodukter, gitignored |
| `DESIGN.md`, `PLAN.md`, `STATUS.md` | Designtokens, plan og status |

## Oppdatere data

Alt bygges fra rådata med to kommandoer. Venv-et er Python 3.12 via `uv`; pakkene står pinnet i `requirements.txt`.

```
.venv\Scripts\python.exe scripts\download.py      # henter alle kilder, cacher i raw/, skriver data/SOURCES.md
.venv\Scripts\python.exe scripts\build.py         # jaktfelt → 10 m-rastere → score, PNG, COG, grid.geojson
git add data config && git commit -m "Oppdater data" && git push
```

`download.py --only=<kilde>` eller `--skip=<kilde>` begrenser kjøringen, `--force` ignorerer cachen. Kildene er `teig`, `n50`, `artskart`, `dtm`, `ar5`, `sr16`. Hvert hentescript prøver i rekkefølge WFS/WCS/REST, Atom-feed og nedlastings-API, og dokumenterer hva som fungerte i `data/SOURCES.md`.

Førstegangs oppsett:

```
python -m pip install --user uv
python -m uv python install 3.12
python -m uv venv .venv --python 3.12
python -m uv pip install --python .venv -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium     # bare for skjermbilder
```

### Når NIBIO slipper ny SR16 eller AR5

1. `scripts/download.py --only=sr16 --force` henter fylkesfilen på nytt via NIBIO sitt nedlastings-API og klipper båndene til området. Filen er rundt 1,9 GB og ligger i `raw/sr16/`.
2. AR5 hentes som 5 m-raster fra NIBIO sin AR5 WMS, fordi FKB-AR5 vektor krever Norge digitalt-rolle. `scripts/download.py --only=ar5 --force` henter på nytt og sjekker fargekodingen mot GetFeatureInfo. Har du en Geonorge-bruker med FKB-tilgang, kan Bygland-filen (GML, EPSG:25833) legges i `raw/ar5/manual/`.
3. Kjør `scripts/build.py`. Grid og score bygges på nytt; `scripts/compare_scores.py` viser hva som endret seg mot forrige versjon og hvor.
4. Commit `data/` og push. Pages oppdateres automatisk. Nettsiden kaster lagrede ruter når grid-tidsstempelet endres.

### Habitatregler

Endre `config/habitat.json`, øk `versjon`, kjør `scripts/build_scores.py` og `scripts/compare_scores.py`, og se på `raw/preview/score_<art>.png`. Nettsiden leser samme fil, så terskler og vekter i panelet følger med. Kommandoen `/tune` i Claude Code leser eksporterte jaktlogger og foreslår justeringer.

### Automatikk i GitHub Actions

- `forecast.yml` henter MET-varselet hver 6. time og commiter `data/forecast.json` og `data/sun.json` bare ved endring. Nettsiden bruker filene når direktekallet til MET feiler.
- `matrikkel.yml` henter teigene fra Kartverkets WFS hver mandag og commiter `data/jaktfelt.geojson` med venner bare når geometrien er endret.

### Artskart

`scripts/refresh_artskart.py` henter funn av lirype, orrfugl og storfugl siste 15 år på nytt når som helst.

## Observasjonsdatabasen

`data/observasjoner.geojson` er sannheten for egne og andres fugleobservasjoner. Den er versjonert i git og leses av nettsiden. Dette er noe annet enn jaktloggen i nettleseren, som er lokal og privat (`logg/` er gitignored).

Schema per feature:

| Felt | Verdier |
|---|---|
| `id` | lages av scriptet, `o-ÅÅÅÅMMDD-nn` |
| `dato` | ISO-dato |
| `dato_usikker` | `true` når datoen er omtrentlig |
| `art` | `lirype`, `orrfugl`, `storfugl`, `ukjent_honsefugl` |
| `kjonn` | `tiur`, `roy`, `ukjent` |
| `antall` | tall eller `null` |
| `type` | `sett`, `stokket`, `felt`, `spor`, `omrade` |
| `kilde` | navnet på den som så det |
| `presisjon_m` | tall eller `null` |
| `notat` | fritekst |
| geometri | `Point` eller `Polygon` i WGS84 |

Legg inn nye med `/obs <fritekst>` i Claude Code (strukturerer, viser tabell, commiter etter godkjenning) eller direkte:

```
.venv\Scripts\python.exe scripts\obs_add.py nye.geojson --tabell   # kontroller
.venv\Scripts\python.exe scripts\obs_add.py nye.geojson            # legg inn, så commit
.venv\Scripts\python.exe scripts\obs_add.py logg.geojson --fra-logg # promoter en eksportert jaktlogg
```

Nettsiden kan også laste ned loggen direkte i dette schemaet («Last ned som observasjoner»), så en logg promoteres med én kommando.

## Gåtte turer

Eksporter aktiviteten som GPX fra Garmin Connect (eller en annen klokke) og legg filen i `logg/turer/` (gitignored, rådataene med puls og sekundpunkter blir liggende lokalt). Kjør

```
.venv\Scripts\python.exe scripts\import_turer.py            # alle logg/turer/*.gpx → data/turer.geojson
.venv\Scripts\python.exe scripts\import_turer.py --tabell   # bare vis tabellen
```

Scriptet forenkler sporet (Douglas–Peucker, 6 m), regner km og høydemeter på det fulle sporet, og skriver `data/turer.geojson` med dato, start, slutt, km, høydemeter, andel innenfor jaktfeltet og sekunder fra start per punkt. Filen commites, så laget «Gått» vises for alle. Scriptet bygger filen på nytt fra alle GPX-filene hver gang.

I nettsiden ligger turene i laget «Gått» (på som standard). Klikk på sporet for nøkkeltall. Observasjoner i ettertid: trykk Støkk eller Felt, velg «Klikk i kartet» og klikk på sporet der det skjedde. Dato og klokkeslett foreslås fra nærmeste punkt på sporet (innen 80 m) og kan endres i dialogen. «Last ned som observasjoner» og `scripts/obs_add.py` tar dem videre inn i databasen.

I nettsiden vises databasen som laget «Observasjoner» (på som standard på stor skjerm, av på telefon): ikon per art i artsfarge med dekkevne etter alder, polygoner som tynt omriss. I planleggeren gir observasjonene bonus i cellene innen 300 m av et punkt eller inne i et polygon pluss 150 m, vektet etter alder i forhold til plandagen (0 til 14 dager 1,0, 15 til 60 dager 0,5, samme måned tidligere år 0,25, ellers 0,1). Ukjent hønsefugl gir bonus til rype og orrfugl. Bonusen legges til etter habitatmodellen, maks pluss 20, og vises for seg i cellepopupen («modell 62, observasjoner +12»). Loggregistreringene i nettleseren går gjennom samme mekanisme. Alle tall står i `config/route.json` under `observasjoner`.

## Nettsiden

- Oppsettet (dato, dager, art, start, slutt og sløyfe per dag, form) lagres i nettleseren og i lenka, så det kan deles. `auto=1` i lenka får siden til å legge rutene selv. Standard er tre dager i rekkefølgen fra `config/route.json`: storfugl som gjennomgang Mele til Enden av vegen med to biler (snudd ved sørlig morgenvind ved fjorden), deretter rype og orrfugl som rundtur fra Troddebakken. Storfugl først fordi beltet langs lia da er urørt.
- Ruter legges per dag innenfor km, høydemeter og timer fra `config/route.json`. Målfelt er de høyest scorede sammenhengende feltene for dagens art, gjennomgått i parallelle drag. Celler ruten har passert samme dag straffes slik at returen går en annen vei. Dager etter hverandre roterer med halveringstid. Overlapp og andel i gode celler vises per dag.
- Loggen (Støkk, Felt) bruker GPS, lagres i nettleseren og lastes ned som GeoJSON. Registreringene gir bonus i cellene rundt for neste dags rute. Eksporterte logger i `logg/` brukes av `/briefing` og `/tune`.
- Kjerneområder tegnes i kartet og lastes ned i formatet til `config/kjerner.geojson`. Legg filen i `config/` og commit, så gjelder den for alle. Positiv bonus løfter score i cellene (score + bonus × (100 − score)), negativ trekker ned (score + bonus × score, så −0,3 gjør 80 til 56); avkrysningen «Ingen fugl her» setter standardtrekket. I filen kan feltet hete `bonus` eller `bonus_faktor`; mangler tallet, trekker et notat med «ingen fugl» ned. Tom `arter`-liste betyr alle arter. Negative kjerner er grå i kartet, og cellepopupen viser «kjerner −12». Tallene står i `config/habitat.json` under `kjerner`, og `scripts/plan_cli.js` bruker kjernene på samme måte som nettsiden.
- Offline: service workeren cacher appen, konfig, datafiler, siste varsel og kartflisene du har sett. Statusmerket øverst i panelet viser «Offline-klar».

## Verktøy

- `scripts/screenshot.py --dag 1` tar et ekte skjermbilde av Pages-siden i Chromium med standardoppsettet og lagrer `raw/preview/skjermbilde_dag1.png`. `--url http://127.0.0.1:8765/` tester lokalt (start `python -m http.server 8765` i prosjektmappa). Brukes som visuell regresjonstest.
- `scripts/compare_scores.py` sammenligner `data/grid.geojson` med en tidligere kopi.
- `/briefing <dato>` og `/tune` i Claude Code, definert i `.claude/commands/`.

## Kilder og lisenser

Kartverket (Matrikkelen Teig, N50, NHM DTM, topografisk WMTS) CC BY 4.0. NIBIO (AR5 WMS, SR16) CC BY 4.0 / NLOD. MET Norge (Locationforecast, Sunrise) NLOD 2.0 / CC BY 4.0. Artsdatabanken (Artskart) CC BY 4.0 per datasett. Nøyaktige URL-er, datoer og versjoner står i `data/SOURCES.md`.
