# STATUS

Sist oppdatert: 2026-10-20 (vær, rute, rotasjon og GPX-eksport på Pages; stopp for test)

## Gjort
- Plan, sjekkliste, repo på `kskjevrak/jakt`. GitHub Pages (main, rot) → https://kskjevrak.github.io/jakt/ . Actions aktivert
- Verktøy: `frontend-design` + `emil-design-eng` i `.claude/skills/` (øvrige skills og `.agents/` gitignored), uv + Python 3.12 venv, pinnet `requirements.txt`
- Alle seks datakilder hentet maskinelt (`scripts/download.py`, detaljer i `data/SOURCES.md`)
- Jaktfelt 2139 ha verifisert av Knut. Startpunkter i `config/start.json` verifisert
- `config/habitat.json` v3: lirype 680–900 med mildere topp-/steinurstraff, orrfugl 520–700 + flatt_myrlandskap + helningsstraff, storfugl 300–500 + trehøyde 12/17 + furu vekt 4 + gammelskog. `kjerner`-regel for lokalkunnskap (bonus på 50 m-celler i nettsiden)
- `config/kjerner.geojson` (tom, fylles fra jaktloggen), `config/steder.json` med Hukebu (589 moh mot DTM, oppgitt ca 585)
- `config/route.json`: budsjetter, gangfart, rotasjon, loggbonus, støkk-kalibrering, værpunkter
- `scripts/build_grid.py` → 10 m rastere i `raw/derived/`, N50-vektorer i `data/`
- `scripts/build_scores.py` → `data/score_<art>.tif/.png/.json`, `data/dominant.tif/.png/.json` (dominerende art der score > 50), `data/grid.geojson` (14 816 celler, 7,4 MB, med `dom`), `data/score_stats.json`, forhåndsvisninger i `raw/preview/`
- `scripts/compare_scores.py`: sammenligner grid mot forrige versjon, viser største endringer med nærmeste N50-stedsnavn og sjekker navngitte kjerneområder
- `kontroll.html` viser score per art, dominerende art og N50-myr som lag
- `DESIGN.md`: tokens for farger (lys/mørk), typografi (Schibsted Grotesk 400/700, selvhostet i `fonts/`), avstand, bevegelse, kartstil og språk
- `index.html` delsteg 2 (vær): MET Locationforecast compact for fjord/Litjønni/Hakefjellet med localStorage-cache etter Expires, fallback `data/forecast.json`; Sunrise 3.0 med `data/sun.json` som fallback; værkort per dag med vindpil + tall, temperatur, nedbør, skydekke, timestripe for Hakefjellet og «unngå snaufjell» over terskel fra `route.json`. `scripts/fetch_forecast.py` + `.github/workflows/forecast.yml` (hver 6. time)
- `index.html` delsteg 3 (rute og rotasjon): graf over 50 m-celler innenfor jaktfeltet (vann, bebygd og helning over 35° er sperret), Tobler-lignende gangtid fra `route.json`, Dijkstra, målpartier fra score (min 55, inntil 8, rotasjonsstraff fra tidligere dager og 300 m-utelukkelse), innsettings-heuristikk med 2-opt innenfor km/høydemeter/timer, sløyfe om Hukebu med lunsj, gangretning valgt mot morgenvinden ved Litjønni. To jegerspor ±30 m, korridor, retningspiler, nummererte partier, «sist besøkt»-skravur med alder. Rutestatistikk med km, hm, tid, terrengandeler, forventet støkk (8,5 fugl/km² × score/middel × 35 %), avstand og gangtid fra bua. GPX per dag og alle dager (rute, to spor, veipunkter), PNG av kartet. Ruter lagres i localStorage med signatur av oppsettet
- `index.html` delsteg 1: MapLibre 5.6.0 med Kartverket topo/gråtone, score fra `grid.geojson` (farger og terskler fra `habitat.json`, filtrerbar på høydesone), 10 m-PNG og dominerende art som valgfrie lag, kjerner, Artskart, jaktfelt, naboteiger (skravur), N50 vann/bekker/stier/myr, WMS-sannhetslag (AR5, SR16 treslag/bonitet, matrikkelkart), Hukebu-markør med popup og handlinger, startpunkter, slicer (dag/art/høydesone), oppsettpanel (localStorage + URL-hash), mobilark, lys/mørk modus, cellepopup. Kjerner-bonus regnes i nettleseren på 50 m-celler

## Score v3b innenfor jaktfeltet (raster 10 m)
| Art | ha ≥ 60 | mål | middel | dominerende art (score > 50) |
|---|---|---|---|---|
| Lirype | 856 | 650–850 | 54 | 808 ha |
| Orrfugl | 463 | 200–350 | 35 | 313 ha |
| Storfugl | 594 | 350–500 | 34 | 552 ha |

Ingen art over 50 på 518 ha. Storfugl v3b: høyde 300–500, furu vekt 4 (gran 0,3, lauv 0,25), trehøyde 8/13 etter Knuts valg. Orrfugl og lirype som v2.

Flyet og Litjønni er ikke orrfugl-kjerner i dataene (1–2 % myr, ingen myr over 1 ha med skog på to sider). Gytjønn og myrene øst for Bergebekken er det. Se forslag i chat / neste justering.

## Gjenstår
- Knut tester på PC: velg dag 1–3, lag ruter, se dem på Pages, eksporter GPX
- Trinn 6 videre: logg (støkk/felt med GPS, GeoJSON-eksport, polygon-eksport til `kjerner.geojson`, loggbonus) → offline (`sw.js`, manifest)
- Mobiltest er utsatt; mobilstrukturen (ark, slicer) er beholdt
- Trinn 7: Actions for værfallback (6 t) og ukentlig matrikkelsjekk
- Trinn 8–9: README med oppdateringsrutine, `/briefing` og `/tune`

## Kjente problemer og valg
- AR5 er ikke detaljkartlagt over skoggrensa; myr = AR5-myr ∪ N50-myr, `arealtype_komb` setter åpen fastmark til myr der N50 har myr
- FKB-AR5 vektor krever Norge digitalt-rolle; WMS-rasterisering brukes. Kantpiksler kan få nabo-klassen
- Blåbærmark finnes ikke som datasett; `blabaermark_proxy` bruker AR5 grunnforhold
- Artskart: bare 4 funn siste 15 år i området
- Hakefjellets sørvest-side ligger utenfor jaktfeltet; «sørvestli» er tolket som sørvestvendte celler langs sørvestgrensa
- Windows-konsollen trenger `PYTHONIOENCODING=utf-8` for norske tegn i scriptutskrift (compare_scores setter dette selv)
