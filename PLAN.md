# PLAN – Fugledashboard for støkkjakt i Bygland

Statisk, klientside dashboard på GitHub Pages (`kskjevrak/jakt`). Tung geoprosessering
kjøres lokalt i Python og commites som ferdige, klippede datafiler. Nettsiden leser disse
pluss åpne live-tjenester (Kartverket, NIBIO, MET, Artskart). Ingen backend, ingen nøkler.

## 1. Mappestruktur

```
index.html                 # hele appen, vanilla JS + MapLibre GL JS (låst versjon fra cdnjs)
sw.js                      # service worker (offline: siste kart, grid, vær)
manifest.webmanifest
DESIGN.md                  # tokens (farger, spacing, typografi, easing) – skrives før første UI-commit
config/habitat.json        # høydesoner, helning, avstander, vekter per art
config/route.json          # km/høydemeter per form, halveringstid rotasjon, jegeravstand, støkk-kalibrering
data/jaktfelt.geojson      # dissolvet jaktfelt (WGS84)
data/naboteiger.geojson    # naboteiger innen 500 m, gnr/bnr som attributt
data/grid.geojson          # 50 m celler med alle attributter (< 10 MB, ellers topojson/flatgeobuf)
data/score_<art>.png/.tif  # score 0–100 per art, 10 m (PNG for kartet + COG for GIS)
data/vann.geojson, bekker.geojson, stier.geojson   # N50, klippet
data/artskart.geojson      # funn siste 15 år
data/forecast.json, sun.json                       # fallback fra GitHub Action
data/SOURCES.md            # URL, dato, versjon, hva som feilet
scripts/                   # download.py (alle kilder), build.py (alt fra raw/), fetch_*.py per kilde,
                           # build_grid.py, build_scores.py, refresh_artskart.py, fetch_forecast.py
raw/                       # rådata, gitignored
.github/workflows/         # forecast.yml (hver 6. time), matrikkel.yml (ukentlig)
.claude/commands/          # briefing.md, tune.md
```

## 2. Datapipeline (Python, lokalt)

Rekkefølge per kilde: WFS/WCS/REST → Atom feed → Geonorge nedlastings-API → manuelt (siste utvei,
dokumentert i `data/SOURCES.md`). Hvert hentescript cacher på URL + ETag/Last-Modified i `raw/`.

| # | Kilde | Primærvei | Fallback | Bruk |
|---|-------|-----------|----------|------|
| 1 | Matrikkel Teig | Kartverket WFS, filter kommune 4220 + gnr/bnr | Atom feed uuid 74340c24… | jaktfelt, naboteiger. Valideres mot Eiendom REST-API |
| 2 | FKB-AR5 | NIBIO WFS / Geonorge nedlasting 4220 | Atom | arealtype, myr, treslag, bonitet |
| 3 | SR16 raster 16 m | NIBIO Atom (Agder) | nedlastings-API | treslag, middelhøyde, volum, bonitet |
| 4 | DTM 10 m | Kartverket høyde-WCS, bbox UTM33 | nedlastings-API «DTM 10» | høyde, helning, eksposisjon, TPI. Topper sjekkes mot hoydedata-API |
| 5 | N50 | Kartverket WFS / Atom 4220 | – | vann, bekker, stier |
| 6 | Artskart | publicapi Observations/list med gmWktPolygon | – | funn per art, dato, antall, kilde |

Avledning: alt reprojiseres til EPSG:25833, klippes til jaktfelt + 500 m buffer. DTM 10 m gir
helning, eksposisjon og TPI (rygg/dal). Avstandsrastere til myr (AR5) og bekk (N50). Score per art =
vektet sum av regel-funksjoner fra `config/habitat.json` (trapes-/terskelfunksjoner på høyde,
helning, avstand, arealtype, treslag, trehøyde, bonitet), skalert 0–100. 50 m-grid aggregerer
rasterverdiene (median/andel) og bærer score per art. Celler uten data merkes «ukjent», ikke gjettet.

## 3. Nettsiden (byggerekkefølge)

1. Kart og lag: Kartverket WMTS topo, jaktfelt, naboteiger (rød skravur), score per art, N50-lag,
   Artskart-punkter, NIBIO/Kartverket WMS som «sannhetslag».
2. Oppsettpanel: dato, dager, jegere, starttid/timer, startpunkt, art per dag, form → localStorage + URL-hash.
3. Vær: MET Locationforecast compact for tre punkter (fjord 250, Litjønni 670, Hakefjellet 850 moh),
   Sunrise 3.0, cache i localStorage med Expires, fallback `data/forecast.json`. Vind > 10 m/s på fjellet
   markeres «unngå snaufjell» (terskel i config).
4. Rute: celle-graf (8-nabo, kostnad = avstand × helningsfaktor, forbudt utenfor jaktfelt/i vann).
   Velg målklynger etter score (minus rotasjonsstraff, pluss loggbonus), koble med korteste vei
   innenfor km/høydemeter-budsjett, start/slutt i startpunkt. Polygonkjede = korridor rundt senterlinje,
   to spor ±30 m, gangretning valgt slik at inngang i beste partier skjer mot vinden.
5. Rotasjon: besøkte celler straffes med konfigurerbar halveringstid; «sist besøkt»-skravur.
6. Logg: støkk/felt med GPS, art, antall, tid → localStorage, eksport/import GeoJSON, loggbonus i score.
7. Eksport: GPX (rute + begge spor), PNG av kart.
8. Offline: service worker som cacher app, data og siste vær.
9. Lys/mørk modus, norsk UI, `prefers-reduced-motion`. Design etter `emil-design-eng` og DESIGN.md.

## 4. Automatisering

- `forecast.yml`: hver 6. time, henter MET med identifiserende User-Agent, commiter `data/forecast.json` + `sun.json` kun ved endring.
- `matrikkel.yml`: ukentlig WFS-henting, commiter kun ved endret geometri.
- GitHub Pages fra `main`, rot `/`.

## 5. Slash-kommandoer

- `/briefing <dato>`: leser forecast, grid, logg → kort kveldsbriefing på norsk.
- `/tune`: leser jaktlogg → foreslår justerte vekter i `config/habitat.json` med begrunnelse.

## 6. Milepæler og stoppunkter

1. Plan + spørsmål (dette dokumentet) ✔
2. Repo-oppsett, venv, `download.py` kjørt, rapport per kilde
3. **Stopp:** `jaktfelt.geojson` vist i minimalt kart, du verifiserer grensene
4. Grid + score-rastere
5. Nettside trinn 1–9
6. Pages + Actions, README, slash-kommandoer

## 7. Antakelser (si ifra hvis noe er feil)

- Dokumentasjon og UI på norsk bokmål, kode og commit-meldinger på engelsk.
- Score-raster leveres som én georeferert PNG per art (MapLibre image source) pluss COG. Ikke flistjeneste; området er lite nok.
- `index.html` holdes som ett dokument med inline CSS/JS; `sw.js` må være egen fil.
- Artskart: «kilde» lagres som datasett/institusjon, ikke observatørnavn.
- Standard budsjett per form (lett/normal/hard): 8/12/16 km og 400/700/1000 høydemeter, justerbart i `config/route.json`.
- Forventet støkk kalibreres slik at arealvektet snitt over jaktfeltet = 8,5 fugl/km², multiplisert med en oppdagelsesandel for støkkjakt uten hund (konfigurerbar).
