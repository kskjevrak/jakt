---
description: Les jaktloggen og foreslå justerte vekter og terskler i config/habitat.json med begrunnelse
argument-hint: [glob for loggfiler, standard logg/*.geojson]
---

Foreslå justeringer av habitatreglene i `config/habitat.json` basert på hvor fuglene faktisk ble støkt og felt.

Gjør dette, i rekkefølge:

1. Kjør `.venv/Scripts/python.exe scripts/tune_data.py $ARGUMENTS` og les JSON-utskriften. Den kobler hver registrering i de eksporterte loggfilene til nærmeste 50 m-celle i `data/grid.geojson` og gir per art: score ved funn mot middelscore i jaktfeltet, andel funn i celler under 60, og fordelingen av høyde, helning, eksposisjon, arealtype, treslag, kronedekning og avstander til myr, bekk og skoggrense. Kodene er forklart under `variabler`.
2. Les `config/habitat.json` og se hvilke faktorer og straffer som finnes for hver art, med trapes-punkter, klasser og vekter.
3. Vurder per art, bare der det finnes minst 3 registreringer:
   - Ligger funnene systematisk utenfor en trapes (for eksempel høyde eller helning)? Foreslå å flytte punktene, aldri mer enn 20 prosent av bredden per runde.
   - Har funnene en klasse (arealtype, treslag, bonitet) som får lav verdi i dag? Foreslå å heve klassen, maks 0,2 per runde.
   - Er en faktor uten utslag (funnene har samme spredning som jaktfeltet ellers)? Foreslå lavere vekt.
   - Ikke foreslå endringer på grunnlag av færre enn 3 funn, og si tydelig hvor tynt grunnlaget er.
4. Skriv forslaget som en tabell med kolonnene Art, Faktor, I dag, Forslag, Begrunnelse (med tall fra utskriften). Legg til én setning om forventet effekt på arealet over 60, basert på `data/score_stats.json`.
5. Ikke endre `config/habitat.json` selv. Hvis brukeren godkjenner, gjør endringen, øk `versjon`, kjør `.venv/Scripts/python.exe scripts/build_scores.py` og deretter `.venv/Scripts/python.exe scripts/compare_scores.py`, og rapporter tabellen før og etter.
