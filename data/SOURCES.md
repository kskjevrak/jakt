# Datakilder

Generert av `scripts/download.py` 2026-10-20T12:39:24Z. Alle kilder er åpne data (NLOD / CC BY 4.0) med mindre annet er nevnt.
Rekkefølge som ble forsøkt per kilde: (1) WFS/WCS/REST, (2) Atom feed, (3) Geonorge/NIBIO nedlastings-API, (4) manuelt.

| Kilde | Vei som fungerte | Størrelse | Datert (server) | Hentet |
|---|---|---|---|---|
| SR16 Skogressurskart raster (16 m) | NIBIO nedlastings-API (fylkesfil) + klipp til AOI | 1.7 GB | Mon, 31 Aug 2026 11:41:18 GMT | 2026-10-20 |
| Artskart funn (lirype, orrfugl, storfugl) | REST (Artskart public API) | 2.6 kB | 2011-10-24 – 2026-10-20 | 2026-10-20 |
| FKB-AR5 arealressurs | WMS GetMap 5 m dekodet via SLD (vektor er Norge digitalt-begrenset) | 6.0 MB | Mon, 31 Mar 2025 14:30:02 GMT | 2026-10-20 |
| N50 Kartdata | Atom feed (kommunefil GML) | 23.9 MB | Fri, 16 Oct 2026 04:57:39 GMT | 2026-10-20 |
| Høyde – NHM DTM (1 m, hentet som 2 m) | WCS 1.0.0 (Kartverket NHM DTM) | 140.1 MB | – | 2026-10-20 |
| Matrikkelen – Eiendomskart Teig | WFS (Kartverket) + REST-validering | 4.5 MB | 2026-02-25T13:16:28.043 | 2026-10-20 |

## SR16 Skogressurskart raster (16 m)

Datasett: NIBIO, uuid 5de45872-f534-4e97-840e-3cfd8db04398  
Lisens: CC BY 4.0 (NLOD)  
Status: OK via **NIBIO nedlastings-API (fylkesfil) + klipp til AOI**

Forsøk:
- FEIL WCS: `https://wcs.nibio.no/cgi-bin/sr16` – vertsnavn finnes ikke; wms.nibio.no/cgi-bin/sr16 gir ServiceException for SERVICE=WCS
- FEIL Atom: `https://kartkatalog.geonorge.no/api/getdata/5de45872-f534-4e97-840e-3cfd8db04398` – ingen Atom-feed registrert for datasettet
- OK Nedlastings-API: `https://kartkatalog.nibio.no/api/v2/can-download` – {"canDownload":true}
- OK Nedlastings-API: `https://kartkatalog.nibio.no/api/v2/order` – ordre a4fa3da6-1a19-4d92-bb47-5b27a023725f, fil 42_25833_sr16_RASTER.zip status ReadyForDownload

Filer:
- `raw\sr16\42_25833_sr16_RASTER.zip` (1.7 GB, Last-Modified: Mon, 31 Aug 2026 11:41:18 GMT, hentet 2026-10-20T12:37:34Z)  
  `https://kart8.nibio.no/uttak_Download/sr16raster/42_25833_sr16_RASTER.zip`
- `raw\sr16\aoi_treslag.tif` (48.0 kB, Last-Modified: ?, hentet 2026-10-20T12:39:23Z)  
- `raw\sr16\aoi_hoyde.tif` (562.1 kB, Last-Modified: ?, hentet 2026-10-20T12:39:23Z)  
- `raw\sr16\aoi_overhoyde.tif` (583.3 kB, Last-Modified: ?, hentet 2026-10-20T12:39:23Z)  
- `raw\sr16\aoi_volum.tif` (627.8 kB, Last-Modified: ?, hentet 2026-10-20T12:39:23Z)  
- `raw\sr16\aoi_bonitet.tif` (70.6 kB, Last-Modified: ?, hentet 2026-10-20T12:39:23Z)  
- `raw\sr16\aoi_kronedekning.tif` (225.2 kB, Last-Modified: ?, hentet 2026-10-20T12:39:23Z)  
- `raw\sr16\aoi_grunnflate.tif` (427.1 kB, Last-Modified: ?, hentet 2026-10-20T12:39:23Z)  
- `raw\sr16\aoi_diameter.tif` (395.0 kB, Last-Modified: ?, hentet 2026-10-20T12:39:23Z)  
- `raw\sr16\aoi_treantall.tif` (671.6 kB, Last-Modified: ?, hentet 2026-10-20T12:39:23Z)  
- `raw\sr16\aoi_alder.tif` (589.9 kB, Last-Modified: ?, hentet 2026-10-20T12:39:24Z)  

Merknader:
- Klippet til AOI: treslag, hoyde, overhoyde, volum, bonitet, kronedekning, grunnflate, diameter, treantall, alder
- Kjøretid 1 s

## Artskart funn (lirype, orrfugl, storfugl)

Datasett: Artsdatabanken Artskart public API, observations/list  
Lisens: CC BY 4.0 (per datasett)  
Status: OK via **REST (Artskart public API)**

Versjon/dato: 2011-10-24 – 2026-10-20

Forsøk:
- OK REST: `https://artskart.artsdatabanken.no/publicapi/api/observations/list?filter.taxons=3987&filter.wktPolygon=...` – 4 funn av lirype totalt i polygonet, 0 siste 15 år
- OK REST: `https://artskart.artsdatabanken.no/publicapi/api/observations/list?filter.taxons=203489&filter.wktPolygon=...` – 7 funn av orrfugl totalt i polygonet, 3 siste 15 år
- OK REST: `https://artskart.artsdatabanken.no/publicapi/api/observations/list?filter.taxons=203484&filter.wktPolygon=...` – 4 funn av storfugl totalt i polygonet, 1 siste 15 år

Filer:
- `data/artskart.geojson` (2.6 kB, Last-Modified: ?, hentet 2026-10-20T12:38:04Z)  
  `https://artskart.artsdatabanken.no/publicapi/api/observations/list`

Merknader:
- 4 funn totalt. Observatørnavn lagres ikke.
- Kjøretid 1 s

## FKB-AR5 arealressurs

Datasett: Geovekst/NIBIO FKB-AR5, uuid 166382b4-82d6-4ea9-a68e-6fd0c87bf788  
Lisens: FKB-AR5 vektor: Norge digitalt-begrenset. AR5 WMS og AR50: NLOD/CC BY 4.0  
Status: OK via **WMS GetMap 5 m dekodet via SLD (vektor er Norge digitalt-begrenset)**

Forsøk:
- FEIL WFS: `https://wfs.nibio.no/cgi-bin/ar5` – MapServer Message  
 
 
msLoadMap(): Unable to access file. (/var/www/wfs/ar5/ar5.map)
- FEIL WFS: `https://wfs.nibio.no/cgi-bin/ar5_2` – MapServer Message  
 
 
msLoadMap(): Unable to access file. (/var/www/wfs/ar5_2/ar5_2.map)
- FEIL Atom: `https://nedlasting.geonorge.no/api/download/file//166382b4-82d6-4ea9-a68e-6fd0c87bf788/C37E2E92-BA17-44AA-843C-DA2EDE448437` – HTTP 403; feed-kategori: Norge digitalt-begrenset
- FEIL Nedlastings-API (Geonorge): `https://nedlasting.geonorge.no/api/capabilities/166382b4-82d6-4ea9-a68e-6fd0c87bf788` – krever rolle: nd.filnedlasting,nd.landbrukspart,nd.filnedlasting.fkb
- OK WMS GetStyles: `https://wms.nibio.no/cgi-bin/ar5?REQUEST=GetStyles` – Arealtype: 11 klasser, Grunnforhold: 6 klasser, Skogbonitet: 5 klasser, Treslag: 4 klasser
- OK WMS GetMap: `https://wms.nibio.no/cgi-bin/ar5?REQUEST=GetMap&CRS=EPSG:25833&LAYERS=...` – 4 lag à 2410x1308 px, 5 m
- OK WMS GetFeatureInfo: `https://wms.nibio.no/cgi-bin/ar5?REQUEST=GetFeatureInfo&INFO_FORMAT=application/vnd.ogc.gml` – 12/12 stikkprøver: dekodet artype/treslag/grunnforhold = attributter fra GetFeatureInfo
- OK Nedlastings-API (AR50, NIBIO): `https://kartkatalog.nibio.no/api/v2/order` – 4220_4258_ar50_gdb.zip gdb EPSG:4258

Filer:
- `raw\ar5\ar5_arealtype_5m.tif` (135.7 kB, Last-Modified: ?, hentet 2026-10-20T12:38:06Z)  
  `https://wms.nibio.no/cgi-bin/ar5`
- `raw\ar5\ar5_treslag_5m.tif` (149.7 kB, Last-Modified: ?, hentet 2026-10-20T12:38:06Z)  
  `https://wms.nibio.no/cgi-bin/ar5`
- `raw\ar5\ar5_skogbonitet_5m.tif` (119.5 kB, Last-Modified: ?, hentet 2026-10-20T12:38:07Z)  
  `https://wms.nibio.no/cgi-bin/ar5`
- `raw\ar5\ar5_grunnforhold_5m.tif` (170.0 kB, Last-Modified: ?, hentet 2026-10-20T12:38:07Z)  
  `https://wms.nibio.no/cgi-bin/ar5`
- `raw\ar5\ar50\4220_4258_ar50_gdb.zip` (5.5 MB, Last-Modified: Mon, 31 Mar 2025 14:30:02 GMT, hentet 2026-10-20T12:31:53Z)  
  `https://kart8.nibio.no/uttak_Download/ar50/4220_4258_ar50_gdb.zip`

Merknader:
- Skogbonitet-dekoding: (WMS-stilkode grvanlig, AR5 arskogbon) observert: [(8, 13), (9, 12), (10, 11)]. AR5 arskogbon: 11 impediment, 12 lav, 13 middels, 14 høg, 15 særs høg.
- Vektor-AR5 er ikke åpen; klassene er rasterisert fra NIBIO sin AR5 WMS i 5 m og aggregeres til 10 m i build. Kantpiksler mellom to klasser kan få nærmeste legendefarge.
- Kjøretid 5 s

## N50 Kartdata

Datasett: Kartverket, uuid ea192681-d039-42ec-b1bc-f3ce04c189ac  
Lisens: CC BY 4.0  
Status: OK via **Atom feed (kommunefil GML)**

Forsøk:
- FEIL WFS: `https://kartkatalog.geonorge.no/api/search?text=N50 Kartdata WFS` – ingen N50 WFS registrert i Geonorge
- OK Atom: `https://nedlasting.geonorge.no/geonorge/Basisdata/N50Kartdata/GML/Basisdata_4220_Bygland_25833_N50Kartdata_GML.zip` – kommunefil GML EPSG:25833

Filer:
- `raw\n50\Basisdata_4220_Bygland_25833_N50Kartdata_GML.zip` (23.9 MB, Last-Modified: Fri, 16 Oct 2026 04:57:39 GMT, hentet 2026-10-20T12:23:35Z)  
  `https://nedlasting.geonorge.no/geonorge/Basisdata/N50Kartdata/GML/Basisdata_4220_Bygland_25833_N50Kartdata_GML.zip`

Merknader:
- Kjøretid 9 s

## Høyde – NHM DTM (1 m, hentet som 2 m)

Datasett: Kartverket, Nasjonal detaljert høydemodell DTM, WCS coverage nhm_dtm_topo_25833  
Lisens: CC BY 4.0  
Status: OK via **WCS 1.0.0 (Kartverket NHM DTM)**

Forsøk:
- OK WCS 1.0.0: `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833?service=WCS&version=1.0.0&request=GetCoverage&coverage=nhm_dtm_topo_25833` – 35 fliser à 2000 m / 2 m oppløsning
- FEIL WCS 1.1.2: `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833?version=1.1.2` – UnSupportedCombination: image/GeoTIFF does not support the coverage data type
- FEIL WCS 2.0.1: `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833?version=2.0.1` – ArcGIS Server http.400 på alle GetCoverage-varianter
- OK REST: `https://ws.geonorge.no/hoydedata/v1/punkt` – punkthøyder for kjente topper

Filer:
- `raw\dtm\tiles\dtm2m_72000_6534000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:29:39Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_72000_6536000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:29:42Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_72000_6538000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:29:45Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_72000_6540000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:29:48Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_72000_6542000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:29:52Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_74000_6534000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:29:55Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_74000_6536000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:29:58Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_74000_6538000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:01Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_74000_6540000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:04Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_74000_6542000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:08Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_76000_6534000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:11Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_76000_6536000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:15Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_76000_6538000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:19Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_76000_6540000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:23Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_76000_6542000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:27Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_78000_6534000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:30Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_78000_6536000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:34Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_78000_6538000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:38Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_78000_6540000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:41Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_78000_6542000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:45Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_80000_6534000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:51Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_80000_6536000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:55Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_80000_6538000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:30:59Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_80000_6540000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:03Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_80000_6542000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:07Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_82000_6534000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:11Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_82000_6536000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:14Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_82000_6538000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:17Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_82000_6540000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:21Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_82000_6542000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:25Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_84000_6534000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:28Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_84000_6536000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:30Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_84000_6538000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:35Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_84000_6540000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:39Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`
- `raw\dtm\tiles\dtm2m_84000_6542000.tif` (4.0 MB, Last-Modified: ?, hentet 2026-10-20T12:31:42Z)  
  `https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833`

Merknader:
- Hakefjellet: høyde-API 872.0 m (dtm1), forventet 873 m, avvik -1.0 m (stedsnavnpunktet er ikke nødvendigvis toppunktet)
- Skjevraknuten: høyde-API 783.9 m (dtm1), forventet 786 m, avvik -2.1 m (stedsnavnpunktet er ikke nødvendigvis toppunktet)
- Hukebuvatnet: høyde-API 584.0 m (innsjohoyde), forventet 584 m, avvik +0.0 m (stedsnavnpunktet er ikke nødvendigvis toppunktet)
- Fallback dokumentert, ikke brukt: Geonorge nedlastings-API, DTM 10 UTM33 uuid dddbb667-1303-4ac5-8640-7ec04c0e3918.
- Kjøretid 128 s

## Matrikkelen – Eiendomskart Teig

Datasett: Kartverket, uuid 74340c24-1c8a-4454-b813-bfe498e80f16 (daglig oppdatert)  
Lisens: CC BY 4.0  
Status: OK via **WFS (Kartverket) + REST-validering**

Versjon/dato: 2026-02-25T13:16:28.043

Forsøk:
- OK REST: `https://api.kartverket.no/eiendom/v1/geokoding?matrikkelnummer=4220-49/1` – 5 teig(er) for 49/1, 1 feste/seksjon-teig(er)
- OK REST: `https://api.kartverket.no/eiendom/v1/geokoding?matrikkelnummer=4220-49/2` – 7 teig(er) for 49/2, 0 feste/seksjon-teig(er)
- OK REST: `https://api.kartverket.no/eiendom/v1/geokoding?matrikkelnummer=4220-49/3` – 9 teig(er) for 49/3, 0 feste/seksjon-teig(er)
- OK REST: `https://api.kartverket.no/eiendom/v1/geokoding?matrikkelnummer=4220-49/4` – 2 teig(er) for 49/4, 0 feste/seksjon-teig(er)
- OK REST: `https://api.kartverket.no/eiendom/v1/geokoding?matrikkelnummer=4220-50/1` – 10 teig(er) for 50/1, 0 feste/seksjon-teig(er)
- OK WFS: `https://wfs.geonorge.no/skwms1/wfs.matrikkelen-eiendomskart-teig?service=WFS&version=2.0.0&request=GetFeature&typeNames=app:Teig&bbox=...` – 522 teiger i bbox (73260, 6534864, 87110, 6542921)

Filer:
- `raw\teig\teig_wfs.gml` (4.5 MB, Last-Modified: ?, hentet 2026-10-20T12:22:36Z)  
  `https://wfs.geonorge.no/skwms1/wfs.matrikkelen-eiendomskart-teig`

Merknader:
- 34 teigpunkter fra REST for 5 matrikkelenheter; 522 teiger lastet i bbox med 2500 m margin.
- Kjøretid 6 s
- Jaktfelt 2139.0 ha, 33 teiger + 1 festeteiger, 37 naboteiger innen 500 m
- Flagget: ['49/3,5 (flere matrikkelenheter)']
