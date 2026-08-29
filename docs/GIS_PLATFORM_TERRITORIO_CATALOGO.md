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

Nessun layer PAI e ammesso nel seed dopo P0. I tre layer candidati sono ancora
pubblicati dal servizio, ma i record GeoNetwork indicati dalle capabilities
restituiscono `404`; senza condizioni d'uso accertabili restano esclusi. Il
dettaglio e nella sezione "Licenze".

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
| `ras_ortofoto_1977` | `raster:ortofoto_1977_1978` | Ricostruzione usi consolidati. |

Le altre ortofoto candidate non entrano nel seed: i rispettivi metadati
richiedono autorizzazioni del proprietario o dichiarano copyright. Possono
essere rivalutate solo dopo autorizzazione scritta; il dettaglio e nella
sezione "Licenze".

### Gruppo `morfologia`

| name GAIA | remote_layer | uso |
| --- | --- | --- |
| `ras_dtm_1m` | `raster:DTM_1M_MOSAICO_ALTIMETRIA` | Quote da rilievo LiDAR per dimensionamento tratti. |
| `ras_dtm_1m_hillshade` | `raster:DTM_1M_MOSAICO_OMBRE` | Lettura morfologica del terreno. |
| `ras_dtm_10m` | `raster:DTM_10M_ALTIMETRIA_REV01` | Copertura estesa dove manca il rilievo 1m. |

P0 ha corretto i tre identificativi: quelli censiti inizialmente
(`DTM_1m_altimetrie`, `DTM_1m_hillshade`, `DTM_10m_altimetrie`) erano nomi di
stile presenti nelle capabilities, non nomi di layer WMS.

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

Verifica P0 eseguita il 2026-08-27 sulle condizioni pubblicate e sui metadati
raggiungibili dai documenti GetCapabilities. La licenza e l'attribuzione sono
obbligatorie in `metadata_json`; M22 deve registrare i valori letterali qui
definiti e rifiutare definizioni incomplete.

### Condizioni Per Sorgente

| sorgente | decisione P0 | licenza e condizioni | attribuzione obbligatoria |
| --- | --- | --- | --- |
| RAS SITR vettoriale | ammessa con vincoli | `CC BY 4.0` solo per i 14 layer rimasti nel seed, confermata dai singoli metadati; WFS limitato a `100000` feature per richiesta | `Dati: Regione Autonoma della Sardegna - Sardegna Geoportale, "<titolo layer>", licenza CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Nessuna modifica ai dati; resa cartografica tramite GAIA.` |
| RAS SITR raster | ammessa con vincoli | `CC BY 4.0` per ortofoto 1977-78 e i tre DTM corretti; tutte le altre ortofoto candidate sono escluse | stesso testo RAS, con il titolo specifico del layer |
| AdE Cartografia Catastale WMS | ammessa con vincoli | `CC BY 4.0`; l'Agenzia puo sospendere o limitare accessi che disturbano il servizio e dichiara un limite massimo, non quantificato, di richieste contemporanee | `Dati: Agenzia delle Entrate - Cartografia Catastale, licenza CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Titolarita dei dati: Agenzia delle Entrate. Nessuna modifica ai dati; resa cartografica tramite GAIA.` |

Se GAIA modifica o trasforma dati CC BY, `Nessuna modifica ai dati` va
sostituito da una descrizione sintetica delle modifiche. La sola
riproiezione/resa eseguita dal servizio remoto non e una modifica operata da
GAIA.

Fonti ufficiali consultate:

- RAS, [Note legali e condizioni d'uso dei dati](https://www.sardegnageoportale.it/documentazione/notelegali/): i dati di proprieta RAS con metadato `Nessuna limitazione d'uso` sono CC BY 4.0; per dati di altri enti e ortofoto prevale il singolo metadato o la licenza dedicata;
- RAS, [servizio WMS](https://www.sardegnageoportale.it/index.php?xsl=2425&s=324505&v=2&c=14488&t=1&tb=14401) e [servizio WFS](https://www.sardegnageoportale.it/index.php?xsl=2425&s=324508&v=2&c=14489&t=1&tb=14401): nessun limite di frequenza numerico pubblicato per WMS; massimo `100000` feature per richiesta WFS;
- AdE, [Consultazione cartografia catastale WMS](https://www.agenziaentrate.gov.it/portale/web/guest/schede/fabbricatiterreni/consultazione-cartografia-catastale/servizio-consultazione-cartografia): CC BY 4.0, citazione obbligatoria della titolarita AdE, limite concorrente non quantificato e possibile sospensione per uso disturbante.

Non risultano SLA o rate limit numerici ulteriori pubblicati. M21 deve quindi
usare timeout, cache, richieste serializzate o limitate, backoff su `429`/`5xx`
e degradazione governata; la licenza non va interpretata come garanzia di
disponibilita.

### Esclusioni P0

| layer candidato | decisione | evidenza e motivazione |
| --- | --- | --- |
| `dbu:pai_pericolo_idraulico_rev_dic_23` | escluso | layer WMS presente, ma il [record GeoNetwork](https://webgis2.regione.sardegna.it/geonetwork/srv/ita/catalog.search#/metadata/R_SARDEG:132322a2-9287-4a38-bfcb-843dfb27d6f4) restituisce `404` via API: licenza non accertabile |
| `dbu:pai_rischio_idraulico_rev_dic_23` | escluso | layer WMS presente, ma il [record GeoNetwork](https://webgis2.regione.sardegna.it/geonetwork/srv/ita/catalog.search#/metadata/R_SARDEG:f86ae5a0-7b76-47d0-8e35-f55b8515e4a2) restituisce `404` via API: licenza non accertabile |
| `dbu:pai_pericolo_geomorfologico_rev_dic_23` | escluso | layer WMS presente, ma il [record GeoNetwork](https://webgis2.regione.sardegna.it/geonetwork/srv/ita/catalog.search#/metadata/R_SARDEG:ab75d78e-c23d-4224-b24a-903bcc32b238) restituisce `404` via API: licenza non accertabile |
| `raster:Mosaico_2022_GB` | escluso | il [metadato](https://webgis2.regione.sardegna.it/geonetwork/srv/ita/catalog.search#/metadata/R_SARDEG:b4355702-ed36-4f2e-97c8-07e65e785efc) richiede agli utenti terzi autorizzazione del proprietario |
| `raster:ortofoto_2019` | escluso | il [metadato](https://webgis2.regione.sardegna.it/geonetwork/srv/ita/catalog.search#/metadata/R_SARDEG:c82b8535-50b8-4f00-8a5e-a3ae24c33030) richiede agli utenti terzi autorizzazione del proprietario |
| `raster:ortofoto_2013` | escluso | il [metadato](https://webgis2.regione.sardegna.it/geonetwork/srv/ita/catalog.search#/metadata/R_SARDEG:6b5bd1ad-7730-4b2f-af64-59a7c69b14d1) richiede agli utenti terzi autorizzazione del proprietario |
| `raster:ortofoto_2006` | escluso | il [metadato](https://webgis2.regione.sardegna.it/geonetwork/srv/ita/catalog.search#/metadata/R_SARDEG:MFOMJ) richiede agli utenti terzi autorizzazione del proprietario |
| `raster:ortofoto_1997` | escluso | il [metadato](https://webgis2.regione.sardegna.it/geonetwork/srv/ita/catalog.search#/metadata/R_SARDEG:8514adfb-02f8-4b84-8cd5-1d9d22b2ee65) dichiara dato soggetto a copyright e accesso pubblico limitato |
| `raster:ortofoto_1954_1955` | escluso | il [metadato](https://webgis2.regione.sardegna.it/geonetwork/srv/ita/catalog.search#/metadata/R_SARDEG:OWSCQ) richiede agli utenti terzi autorizzazione del proprietario |
| `raster:ortofoto_1940_1945` | escluso | il [metadato](https://webgis2.regione.sardegna.it/geonetwork/srv/ita/catalog.search#/metadata/R_SARDEG:XKPUR) richiede agli utenti terzi autorizzazione del proprietario |

Le esclusioni sono dal seed, non dal censimento. Possono essere riaperte solo
con condizioni d'uso nuovamente pubblicate o autorizzazione scritta che copra
l'uso GAIA e il testo di attribuzione.

### Disponibilita E Tempi P0

I GetCapabilities sono stati rieseguiti il 2026-08-27. Il confronto usa solo i
`Name` figli diretti di `Layer`, per non confondere i nomi di stile con i
`remote_layer`:

- RAS vettoriale: `379` layer `dbu:`, tutti i 14 layer ammessi presenti;
- RAS raster: `52` layer, i quattro layer ammessi presenti dopo la correzione
  dei nomi DTM;
- AdE WMS: `13` layer nominati, tutti i tre layer del seed presenti;
- nessun layer ammesso risulta scomparso o rinominato; i tre DTM erano stati
  censiti inizialmente con il nome dello stile e sono stati corretti.

Misure seriali da host di sviluppo in Italia, tre richieste per riga, cache
remota non controllata. GetMap: WMS `256x256`, PNG, bounding box Sardegna.
GetFeature: WFS 1.1.0, `maxFeatures=1`, JSON, senza filtro spaziale. I valori
sono mediana e intervallo min-max del tempo totale di `curl`:

| layer | GetMap | GetFeature | esito e dimensione risposta |
| --- | --- | --- | --- |
| `dbu:areebonifica` | `0.732 s` (`0.296-0.807`) | `0.276 s` (`0.266-0.277`) | HTTP 200; PNG `5013 B`, JSON `8151 B` |
| `dbu:agr_consorzi_irrigui_bonif_comprensori` | `0.427 s` (`0.382-0.498`) | `0.600 s` (`0.565-0.661`) | HTTP 200; PNG `13361 B`, JSON `522356 B` |
| `dbu:usosuolo2008_areali` | `0.273 s` (`0.271-0.273`) | `0.304 s` (`0.299-0.319`) | HTTP 200; PNG `1784 B`, JSON `3324 B` |
| `raster:ortofoto_1977_1978` | `0.545 s` (`0.526-0.553`) | non applicabile | HTTP 200; PNG `115100 B` |
| `CP.CadastralParcel` | `0.223 s` (`0.217-0.230`) | non misurato in P0 | HTTP 200; PNG `2747 B` |

Le misure non sono un SLA. Per M21 resta appropriato un timeout remoto di
default `12 s`, con timeout piu corto per i probe, per assorbire immagini piu
grandi, filtri spaziali, cold cache e variabilita dei servizi pubblici.
