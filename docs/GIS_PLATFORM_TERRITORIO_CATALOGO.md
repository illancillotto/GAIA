# GAIA GIS Platform - Catalogo Territorio Esterno

> Data: 2026-08-27.
> Scope: censimento delle sorgenti cartografiche esterne da registrare nel
> catalogo GIS come layer di consultazione. Documento di riferimento dati, non
> piano di implementazione.
>
> Piano tecnico: `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`.
> Stato lavori: `docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md`.
> Prompt operativi: `docs/GIS_PLATFORM_TERRITORIO_PROMPTS.md`.

## Perche Questo Catalogo

La GIS Platform governa oggi solo layer che vivono nel PostGIS GAIA
(`source_type=postgis`, `postgis_staging`) o registri applicativi di dominio
(`source_type=domain_registry`). I dati territoriali di contesto - vincoli,
pericolosita, uso del suolo, ortofoto storiche, cartografia catastale ufficiale
- sono pubblicati gratuitamente da terzi via WMS e WFS e non devono essere
copiati dentro GAIA.

Questo documento definisce quali sorgenti esterne entrano nel catalogo, con
quale identificativo remoto e per rispondere a quale domanda operativa del
Consorzio.

## Principi Di Selezione

- Un layer entra nel catalogo solo se risponde a una domanda operativa
  dichiarata di un ufficio GAIA.
- La sorgente esterna resta autorevole per il proprio dato; GAIA resta
  autorevole per particelle, distretti, punti di consegna, rete e ruolo.
- Nessun layer esterno viene copiato in PostGIS: si consuma via WMS/WFS
  attraverso il proxy GAIA.
- Nessun layer esterno e modificabile, esportabile come shapefile o
  pubblicabile in QGIS governance come tabella.
- Un layer senza licenza accertata non entra in catalogo.
- Il perimetro geografico e il comprensorio consortile; la copertura nazionale
  non e un obiettivo.

## Sorgenti

### RAS SITR - GeoServer vettoriale

- Endpoint: `https://webgis.regione.sardegna.it/geoserver/ows`
- Servizi: WMS 1.3.0 e WFS 1.1.0 sullo stesso endpoint.
- GetCapabilities WMS verificato il 2026-08-27: `379` layer nel namespace
  `dbu:`.
- Il WFS sullo stesso endpoint abilita l'interrogazione per intersezione, non
  solo la resa grafica: e questo che rende possibile la fase M23.
- Il GeoServer ripubblica in cascata anche i layer AdE sotto `dbu:AdE_*`. Va
  preferito l'endpoint diretto dell'Agenzia; la cascata RAS resta fallback.

### RAS SITR - GeoServer raster

- Endpoint: `https://webgis.regione.sardegna.it/geoserverraster/ows`
- Servizio: WMS.
- Contiene ortofoto storiche, DTM/DSM da rilievo LiDAR, CTR e mosaici DBGT.
- Solo WMS: nessuna interrogazione per intersezione, uso esclusivamente come
  basemap alternativa o overlay.

### Agenzia delle Entrate - Cartografia Catastale INSPIRE

- Endpoint WMS: `https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php`
- Endpoint WFS: `https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php`
- Il WFS e gia usato dal modulo Catasto in
  `backend/app/modules/catasto/services/ade_wfs.py` con costante
  `ADE_WFS_URL`. La fase M21 non modifica quel percorso: aggiunge il WMS come
  layer di confronto visivo.
- Layer WMS disponibili: `CP.CadastralParcel`, `CP.CadastralZoning`,
  `fabbricati`, `acque`, `strade`, `vestizioni`, `province`, `codice_plla`,
  `simbolo_graffa`.

## Seed Catalogo M22

Workspace `territorio`, `domain_module=gis`. La colonna `name` e
l'identificativo GAIA nel catalogo; la colonna `remote_layer` e il nome sul
servizio remoto.

### Gruppo `bonifica` - perimetri consortili di riferimento

| name GAIA | remote_layer | titolo sorgente | domanda operativa |
| --- | --- | --- | --- |
| `ras_aree_bonifica` | `dbu:areebonifica` | PPR06 - Aree della bonifica | La particella ricade in area di bonifica? |
| `ras_comprensori_irrigui` | `dbu:agr_consorzi_irrigui_bonif_comprensori` | AGR - Consorzi di Bonifica - delimitazioni comprensori irrigui | Il comprensorio regionale coincide con il nostro? |
| `ras_distretti_irrigui` | `dbu:agr_consorzi_irrigui_bonif_distretti` | AGR - Consorzi di Bonifica - delimitazioni distretti irrigui | Confronto con `cat_distretti` GAIA. |

> Nota di governance: i distretti RAS non coincideranno con i nostri. La
> sovrapposizione e informativa. La fonte autorevole per il distretto resta
> GAIA. Va scritto nella descrizione del layer, non lasciato all'interpretazione
> dell'operatore.

### Gruppo `colture` - uso reale del suolo

| name GAIA | remote_layer | titolo sorgente | domanda operativa |
| --- | --- | --- | --- |
| `ras_uso_suolo_2008` | `dbu:usosuolo2008_areali` | Carta dell'Uso del Suolo 2008 - poligoni | Che uso del suolo e censito? |
| `ras_colture_2008` | `dbu:usosuolocolture2008` | Carta delle colture dell'Uso del Suolo | Confronto con la coltura dichiarata in DUI. |

### Gruppo `pericolosita` - PAI

| name GAIA | remote_layer | titolo sorgente | domanda operativa |
| --- | --- | --- | --- |
| `ras_pai_pericolo_idraulico` | `dbu:pai_pericolo_idraulico_rev_dic_23` | PAI - Pericolo Idraulico Rev. Dic_23 | Che pericolosita idraulica insiste sul tratto di rete? |
| `ras_pai_rischio_idraulico` | `dbu:pai_rischio_idraulico_rev_dic_23` | PAI - Rischio Idraulico Rev. Dic_23 | Qual e il rischio idraulico associato? |
| `ras_pai_pericolo_geomorfologico` | `dbu:pai_pericolo_geomorfologico_rev_dic_23` | PAI - Pericolo Geomorfologico Rev. Dic_23 | Ci sono criticita geomorfologiche sul tracciato? |

> Le revisioni PAI cambiano nel tempo. Il catalogo registra la revisione
> nell'identificativo remoto e nel titolo: un aggiornamento di revisione e un
> nuovo layer, non una modifica silenziosa di quello esistente.

### Gruppo `vincoli`

| name GAIA | remote_layer | titolo sorgente | domanda operativa |
| --- | --- | --- | --- |
| `ras_vincolo_idrogeologico` | `dbu:vincolo_idrogeologico_sardegna_rdl_3267_1923` | Vincolo Idrogeologico ai sensi del RDL 3267/1923 | Posso intervenire sulla rete in quel punto? |
| `ras_beni_paesaggistici` | `dbu:benipaesaggisticiexart136_142` | PPR06 - Beni paesaggistici storico culturali puntuali ex artt. 136 e 142 D.Lgs. 42/04 | Ci sono beni tutelati interferenti? |
| `ras_fascia_150m_fiumi` | `dbu:art142_fascia_150m_fiumi_indic` | Art. 142 - Fascia di 150 m dai fiumi (dati indicativi) | Il tratto ricade in fascia di tutela fluviale? |
| `ras_siti_interesse_comunitario` | `dbu:sitiinteressecomunitario` | PPR06 - Siti di interesse comunitario | Interferenza con Rete Natura 2000. |

> Il layer `art142_fascia_150m_fiumi_indic` e dichiarato indicativo dalla
> sorgente stessa. La descrizione in catalogo deve riportarlo, e la scheda
> territoriale M24 deve trattarlo come segnalazione, mai come accertamento.

### Gruppo `idrografia`

| name GAIA | remote_layer | titolo sorgente | domanda operativa |
| --- | --- | --- | --- |
| `ras_reticolo_idrografico` | `dbu:dbgt_10k_22_v05_04_reticolo_idrografico` | DBGT10K_22_v05 - 04 Reticolo Idrografico | Il reticolo interferisce con la nostra rete? |
| `ras_reticolo_naturale` | `dbu:dbgt_10k_22_v05_04_reticolo_idrografico_naturale` | DBGT10K_22_v05 - 04 Reticolo Idrografico Naturale | Distinzione naturale/artificiale. |
| `ras_laghi_invasi_stagni` | `dbu:laghiinvasistagni` | PPR06 - Laghi naturali, invasi artificiali, stagni e lagune | Corpi idrici di riferimento. |

### Gruppo `amministrativo`

| name GAIA | remote_layer | titolo sorgente | domanda operativa |
| --- | --- | --- | --- |
| `ras_limiti_comunali` | `dbu:limiti_amministr_com_ctr` | Limiti amministrativi comunali CTR | Attribuzione comunale della particella. |

### Gruppo `eventi`

| name GAIA | remote_layer | titolo sorgente | domanda operativa |
| --- | --- | --- | --- |
| `ras_aree_incendiate_2024` | `dbu:areeincendiateperim2024` | CFVA - Perimetri dei soprassuoli percorsi dal fuoco - 2024 | Rilevante per esenzioni, danni e contenzioso sul ruolo. |

> La serie `areeincendiateperim*` esiste per anno dal 2005. Il seed registra
> solo l'anno piu recente disponibile. Gli anni precedenti si aggiungono su
> richiesta motivata, secondo la regola di governo del catalogo.

### Gruppo `catasto_ufficiale`

| name GAIA | remote_layer | sorgente | domanda operativa |
| --- | --- | --- | --- |
| `ade_particelle_wms` | `CP.CadastralParcel` | AdE Cartografia Catastale | La nostra geometria coincide con quella ufficiale? |
| `ade_zone_censuarie_wms` | `CP.CadastralZoning` | AdE Cartografia Catastale | Inquadramento censuario. |
| `ade_fabbricati_wms` | `fabbricati` | AdE Cartografia Catastale | Presenza di fabbricati sulla particella. |

### Gruppo `ortofoto` - basemap alternative

Sorgente: GeoServer raster RAS. Solo WMS, nessuna interrogazione.

| name GAIA | remote_layer | uso |
| --- | --- | --- |
| `ras_ortofoto_2022` | `raster:Mosaico_2022_GB` | Ortofoto piu recente disponibile. |
| `ras_ortofoto_2019` | `raster:ortofoto_2019` | Confronto recente. |
| `ras_ortofoto_2013` | `raster:ortofoto_2013` | Confronto decennale. |
| `ras_ortofoto_2006` | `raster:ortofoto_2006` | Confronto storico. |
| `ras_ortofoto_1997` | `raster:ortofoto_1997` | Confronto storico. |
| `ras_ortofoto_1977` | `raster:ortofoto_1977_1978` | Ricostruzione usi consolidati. |
| `ras_ortofoto_1954` | `raster:ortofoto_1954_1955` | Volo storico, riferimento per contenzioso. |
| `ras_ortofoto_1940` | `raster:ortofoto_1940_1945` | Volo storico piu antico disponibile. |

### Gruppo `morfologia`

| name GAIA | remote_layer | uso |
| --- | --- | --- |
| `ras_dtm_1m` | `raster:DTM_1m_altimetrie` | Quote da rilievo LiDAR per dimensionamento tratti. |
| `ras_dtm_1m_hillshade` | `raster:DTM_1m_hillshade` | Lettura morfologica del terreno. |
| `ras_dtm_10m` | `raster:DTM_10m_altimetrie` | Copertura estesa dove manca il rilievo 1m. |

## Interrogabilita

Non tutti i layer del seed sono interrogabili allo stesso modo. La fase M23
deve trattare tre categorie distinte:

| categoria | sorgenti | modalita interrogazione |
| --- | --- | --- |
| `wfs_queryable` | RAS vettoriale, AdE | `GetFeature` WFS con filtro spaziale. Restituisce attributi strutturati. |
| `wms_infoable` | layer vettoriali senza WFS affidabile | `GetFeatureInfo` WMS. Restituisce testo o HTML da normalizzare. |
| `wms_visual_only` | ortofoto, DTM, mosaici raster | Nessuna interrogazione. Solo resa grafica. |

La categoria va registrata nei metadata del layer al momento del seed e non
dedotta a runtime.

## Verifica Sorgenti

Comandi usati il 2026-08-27 per censire i layer. Da rieseguire prima di ogni
revisione del seed.

```bash
# RAS vettoriale: elenco layer
curl -sS "https://webgis.regione.sardegna.it/geoserver/ows?service=WMS&version=1.3.0&request=GetCapabilities" \
  | grep -o "<Name>dbu:[^<]*</Name>" | sed 's/<[^>]*>//g' | sort -u

# RAS raster: elenco layer
curl -sS "https://webgis.regione.sardegna.it/geoserverraster/ows?service=WMS&request=GetCapabilities" \
  | grep -o "<Name>[^<]*</Name>" | sed 's/<[^>]*>//g' | sort -u

# AdE cartografia catastale: elenco layer
curl -sS "https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php?service=WMS&request=GetCapabilities&version=1.3.0" \
  | grep -o "<Name>[^<]*</Name>" | sed 's/<[^>]*>//g'
```

## Licenze

Da accertare e registrare in `metadata_json.license` e
`metadata_json.attribution` prima del seed M22. Il campo non e opzionale: il
bootstrap deve rifiutare una definizione senza licenza.

Verifiche richieste prima di chiudere M22:

- condizioni d'uso pubblicate dal SITR della Regione Sardegna per i layer
  vettoriali e raster;
- condizioni d'uso del servizio WMS Cartografia Catastale dell'Agenzia delle
  Entrate;
- obblighi di attribuzione da riportare in mappa e nella scheda territoriale
  M24.

Se una licenza non risulta accertabile per un layer, il layer resta fuori dal
seed e la decisione va registrata nel progress con la motivazione.
