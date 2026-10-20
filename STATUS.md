# STATUS

Sist oppdatert: 2026-10-20 (vær, rute, rotasjon og GPX-eksport på Pages; stopp for test)

## Gjort
- Plan, sjekkliste, repo på `kskjevrak/jakt`. GitHub Pages (main, rot) → https://kskjevrak.github.io/jakt/ . Actions aktivert
- Verktøy: `frontend-design` + `emil-design-eng` i `.claude/skills/` (øvrige skills og `.agents/` gitignored), uv + Python 3.12 venv, pinnet `requirements.txt`
- Alle seks datakilder hentet maskinelt (`scripts/download.py`, detaljer i `data/SOURCES.md`)
- Jaktfelt 2139 ha verifisert av Knut. Startpunkter i `config/start.json` verifisert
- `config/habitat.json` v3: lirype 680–900 med mildere topp-/steinurstraff, orrfugl 520–700 + flatt_myrlandskap + helningsstraff, storfugl 300–500 + trehøyde 8/13 + furu vekt 4 (gran 0,3, lauv 0,25) + gammelskog. `kjerner`-regel for lokalkunnskap (bonus på 50 m-celler i nettsiden)
- `config/kjerner.geojson` (tom, fylles fra jaktloggen), `config/steder.json` med Hukebu (589 moh mot DTM, oppgitt ca 585)
- `config/route.json`: budsjetter, gangfart, rotasjon, loggbonus, støkk-kalibrering, værpunkter
- `scripts/build_grid.py` → 10 m rastere i `raw/derived/`, N50-vektorer i `data/`
- `scripts/build_scores.py` → `data/score_<art>.tif/.png/.json`, `data/dominant.tif/.png/.json` (dominerende art der score > 50), `data/grid.geojson` (14 816 celler, 7,4 MB, med `dom`), `data/score_stats.json`, forhåndsvisninger i `raw/preview/`
- `scripts/compare_scores.py`: sammenligner grid mot forrige versjon, viser største endringer med nærmeste N50-stedsnavn og sjekker navngitte kjerneområder
- `kontroll.html` viser score per art, dominerende art og N50-myr som lag
- `DESIGN.md`: tokens for farger (lys/mørk), typografi (Schibsted Grotesk 400/700, selvhostet i `fonts/`), avstand, bevegelse, kartstil og språk
- `index.html` delsteg 2 (vær): MET Locationforecast compact for fjord/Litjønni/Hakefjellet med localStorage-cache etter Expires, fallback `data/forecast.json`; Sunrise 3.0 med `data/sun.json` som fallback; værkort per dag med vindpil + tall, temperatur, nedbør, skydekke, timestripe for Hakefjellet og «unngå snaufjell» over terskel fra `route.json`. `scripts/fetch_forecast.py` + `.github/workflows/forecast.yml` (hver 6. time)
- `index.html` delsteg 3 (rute og rotasjon, v2 etter Knuts tilbakemelding): graf over 50 m-celler innenfor jaktfeltet (vann, bebygd og helning over 35° er sperret), Tobler-lignende gangtid fra `route.json`. Målfelt = sammenhengende celler over 75-persentilen av dagens score innenfor artens høydesone (rotasjonsstraff og 300 m-utelukkelse fra tidligere dager). Ruten går gjennom feltene i rette, parallelle drag på tvers av lengderetningen med 200 m mellomrom; transport med Dijkstra der dagens korridor (150 m / 300 m) koster ×3 / ×1,4, så returen legges en annen vei. Start, slutt og steder er aldri mål. Sløyfe om Hukebu med lunsj (55 % av tiden før). To jegerspor ±30 m, retningspiler, nummererte felt, «sist besøkt»-skravur. Statistikk: km, hm, tid, andel av km i celler over 60, andel drag, overlapp med seg selv (mål under 10 %), terrengandeler, forventet støkk, avstand og gangtid fra bua. GPX per dag/alle dager, PNG av kartet. Diagnoselogg per dag i ruteobjektet. Verifisert i Node på ekte grid (`raw/_tools/rute_test2.js`) og tegnet på topo (`raw/_tools/render_ruter.py`)
- Kart og popup: topo i vanlige farger i begge moduser, score 0,55 dekkevne, én popup om gangen, markørklikk stopper kartklikk, cellepopup i klartekst med avrundede verdier og dagens art i fet, bare dagens start/slutt vises som markører
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
- Knut tester rute v2 på PC: velg dag 1–3, lag ruter, se dem på Pages, eksporter GPX. Siste måling fra Troddebakken (normal form, 7 t): dag 1 rype 10,1 km / 574 hm / 7,0 t / 79 % over 60 / overlapp 11,5 %; dag 2 orrfugl 10,3 km / 534 hm / 6,4 t / 54 % / 12,6 %; dag 3 storfugl 5,3 km / 499 hm / 5,6 t / 54 % / 27,6 % (trang adkomst ned lia)
- Trinn 6 videre: logg (støkk/felt med GPS, GeoJSON-eksport, polygon-eksport til `kjerner.geojson`, loggbonus) → offline (`sw.js`, manifest)
- Mobiltest er utsatt; mobilstrukturen (ark, slicer) er beholdt
- Trinn 7: Actions for værfallback (6 t) og ukentlig matrikkelsjekk
- Trinn 8–9: README med oppdateringsrutine, `/briefing` og `/tune`

## Kjente problemer og valg
- AR5 er ikke detaljkartlagt over skoggrensa; myr = AR5-myr ∪ N50-myr, `arealtype_komb` setter åpen fastmark til myr der N50 har myr
- FKB-AR5 vektor krever Norge digitalt-rolle; WMS-rasterisering brukes. Kantpiksler kan få nabo-klassen
- Blåbærmark finnes ikke som datasett; `blabaermark_proxy` bruker AR5 grunnforhold
- Artskart: bare 4 funn siste 15 år i området
- Overlappmålet under 10 % nås ikke der adkomsten er en trang li (storfugl fra Troddebakken 27,6 %); straff ×3 er valgt fordi ×4 og høyere gir absurde omveier og stenger fjerne felt. Sløyfe om Hukebu for storfugl finner ingen felt innenfor budsjettet
- Ingen nettleser i utviklingsmiljøet: ruter verifiseres i Node og tegnes med Python; ekte skjermbilder krever Playwright (ikke installert)
- Hakefjellets sørvest-side ligger utenfor jaktfeltet; «sørvestli» er tolket som sørvestvendte celler langs sørvestgrensa
- Windows-konsollen trenger `PYTHONIOENCODING=utf-8` for norske tegn i scriptutskrift (compare_scores setter dette selv)
