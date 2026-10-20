# STATUS

Sist oppdatert: 2026-10-20 (habitatregler v2 kjørt, DESIGN.md skrevet, klar for index.html)

## Gjort
- Plan, sjekkliste, repo på `kskjevrak/jakt`. GitHub Pages (main, rot) → https://kskjevrak.github.io/jakt/ . Actions aktivert
- Verktøy: `frontend-design` + `emil-design-eng` i `.claude/skills/` (øvrige skills og `.agents/` gitignored), uv + Python 3.12 venv, pinnet `requirements.txt`
- Alle seks datakilder hentet maskinelt (`scripts/download.py`, detaljer i `data/SOURCES.md`)
- Jaktfelt 2139 ha verifisert av Knut. Startpunkter i `config/start.json` verifisert
- `config/habitat.json` v2 med Knuts justeringer (lirype 680–900, storfugl 300–560 + gammelskog, orrfugl 520–700 + flatt_myrlandskap + helningsstraff)
- `config/route.json`: budsjetter, gangfart, rotasjon, loggbonus, støkk-kalibrering, værpunkter
- `scripts/build_grid.py` → 10 m rastere i `raw/derived/`, N50-vektorer i `data/`
- `scripts/build_scores.py` → `data/score_<art>.tif/.png/.json`, `data/dominant.tif/.png/.json` (dominerende art der score > 50), `data/grid.geojson` (14 816 celler, 7,4 MB, med `dom`), `data/score_stats.json`, forhåndsvisninger i `raw/preview/`
- `scripts/compare_scores.py`: sammenligner grid mot forrige versjon, viser største endringer med nærmeste N50-stedsnavn og sjekker navngitte kjerneområder
- `kontroll.html` viser score per art, dominerende art og N50-myr som lag
- `DESIGN.md`: tokens for farger (lys/mørk), typografi (Schibsted Grotesk 400/700), avstand, bevegelse, kartstil og språk

## Score v2 innenfor jaktfeltet
| Art | ha ≥ 60 | mål | middel |
|---|---|---|---|
| Lirype | 856 | 650–850 | 54 |
| Orrfugl | 463 | 200–350 | 35 |
| Storfugl | 667 | 350–500 | 36 |

Flyet og Litjønni er ikke orrfugl-kjerner i dataene (1–2 % myr, ingen myr over 1 ha med skog på to sider). Gytjønn og myrene øst for Bergebekken er det. Se forslag i chat / neste justering.

## Gjenstår
- Knut avgjør neste regeljustering (forslag med simulerte utfall er gitt)
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
