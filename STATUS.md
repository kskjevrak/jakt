# STATUS

Sist oppdatert: 2026-10-20 (trinn 2–4 ferdig, venter på verifisering av jaktfeltgrensene)

## Gjort
- Plan (`PLAN.md`), sjekkliste bekreftet, repo pushet til `kskjevrak/jakt` (main)
- Verktøy: `frontend-design`-skill installert i `.claude/skills/`, `emil-design-eng` bekreftet, uv + Python 3.12 venv i `.venv/`
  med geopandas 1.2, rasterio 1.5.2 (GDAL 3.12), shapely 2.2, pyproj 3.8, numpy 2.5, scipy 1.18 – pinnet i `requirements.txt`
- `gh` CLI 2.102 installert via winget (ikke innlogget ennå)
- `scripts/common.py`: felles HTTP-session med User-Agent, cache (ETag/Last-Modified/alder) i `raw/_cache.json`, gjenopptakbar nedlasting, rapportgenerator
- `scripts/download.py` + ett hentescript per kilde. Alle seks kilder hentet maskinelt, se `data/SOURCES.md`:
  - Teig: Kartverket WFS 2.0.0 + REST-validering av alle gnr/bnr (Atom-fallback implementert)
  - N50: Atom feed, kommunefil 4220 GML 25833
  - DTM: Kartverket NHM WCS 1.0.0, 35 fliser à 2 km i 2 m (toppene Hakefjellet/Skjevraknuten/Hukebuvatnet verifisert mot høyde-API)
  - AR5: vektor er Norge digitalt-begrenset. Rasterisert i 5 m fra NIBIO AR5 WMS, dekodet via SLD, 12/12 stikkprøver verifisert med GetFeatureInfo. AR50 vektor lastet som referanse
  - SR16: NIBIO nedlastings-API, Agder-fil 1,85 GB, 10 bånd klippet til AOI (16 m)
  - Artskart: REST, polygon i WGS84; kun 4 funn siste 15 år i området
- `scripts/build_jaktfelt.py`: `data/jaktfelt.geojson` (2139 ha, 33 teiger + 1 punktfeste), `data/teiger.geojson`, `data/naboteiger.geojson` (37 innen 500 m), `data/aoi.geojson`
- `config/start.json` med Mele og Gateskar (geokodet), Troddebakken og Enden av vegen tomme
- `kontroll.html`: minimalt verifiseringskart (Kartverket WMTS + jaktfelt + naboteiger + matrikkel-WMS som sannhetslag + klikk for koordinater)

## Gjenstår
- **Knut verifiserer** jaktfeltgrensene i `kontroll.html`, avklarer teigen «49/3,5» (541 ha, delt mellom 49/3 og 49/5) og Gateskar-koordinaten
- `gh auth login` (Knut), slå på GitHub Pages (main, rot), sjekke at Actions er aktivert
- Trinn 5: `build_grid.py` (50 m grid), `build_scores.py` (score-rastere + PNG < 2 MB), `config/habitat.json`, `config/route.json`
- Trinn 6: `DESIGN.md` → `index.html` (kart/lag, oppsett, vær, rute, rotasjon, logg, eksport, offline)
- Trinn 7: Actions for værfallback (6 t) og ukentlig matrikkelsjekk
- Trinn 8–9: README med oppdateringsrutine, `/briefing` og `/tune`

## Kjente problemer
- FKB-AR5 vektor krever Norge digitalt-rolle; vi bruker WMS-rasterisering (5 m). Kantpiksler mellom klasser kan få nærmeste legendefarge
- Artskart-API: `filter.fromDate` gir 504, dato filtreres lokalt. Polygon må være i lon/lat
- Kartverket NHM WCS: bare versjon 1.0.0 fungerer for GeoTIFF; 1.1.2 og 2.0.1 feiler
- SR16-fylkesfilen er 1,85 GB i `raw/` (gitignored); kun AOI-klipp brukes videre
- `sources.json`/`SOURCES.md` regenereres ved hver kjøring; parallelle kjøringer flettes ved slutt
