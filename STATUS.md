# STATUS

Sist oppdatert: 2026-10-21 (alle trinn på Pages; venter på Knuts test av logg, offline og dag 3)

## Gjort
- Plan, sjekkliste, repo på `kskjevrak/jakt`. GitHub Pages (main, rot) → https://kskjevrak.github.io/jakt/ . Actions aktivert og i drift
- Verktøy: `frontend-design` + `emil-design-eng` i `.claude/skills/`, uv + Python 3.12 venv, pinnet `requirements.txt` (inkl. Playwright 1.55 med Chromium)
- Alle seks datakilder hentet maskinelt (`scripts/download.py`, detaljer i `data/SOURCES.md`). Jaktfelt 2139 ha verifisert
- `config/habitat.json` v3b, `config/route.json` (rute v2, standard start/slutt per art, loggbonus), `config/start.json`, `config/steder.json` (Hukebu 589 moh), `config/kjerner.geojson` (tom, fylles fra felt)
- `scripts/build_grid.py` (10 m rastere, N50-vektorer, alle veglenker som transport) og `scripts/build_scores.py` (score, PNG, COG, dominerende art, `grid.geojson` 14 816 celler). `scripts/compare_scores.py` for før/etter
- `index.html`, ett dokument:
  - kart: Kartverket topo i vanlige farger i begge moduser, jaktfelt 3 px mørk oransje med hvit kant, grå stiplede teiger, rød skravur på naboteiger, N50-lag, WMS-sannhetslag, score 0,55 dekkevne (50 m-celler + 10 m PNG + dominerende art)
  - oppsett per dag: art, start, slutt, sløyfe; «Standard for arten» følger `standard_per_art` (storfugl gjennomgang Mele → Troddebakken, snudd ved sørlig morgenvind ved fjorden). Panelet sier hvor bilen må stå. Lagres i localStorage og URL-hash
  - vær: MET live for fjord/Litjønni/Hakefjellet, Sunrise, vindpil + tall, «unngå snaufjell», fallback `data/forecast.json`
  - rute v2: felt = sammenhengende kjerner over 75-persentilen innenfor artens høydesone, rette parallelle drag 200 m, transport med samme-dag-straff ×3/×1,4 så returen går en annen vei, start/slutt/steder aldri mål, automatisk alternativ når opplegget ikke gir rute, rotasjon mellom dager, loggbonus. Statistikk med overlapp og andel km over 60. GPX og PNG
  - logg: Støkk/Felt med GPS eller kartklikk, GeoJSON-eksport/-import, egne punkter i kartet, bonus i neste dags planlegging. «Tegn kjerneområde» → `kjerner.geojson`-eksport
  - offline: `sw.js` (cache først for app og data, nett først for MET, flis-cache med tak), `manifest.webmanifest`, ikoner, statusmerke
  - popup: én om gangen, klartekst, markørklikk stopper kartklikk
- Actions: `forecast.yml` (hver 6. time, i drift) og `matrikkel.yml` (ukentlig, commiter bare ved geometriendring)
- `scripts/screenshot.py`: ekte skjermbilde av Pages i Chromium med oppsett i URL-hash → `raw/preview/`. `scripts/briefing_data.py` og `scripts/tune_data.py` for `/briefing` og `/tune` i `.claude/commands/`
- `README.md` med oppdateringsrutine for data, habitatregler, Actions og verktøy

## Siste rutekjøring (standardoppsett, 22. oktober, normal form, 7 t)
| Dag | Art | Opplegg | km | hm | t | andel km over 60 | overlapp |
|---|---|---|---|---|---|---|---|
| 1 | Rype | Troddebakken rundtur | 10,1 | 581 | 6,7 | 74 % | 13,2 % |
| 2 | Orrfugl | Troddebakken rundtur | 10,7 | 525 | 6,6 | 51 % | 18,6 % |
| 3 | Storfugl | Gjennomgang Mele → Troddebakken | 5,5 | 594 | 6,0 | 81 % | 66,7 % |

Dag 3 er fortsatt svak: Mele og Troddebakken ligger 1,1 km fra hverandre, lia er bratt, og dag 2 har allerede brukt deler av storfuglbeltet. Troddebakken → Mele gir 6,4 km / 467 hm / 32 % overlapp, Mele → Enden av vegen 8,4 km / 788 hm / 24 %.

## Gjenstår / åpne spørsmål
- Knut tester logg (GPS på mobil), offline (slå av nett etter første besøk), kjerneområde-tegning og dag 3-opplegget
- Dag 3: vurder annen rekkefølge (storfugl først), annet sluttpunkt (Enden av vegen) eller lettere budsjett
- Mobiltest er utsatt; strukturen er beholdt

## Kjente problemer og valg
- AR5 er ikke detaljkartlagt over skoggrensa; myr = AR5-myr ∪ N50-myr. FKB-AR5 vektor krever Norge digitalt-rolle; WMS-rasterisering brukes
- Blåbærmark finnes ikke som datasett; `blabaermark_proxy` bruker AR5 grunnforhold. Artskart har bare 4 funn siste 15 år i området
- Overlappmålet under 10 % nås ikke der adkomsten er en trang li; straff ×3 valgt fordi høyere gir absurde omveier
- Gangtiden (Tobler, 3 km/t flatt, terrengfaktorer) gjør at 7 timer binder før 12 km. Justeres i `route.json` under `gange`
- Eksporterte logger i `logg/` er gitignored fordi repoet er offentlig
