---
description: Kveldsbriefing for jaktdagene fra en gitt dato, tre avsnitt per dag, basert på planlagte ruter, vær og observasjoner
argument-hint: <dato YYYY-MM-DD for første jaktdag>
---

Skriv en kveldsbriefing på norsk bokmål for jaktdagene som starter $ARGUMENTS i jaktfeltet i Bygland (støkkjakt uten hund, to jegere). Standarddagene og rekkefølgen står i `config/route.json` under `standard_dager`.

Gjør dette, i rekkefølge:

1. Kjør `node scripts/plan_cli.js $ARGUMENTS` og les JSON-utskriften. Den planlegger dagene med samme kode som nettsiden og gir per dag: opplegg med start, slutt og biltekst, valgt og forkastet retning med km, høydemeter, timer, andel over 60, overlapp og andel av dragene mot vinden, vind per høydepunkt i dragene (`drag_vind`), feltene med høyde og score, og observasjonene som gjelder arten med vekt i dag og avstand til nærmeste felt.
2. Kjør `.venv/Scripts/python.exe scripts/briefing_data.py $ARGUMENTS` for været time for time per punkt (fjorden, Litjønni, Hakefjellet), sol opp og ned, og eventuelle timer med «unngå snaufjell» (terskel `vaer.vind_unngaa_snaufjell_ms` i `config/route.json`). Varselet gjelder første dag; for dag 2 og 3 kjør scriptet med deres datoer hvis varselet rekker.
3. Skriv tre avsnitt per dag, maks 80 ord per avsnitt, som en erfaren jaktkamerat ved kjøkkenbordet:
   - **Opplegg og biler**: art, start og slutt, gjennomgang eller rundtur, hvor bilene står, km, høydemeter og timer, og hvorfor retningen ble valgt fremfor den forkastede (bruk tallene).
   - **Vær og vind i dragene**: vind ved dragenes høyde om morgenen og midt på dagen, hvor stor andel av dragene som går mot vinden, temperatur, nedbør, sol opp og ned, og «unngå snaufjell»-timer hvis de finnes.
   - **Observasjoner og felt**: hvilke felt dagen går gjennom (høyde, størrelse, score), hva observasjonsdatabasen sier om dem (type, dato, kilde, vekt i dag, avstand), og om loggen eller kjerneområder sier noe. Finnes ingen observasjoner for arten, si det i én setning.
4. Ikke finn på tall. Alt skal komme fra utskriftene eller config-filene. Hvis varselet mangler for en dato, si det og bruk det som finnes.
5. Lagre briefingen som `logg/briefing-$ARGUMENTS.md` og vis den i chatten.
