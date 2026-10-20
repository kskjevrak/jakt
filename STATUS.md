# STATUS

Sist oppdatert: 2026-10-20 (habitatregler v3, steder og kjerner lagt inn, index.html under arbeid)

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
- `DESIGN.md`: tokens for farger (lys/mørk), typografi (Schibsted Grotesk 400/700), avstand, bevegelse, kartstil og språk

## Score v3 innenfor jaktfeltet (raster 10 m)
| Art | ha ≥ 60 | mål | middel | dominerende art (score > 50) |
|---|---|---|---|---|
| Lirype | 856 | 650–850 | 54 | 808 ha |
| Orrfugl | 463 | 200–350 | 35 | 313 ha |
| Storfugl | 524 | 350–500 | 32 | 482 ha |

Ingen art over 50 på 537 ha. Orrfugl og lirype beholdes som v2 etter Knuts beslutning.

Flyet og Litjønni er ikke orrfugl-kjerner i dataene (1–2 % myr, ingen myr over 1 ha med skog på to sider). Gytjønn og myrene øst for Bergebekken er det. Se forslag i chat / neste justering.

## Gjenstår
- Trinn 6: `index.html` + `sw.js` etter `DESIGN.md` (kart/lag → oppsett → vær → rute → rotasjon → logg → eksport → offline)
- Trinn 7: Actions for værfallback (6 t) og ukentlig matrikkelsjekk
- Trinn 8–9: README med oppdateringsrutine, `/briefing` og `/tune`

## Kjente problemer og valg
- AR5 er ikke detaljkartlagt over skoggrensa; myr = AR5-myr ∪ N50-myr, `arealtype_komb` setter åpen fastmark til myr der N50 har myr
- FKB-AR5 vektor krever Norge digitalt-rolle; WMS-rasterisering brukes. Kantpiksler kan få nabo-klassen
- Blåbærmark finnes ikke som datasett; `blabaermark_proxy` bruker AR5 grunnforhold
- Artskart: bare 4 funn siste 15 år i området
- Hakefjellets sørvest-side ligger utenfor jaktfeltet; «sørvestli» er tolket som sørvestvendte celler langs sørvestgrensa
- Windows-konsollen trenger `PYTHONIOENCODING=utf-8` for norske tegn i scriptutskrift (compare_scores setter dette selv)
