---
description: Kort kveldsbriefing for en jaktdag basert på værvarsel, habitatscore, kjerneområder og jaktlogg
argument-hint: <dato YYYY-MM-DD>
---

Skriv en kveldsbriefing på norsk bokmål for jaktdagen $ARGUMENTS i jaktfeltet i Bygland (rype, orrfugl, storfugl, støkkjakt uten hund, to jegere).

Gjør dette, i rekkefølge:

1. Kjør `.venv/Scripts/python.exe scripts/briefing_data.py $ARGUMENTS` og les JSON-utskriften. Den inneholder værvarsel per punkt (fjorden, Litjønni, Hakefjellet) for felttimene, soloppgang og solnedgang, de beste cellene per art fra `data/grid.geojson`, kjerneområder fra `config/kjerner.geojson`, eksporterte loggfiler i `logg/*.geojson`, steder og standard start/slutt per art fra `config/route.json`.
2. Les `config/route.json` for terskler (vind over `vaer.vind_unngaa_snaufjell_ms` på Hakefjellet betyr «unngå snaufjell» de timene) og `config/habitat.json` for høydesoner per art.
3. Skriv briefingen, maks 200 ord, som en erfaren jaktkamerat ville sagt det ved kjøkkenbordet kvelden før:
   - Første setning: anbefalt art og område for dagen, og hvorfor (vær, høydesone, hvor det er ferskt terreng).
   - Vær: vind på fjellet med retning og styrke om morgenen og midt på dagen, temperatur, nedbør, og eventuelle timer med «unngå snaufjell». Sol opp og ned.
   - Start og slutt: artens standard fra `standard_per_art`, snudd hvis morgenvinden ved fjorden kommer fra sør, og hvor bilen må stå ved gjennomgang.
   - Hva loggen og kjerneområdene sier, hvis det finnes noe. Hvis loggen er tom, si det i én setning.
   - Én konkret ting å passe på (bratt li, vind i ryggen, kort dag).
4. Ikke finn på tall. Alle tall skal komme fra utskriften eller config-filene. Hvis varselet mangler for datoen, si det og bruk det som finnes.
5. Lagre briefingen som `logg/briefing-$ARGUMENTS.md` og vis den i chatten.
