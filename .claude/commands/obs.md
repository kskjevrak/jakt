---
description: Legg observasjoner i data/observasjoner.geojson fra fritekst, med tabell for godkjenning før commit
argument-hint: <fritekst om hva som ble sett, hvor og når>
---

Strukturer observasjonen(e) under etter schemaet i `data/observasjoner.geojson`, vis en tabell for godkjenning, og legg dem inn når brukeren sier ja.

Fritekst: $ARGUMENTS

Gjør dette, i rekkefølge:

1. Les `metadata._doc` øverst i `data/observasjoner.geojson` for schemaet: id (lages av scriptet), dato (ISO, bruk den oppgitte eller spør), dato_usikker (true hvis teksten er omtrentlig, «medio», «forrige uke»), art (lirype, orrfugl, storfugl eller ukjent_honsefugl), kjonn (tiur eller roy for storfugl, hann eller hunn for orrfugl og rype, ellers ukjent), antall (tall eller null), type (sett, stokket, felt, spor eller omrade), kilde (navnet på den som så det, spør hvis det mangler), presisjon_m (tall eller null), notat (resten av teksten, uendret ordlyd så langt det går). Geometri er Point i WGS84 (lon, lat) eller Polygon.
2. Koordinater: bruk de som står i teksten (lat, lon i den rekkefølgen folk skriver dem; GeoJSON skal ha lon først). Et stedsnavn uten koordinat slås opp i `config/steder.json`, `config/start.json` eller med Kartverkets stedsnavn-API med `kommunenummer=4220`; skriv i notatet at posisjonen er fra stedsnavn. Et område («lia mot Nånes», «myrene øst for Bergebekken») tegnes som et enkelt polygon med 4–8 hjørner ut fra kartet og `data/jaktfelt.geojson`, type omrade, og du sier i tabellen at polygonet er skjønnsmessig.
3. Skriv features til en midlertidig fil i scratchpad-mappa og kjør `.venv/Scripts/python.exe scripts/obs_add.py <fil> --tabell`. Vis tabellen, inkludert kolonnen «innenfor» (om punktet ligger i jaktfeltet), og spør om godkjenning. Rett det brukeren ber om og kjør `--tabell` igjen.
4. Når brukeren godkjenner: kjør `.venv/Scripts/python.exe scripts/obs_add.py <fil>` (uten `--tabell`), så `git add data/observasjoner.geojson` og commit med melding på formen «Observasjoner: <art> <type> <dato>». Push hvis brukeren vil. Nettsiden leser filen direkte, og bonusen i cellene rundt følger reglene i `config/route.json` under `observasjoner`.
5. Finn aldri på dato, antall eller posisjon. Mangler noe, sett null eller spør.
