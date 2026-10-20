# STATUS

Sist oppdatert: 2026-10-20 (trinn 5 ferdig, venter på sjekk av habitat.json og score-PNG før nettsiden)

## Gjort
- Plan, sjekkliste, repo pushet til `kskjevrak/jakt`. GitHub Pages slått på (main, rot) → https://kskjevrak.github.io/jakt/ . Actions er aktivert
- Verktøy: `frontend-design` + `emil-design-eng` i `.claude/skills/` (øvrige skills og `.agents/` er gitignored), uv + Python 3.12 venv, pinnet `requirements.txt`
- `scripts/download.py` + ett hentescript per kilde, alle seks hentet maskinelt (se `data/SOURCES.md`):
  Teig (WFS + REST), N50 (Atom), DTM (NHM WCS 1.0.0, 2 m → 10 m), AR5 (WMS rasterisert 5 m, verifisert med GetFeatureInfo), SR16 (NIBIO API, 10 bånd klippet), Artskart (REST)
- `scripts/build_jaktfelt.py`: jaktfelt 2139 ha, 33 teiger + 1 punktfeste, 37 naboteiger. Grensene verifisert av Knut mot matrikkelkartet. Teigen 49/3,5 behandles som ordinært jaktfelt
- `config/start.json`: Mele, Garteskar, Troddebakken, Enden av vegen (alle verifisert)
- `config/habitat.json`: regler, terskler og vekter per art (trapes/klasser/flagg + multiplikative straffer), fargeskala for PNG
- `config/route.json`: form-budsjetter, gangfart, rotasjon, loggbonus, støkk-kalibrering (8,5 fugl/km²), værpunkter og vindterskel
- `scripts/build_grid.py`: 10 m rastere i `raw/derived/` (høyde, helning, eksposisjon, TPI 150/500, AR5-klasser, SR16, avstander til myr/stor myr/bekk/vann/skoggrense/lauv, flagg). N50 → `data/vann.geojson`, `bekker.geojson`, `stier.geojson`, `myr_n50.geojson`
- `scripts/build_scores.py`: `data/score_<art>.tif` (COG), `data/score_<art>.png` + `.json` (Web Mercator-overlegg, 0,9–1,1 MB), `raw/preview/score_<art>.png` (topo + score + jaktfelt), `data/grid.geojson` (14 816 celler à 50 m, 7,3 MB), `data/score_stats.json`
- `scripts/build.py` kjører jaktfelt → grid → score
- Score innenfor jaktfeltet: lirype middel 50 (40 % ≥ 60, 857 ha), orrfugl 44 (29 %, 615 ha), storfugl 38 (33 %, 697 ha)

## Gjenstår
- **Knut sjekker** `config/habitat.json` og forhåndsvisningene (`raw/preview/score_*.png` via lokal server)
- Trinn 6: `DESIGN.md` → `index.html` (kart/lag, oppsett, vær, rute, rotasjon, logg, eksport, offline) + `sw.js`
- Trinn 7: Actions for værfallback (6 t) og ukentlig matrikkelsjekk
- Trinn 8–9: README med oppdateringsrutine, `/briefing` og `/tune`

## Kjente problemer og valg
- AR5 er ikke detaljkartlagt over skoggrensa: myr på platået mangler i AR5 (82 ha) men finnes i N50 (218 ha). Myrmasken er unionen; `arealtype_komb` setter åpen fastmark til myr der N50 har myr
- FKB-AR5 vektor krever Norge digitalt-rolle; vi bruker WMS-rasterisering. Kantpiksler kan få nabo-klassen
- Blåbærmark finnes ikke som datasett; storfugl-faktoren `blabaermark_proxy` bruker AR5 grunnforhold og er merket proxy
- Artskart har bare 4 funn siste 15 år i området (3 orrfugl, 1 storfugl), så Artskart-laget blir tynt
- Artskart-API: dato filtreres lokalt (server-filter gir 504); Kartverket NHM WCS fungerer bare i versjon 1.0.0
- SR16-fylkesfilen (1,85 GB) ligger i `raw/` og er gitignored
