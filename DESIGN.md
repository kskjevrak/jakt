# DESIGN – fugledashboard Bygland

Designsystemet for `index.html`. Alt UI bruker tokens herfra, ingen løse verdier i koden.
Retning fra oppdraget: rolig, kartdominert, nordisk friluftsfølelse. Kartet eier skjermen, panelene
ligger oppå med lett transparens og blur. Tall skal leses med hansker i sol.

## Hvem og hvor

To jegere i Setesdalsheiene i oktober. Telefonen leses i motlys, med kalde fingre, mellom to drag over en
myr. Kvelden før leses den samme siden på en laptop ved kjøkkenbordet for å legge morgendagens rute.
Siden har én jobb: svare på «hvor går vi i morgen, og hva kan vi vente oss». Alt som ikke hjelper det
svaret, bort.

## Prinsipper

1. **Kartet eier skjermen.** Paneler dekker aldri mer enn en tredjedel av bredden på skrivebord og
   ligger som et nedre ark på mobil. Ingenting har bakgrunn som ikke trenger det.
2. **Ett tall per beslutning.** Hvert kort leder med det ene tallet som avgjør noe (vind på fjellet,
   kilometer, forventede støkk). Tall settes stort, enheten liten etter.
3. **Oransje er handling.** Jaktoransje brukes til én ting: det som skjer nå. Primærknappen, dagens
   rute, aktiv dag i sliceren. Alt annet er dempet gneis-grått, slik at oransje alltid betyr «her».
4. **Bevegelse forklarer.** Animasjon finnes bare der tilstand endres: dag skifter, rute tegnes,
   værkort oppdateres, ark åpnes. Ingen pynt, ingen innganger på hvert element.
5. **Sannhet før modell.** Egne beregnede lag vises alltid litt gjennomskinnelige over topokartet,
   og kildelagene fra NIBIO og Kartverket kan slås på for å sjekke oss.

## Farger

Paletten er hentet fra fjellet i oktober: rim på berget, lav på gneis, bjørk som har gulnet, myrvann.
Ingen lilla, ingen gradienter.

| Token | Lys | Mørk | Bruk |
|---|---|---|---|
| `--bg` | `#EEF0EC` | `#15181A` | Sidebakgrunn bak kartet mens fliser laster |
| `--panel` | `rgba(246, 247, 244, 0.82)` | `rgba(24, 27, 30, 0.80)` | Panelflater, med `backdrop-filter: blur(14px)` |
| `--panel-solid` | `#F6F7F4` | `#181B1E` | Samme panel uten blur (reduced transparency, utskrift) |
| `--line` | `rgba(28, 33, 36, 0.14)` | `rgba(240, 242, 238, 0.14)` | Hårstrek mellom felt, panelkant |
| `--ink` | `#1C2124` | `#F0F2EE` | Primærtekst og store tall |
| `--ink-2` | `#5B6368` | `#A7AFB3` | Sekundærtekst, enheter, forklaringer |
| `--ink-3` | `#8A9196` | `#737B80` | Deaktivert, plassholder |
| `--accent` | `#E85D04` | `#FF7A1A` | Jaktoransje: primærknapp, dagens rute, aktiv dag |
| `--accent-ink` | `#FFFFFF` | `#1A1200` | Tekst på oransje |
| `--accent-soft` | `rgba(232, 93, 4, 0.14)` | `rgba(255, 122, 26, 0.20)` | Bakgrunn bak aktivt valg |
| `--warn` | `#B42318` | `#FF6B5E` | «Unngå snaufjell», vind over terskel, naboteig |
| `--ok` | `#2F6B3A` | `#7FC48A` | Innenfor budsjett, GPS ok |
| `--water` | `#5C9BC2` | `#6FA8CC` | Vann og bekker i egne lag |
| `--mire` | `#8A7A4E` | `#A8976A` | Myr i egne lag |
| `--lirype` | `#B5651D` | `#D98A4A` | Artsfarge, lik `farge` i `config/habitat.json` |
| `--orrfugl` | `#4B3F72` | `#8E82BF` | Artsfarge |
| `--storfugl` | `#1F5E3B` | `#5FA37E` | Artsfarge |
| `--nabo` | `rgba(180, 35, 24, 0.55)` | `rgba(255, 107, 94, 0.55)` | Rødskravur naboteiger |
| `--visited` | `rgba(28, 33, 36, 0.35)` | `rgba(240, 242, 238, 0.35)` | «Sist besøkt»-skravur |
| `--focus` | `#1D6FA5` | `#7CC0F0` | Tastaturfokus, 2 px utenfor elementet |

Scorefargene på kartet kommer fra `visning.stopp` i `config/habitat.json` (gul → mørk rød) og gjentas
i legenden, de defineres ikke her.

Kontrast: `--ink` på `--panel-solid` er 14:1 i lys og 15:1 i mørk modus. `--accent-ink` på
`--accent` er 4,6:1 i lys (hvit på oransje) og 9:1 i mørk. Store tall settes alltid i `--ink`, aldri
i aksentfarge, slik at de leses i sol.

Mørk modus bytter også bakgrunnskartet til Kartverkets gråtonetopo (`topograatone`) dempet med
`raster-brightness-max: 0.62`, slik at panelene og rutelinjen bærer fargen om kvelden.

## Typografi

Én familie, to vekter. **Schibsted Grotesk** (Google Fonts, norsk opphav, åpen lisens) i 400 og 700,
med `font-feature-settings: "tnum"` på alle tall. Fallback `system-ui, -apple-system, "Segoe UI",
sans-serif`. Fontfilene caches av service workeren etter første besøk.

Skala med forhold 1,25 fra 16 px:

| Token | Størrelse / linje | Vekt | Bruk |
|---|---|---|---|
| `--t-num-xl` | 39 / 40 px | 700 | Det ene tallet per kort (vind, km, støkk) |
| `--t-num-l` | 31 / 34 px | 700 | Tall i rutestatistikk |
| `--t-title` | 25 / 30 px | 700 | Dagsoverskrift («Torsdag 22. oktober, dag 2») |
| `--t-lead` | 20 / 26 px | 400 | Briefing-setning, panelintro |
| `--t-body` | 16 / 24 px | 400 | Brødtekst, knapper, slicer |
| `--t-small` | 13 / 18 px | 400 | Enheter, kilder, tidsstempler |

Regler: setningsbokstaver overalt, aldri versaler som etikett. Enheten står etter tallet i
`--t-small` og `--ink-2` («12,4 km», «9 m/s»). Ingen enkeltord i annen farge i overskrifter.
Linjelengde under 70 tegn. Tall i tabeller høyrejusteres, tekst venstrejusteres.

## Avstand, form og lag

| Token | Verdi | Bruk |
|---|---|---|
| `--s-1` … `--s-6` | 4, 8, 12, 16, 24, 32 px | Hele skalaen; 48 px bare som panelmarg på skrivebord |
| `--r-control` | 8 px | Knapper, inputs, slicer-segmenter |
| `--r-panel` | 14 px | Paneler og ark; større radius markerer høyere nivå |
| `--r-pill` | 999 px | Bare på statusmerker (GPS, offline) |
| `--panel-w` | 360 px | Panelbredde på skrivebord, maks 33 vw |
| `--sheet-peek` | 112 px | Synlig del av mobilarket i lukket tilstand |
| `--hit` | 44 px | Minste trykkflate, også med hansker |
| `--z-map / --z-panel / --z-sheet / --z-toast` | 0 / 10 / 20 / 30 | Lagrekkefølge |

Ingen bokskygger. Paneler skilles fra kartet med blur, `--panel` og en 1 px `--line`. Når
`prefers-reduced-transparency: reduce` er satt, eller nettleseren mangler `backdrop-filter`, brukes
`--panel-solid`.

## Layout

Skrivebord (≥ 900 px):

```
┌──────────────────────────────────────────────────────────────────┐
│ ●Dag 1 ○Dag 2 ○Dag 3   ○Lirype ●Orrfugl ○Storfugl   <500 500–700 >700 │  slicer, 48 px, venstrejustert
├────────────┬─────────────────────────────────────────────────────┤
│ Torsdag 22.│                                                     │
│ 9 m/s      │                 K A R T                             │  panel 360 px, blur
│ Hakefjellet│         rute i oransje, spor i to tynne linjer      │
│ ────────   │                                   ┌──────────┐      │
│ 12,4 km    │                                   │ Lag      │      │  lagvelger, kollapset
│ 640 hm     │                                   │ ○ Score  │      │
│ ────────   │                                   │ ○ Myr    │      │
│ [Nytt opp- │                                   └──────────┘      │
│  sett]     │                                       ⊕ ○ GPS       │
└────────────┴─────────────────────────────────────────────────────┘
```

Mobil (< 900 px): sliceren ligger øverst som én rad som kan rulles sideveis. Panelet blir et nedre
ark med `--sheet-peek` synlig (dagens ene tall og km), som dras opp til halv og full høyde. Knappene
«Støkk» og «Felt» ligger alltid synlige i arkets topp slik at de kan trykkes uten å åpne noe.

Alt innhold er venstrejustert. Tall i kolonner høyrejusteres. Ingen sentrering unntatt tomtilstander.

## Bevegelse

Kurver og tider som tokens; bare `transform`, `opacity`, `clip-path` og `filter` animeres.

| Token | Verdi | Bruk |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.23, 1, 0.32, 1)` | Alt som kommer inn eller svarer på trykk |
| `--ease-in-out` | `cubic-bezier(0.77, 0, 0.175, 1)` | Ting som flytter seg på skjermen |
| `--ease-sheet` | `cubic-bezier(0.32, 0.72, 0, 1)` | Mobilarket |
| `--d-press` | 120 ms | `:active` på knapper, `scale(0.97)` |
| `--d-control` | 160 ms | Slicer-segment, brytere, tooltips |
| `--d-panel` | 220 ms | Paneler, popovers (origin ved trigger) |
| `--d-sheet` | 320 ms | Mobilarket opp og ned |
| `--d-swap` | 180 ms | Kryssfading av innhold når dag eller art skifter, med `filter: blur(2px)` midtveis |
| `--d-route` | 600 ms | Rute tegnes inn med `line-gradient`-progresjon; eneste bevisst lange bevegelse |

Regler fra designskillen som gjelder her:

- Ingenting animeres fra `scale(0)`; innganger starter på `scale(0.96)` og `opacity: 0`.
- Ut går raskere enn inn: ark lukker på 220 ms, åpner på 320 ms.
- Tastaturvalg i sliceren animeres ikke.
- Hover-effekter bare under `@media (hover: hover) and (pointer: fine)`.
- `prefers-reduced-motion: reduce`: all `transform`-bevegelse fjernes, kryssfading og rutetegning
  beholdes som ren opasitet på 120 ms.
- Stagger brukes kun når værkortene for flere dager lastes første gang: 40 ms mellom kort.

## Kartet

- Bakgrunn: Kartverket `topo` (lys) / `topograatone` (mørk), WMTS webmercator.
- Jaktfelt: linje 2,5 px `--ink`, ingen fyll. Naboteiger: skravur 45° i `--nabo`, 1 px linje.
- Score: PNG-overlegg med `raster-opacity 0.85`, kan dempes med glidebryter i lagvelgeren.
- Rute: 4 px `--accent`, hvit kant 1 px for lesbarhet på topo. To jegerspor: 1,5 px `--ink`, stiplet.
  Gangretning: pilsymbol langs linjen hver 400 m. Korridor (polygonkjeden): `--accent-soft`.
- Startpunkt: ring 10 px med 2 px kant. Artskart-funn: punkt 6 px i artsfarge. Egne loggpunkter:
  firkant 8 px i artsfarge med `--ink`-kant.
- «Sist besøkt»: skravur i `--visited`, tetthet avtar med alder (styrt av `rotasjon` i `config/route.json`).

## Språk i grensesnittet

Norsk bokmål, setningsbokstaver, aktive verb. Knappen sier hva som skjer: «Lag rute for dag 2»,
«Lagre støkk», «Last ned GPX». Feil forklarer og peker videre: «Fikk ikke vær fra MET. Viser varsel
fra kl. 06 (lagret).» Tom tilstand inviterer: «Velg startpunkt og art, så tegner vi dagens rute.»
Alle terskler i tekst («vind over 10 m/s») leses fra config og skrives aldri fast i HTML.

## Avgrensninger

- Ingen ikonbibliotek. Eneste glyfer er vindpil (rotert etter retning), sol opp og ned, og
  GPS-prikk, tegnet som inline SVG med `currentColor`.
- Ingen kortrutenett. Innhold i panelet står som liste med hårstrek mellom, ikke som bokser.
- Ingen gradienter unntatt rutetegningen (`line-gradient` er progresjon, ikke pynt) og scorelaget.
- Én aksentfarge. Hvis noe «må» ha farge og ikke er handling eller art, er det `--ink-2`.
