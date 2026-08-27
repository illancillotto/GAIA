# GAIA GIS Platform - Prompt Operativi Territorio Esterno

> Data: 2026-08-27.
> Scope: prompt eseguibili per implementare M21-M25 del piano
> `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`.
>
> Ogni prompt e autoconsistente: puo essere incollato in una sessione pulita di
> Cursor senza contesto precedente. Eseguire i prompt in ordine. Non aprire un
> prompt prima che il precedente abbia superato i criteri di accettazione.
>
> Riferimento dati: `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md`.
> Stato lavori: `docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md`.

## Regole Comuni A Tutti I Prompt

Da applicare sempre, anche quando non ripetute nel singolo prompt.

- Backend monolite modulare: il codice nuovo va in
  `backend/app/modules/gis/`. Non creare backend separati.
- Coverage `100%` sui file runtime nuovi o modificati. Una change che introduce
  codice non coperto non e conforme.
- Quality ratchet: il perimetro toccato non puo peggiorare le metriche di
  complessita. `backend/app/modules/gis/services.py` (3441 righe) e
  `frontend/src/components/catasto/gis/MapContainer.tsx` (1552 righe) sono gia
  sopra soglia: il codice nuovo va in moduli e hook dedicati, mai aggiunto
  dentro questi file.
- Documentazione senza caratteri accentati, come tutti i doc `docs/GIS_*`
  esistenti.
- Preservare comportamento, API, schema dati, auth e UI esistenti salvo quanto
  esplicitamente richiesto.
- Un solo prompt per branch. Nome branch indicato in ogni prompt.
- A fine lavoro aggiornare `docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md` con
  evidenze reali (comandi eseguiti e loro output), non con dichiarazioni.
- Se una verifica fallisce, non dichiarare la milestone completata: registrare
  il blocco nel progress.

Comandi di verifica standard:

```bash
make lint-backend
make lint-frontend
$(COMPOSE) exec backend python -m pytest tests/<file di test toccati>
cd frontend && npm run typecheck && npm run test:unit
make complexity-changed BASE_REF=origin/main
make complexity-ratchet BASE_REF=origin/main
```

---

## P0 - Verifica Licenze E Disponibilita Sorgenti

Bloccante. Nessun codice. Da chiudere prima di P2.

Branch: nessuno, solo aggiornamento documentale.

### Prompt

```
Contesto: GAIA sta per registrare nel proprio catalogo GIS layer cartografici
esterni pubblicati da Regione Sardegna (SITR) e Agenzia delle Entrate. Prima di
scrivere codice va accertata la licenza d'uso di ogni sorgente.

Leggi `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md`, sezioni "Sorgenti", "Seed
Catalogo M22" e "Licenze".

Attivita:

1. Rieseguire i tre comandi GetCapabilities riportati nella sezione "Verifica
   Sorgenti" del catalogo e confermare che tutti i `remote_layer` elencati nel
   seed esistano ancora. Registrare eventuali layer scomparsi o rinominati.
2. Accertare le condizioni d'uso pubblicate per:
   - il SITR della Regione Sardegna, GeoServer vettoriale e raster;
   - il servizio WMS Cartografia Catastale dell'Agenzia delle Entrate.
3. Per ciascuna sorgente registrare: licenza, URL delle condizioni d'uso, testo
   di attribuzione richiesto, eventuali limiti di uso automatizzato o di
   frequenza di richiesta.
4. Misurare il tempo di risposta di una GetMap e di una GetFeature per almeno
   tre layer del seed, per avere un ordine di grandezza dei timeout da
   configurare in M21.

Output: aggiornare la sezione "Licenze" di
`docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md` con i risultati, e registrare in
`docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md` la decisione per ogni sorgente:
ammessa, ammessa con vincoli, esclusa. Per ogni esclusione indicare la
motivazione.

Non scrivere codice applicativo in questo passo.
```

### Criteri Di Accettazione

- Ogni sorgente del seed ha licenza accertata e testo di attribuzione.
- Ogni layer del seed e confermato esistente sul servizio remoto.
- Tempi di risposta misurati e registrati.
- Le esclusioni sono motivate nel progress.

---

## P1 - M21 Fondazione Layer Esterni

Branch: `feature/gis-territorio-external-layers-m21`.

### Prompt

```
Contesto: la GIS Platform di GAIA (`backend/app/modules/gis`) governa oggi solo
layer PostGIS (`source_type=postgis`, `postgis_staging`) e registri applicativi
(`source_type=domain_registry`). Va aggiunta la categoria dei layer esterni
consumati via WMS/WFS da servizi di terzi, senza copiare dati in PostGIS.

Leggi prima, in questo ordine:
- `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`, sezione "M21 - Fondazione Layer
  Esterni";
- `docs/GIS_PLATFORM_ARCHITECTURE.md`;
- `backend/app/modules/gis/models.py`;
- `backend/app/modules/gis/schemas.py`;
- `backend/app/modules/gis/router.py`;
- `backend/app/modules/gis/runtime_health.py`;
- `backend/app/modules/gis/bootstrap.py`;
- `backend/app/core/config.py`, sezione impostazioni `GIS_*`;
- `AGENTS.md`, sezioni "Test coverage policy" e "Code complexity program".

Implementa:

1. `backend/app/modules/gis/external_sources.py`
   - registro delle sorgenti esterne configurate: `source_key`, base URL,
     servizio (`wms` o `wfs`), versione, timeout, abilitazione;
   - sorgenti previste: `ras_sitr_vector`, `ras_sitr_raster`, `ade_catasto_wms`;
   - validazione della sezione `metadata_json.external` di un layer;
   - costruzione delle URL remote a partire da layer e richiesta.

2. `backend/app/modules/gis/external_proxy.py`
   - proxy HTTP con `httpx` (gia dipendenza);
   - allowlist rigida di operazioni: GetMap, GetLegendGraphic, GetFeatureInfo,
     GetCapabilities, GetFeature. Qualunque altra operazione va rifiutata;
   - allowlist di parametri per operazione: il proxy non deve poter diventare un
     open relay verso URL arbitrarie;
   - la destinazione remota e determinata esclusivamente da `layer_id` e dal
     registro sorgenti, mai da input del client;
   - nessun header di autenticazione GAIA inoltrato verso l'esterno;
   - timeout per sorgente con default configurabile;
   - cache su filesystem con chiave derivata da layer, operazione e parametri
     normalizzati, TTL per layer da `metadata_json.external.cache_ttl_seconds`;
   - limite di dimensione della cache con pruning;
   - audit degli errori, non delle singole tile.

3. `backend/app/modules/gis/schemas.py`
   - accettare `wms_external` e `wfs_external` come `source_type`;
   - aggiungere `GisExternalLayerConfig` che valida la sezione `external` con i
     campi: `source_key`, `service`, `version`, `remote_layer`, `format`,
     `transparent`, `srid`, `queryable` (`wfs_queryable` | `wms_infoable` |
     `wms_visual_only`), `info_format`, `cache_ttl_seconds`, `license`,
     `attribution`. `license` e `attribution` sono obbligatori.

4. `backend/app/modules/gis/router.py`
   - `GET /gis/external/{layer_id}/wms`;
   - `GET /gis/external/{layer_id}/wfs`;
   - `GET /gis/external/sources`, admin-only.
   Tutti richiedono `can_view` sul layer e rifiutano layer non attivi.

5. `backend/app/core/config.py` e `.env.example`
   - `GIS_EXTERNAL_LAYERS_ENABLED` (default `false`);
   - `GIS_EXTERNAL_CACHE_DIR`;
   - `GIS_EXTERNAL_CACHE_MAX_MB` (default `2048`);
   - `GIS_EXTERNAL_DEFAULT_TIMEOUT_SECONDS` (default `12`);
   - `GIS_EXTERNAL_RAS_VECTOR_URL`;
   - `GIS_EXTERNAL_RAS_RASTER_URL`;
   - `GIS_EXTERNAL_ADE_WMS_URL`.
   Con il flag a `false` i proxy rispondono `503` governato.

6. `backend/app/modules/gis/runtime_health.py`
   - nuova chiave `external_sources`;
   - probe reale `GetCapabilities` con timeout corto e risultato cachato almeno
     5 minuti, per non trasformare l'apertura della pagina in carico verso RAS;
   - il dashboard catalogo deterministico non va modificato.

7. Divieti da applicare nel punto in cui la logica esistente valuta il layer
   target, non con controlli sparsi:
   - un layer esterno non puo essere target di change request (M4);
   - un layer esterno non e esportabile come shapefile (M5);
   - un layer esterno non entra nella policy SQL QGIS come tabella (M6):
     `qgis.mode=not_published`.

Test da scrivere:
- `backend/tests/test_gis_external_sources.py`;
- `backend/tests/test_gis_external_proxy.py`: allowlist operazioni, allowlist
  parametri, cache hit/miss, scadenza TTL, timeout, degradazione, layer non
  attivo, assenza di `can_view`, flag disabilitato, pruning cache;
- estendere `backend/tests/test_gis_platform_api.py` per i nuovi `source_type` e
  per i tre divieti.

Non fare in questo passo:
- non registrare nessun layer esterno nel bootstrap;
- non toccare il frontend;
- non modificare `services.py` oltre al minimo necessario per i tre divieti;
- non modificare `ade_wfs.py` del modulo Catasto.

Al termine aggiorna:
- `docs/GIS_PLATFORM_ARCHITECTURE.md` con una sezione sui layer esterni;
- `docs/GIS_PLATFORM_MILESTONES.md` marcando M21;
- `docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md` con le evidenze dei comandi
  eseguiti.
```

### Criteri Di Accettazione

- `wms_external` e `wfs_external` accettati con validazione della sezione
  `external`, licenza e attribuzione obbligatorie.
- Proxy con allowlist, cache, TTL, timeout e pruning, verificati da test.
- Il proxy non accetta URL dal client: verificato da test dedicato.
- I tre divieti (change request, export, QGIS) verificati da test.
- Flag disabilitato produce `503` governato.
- Coverage `100%` sui file nuovi e modificati.
- `make complexity-ratchet BASE_REF=origin/main` non peggiora.

---

## P2 - M22a Seed Catalogo Territorio

Branch: `feature/gis-territorio-catalog-seed-m22`.
Prerequisito: P0 chiuso, P1 in `main` o nel branch base.

### Prompt

```
Contesto: la fondazione dei layer esterni (M21) e in piedi. Va ora popolato il
catalogo GIS con le sorgenti territoriali censite, senza ancora toccare la
mappa.

Leggi prima:
- `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md` per intero: e la fonte delle
  definizioni layer;
- `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`, sezione "M22";
- `backend/app/modules/gis/bootstrap.py`, per il pattern idempotente di
  `ensure_gis_platform_catalog` e `ensure_catasto_gis_catalog`;
- `backend/app/main.py`, per il punto di registrazione dei bootstrap.

Implementa:

1. `backend/app/modules/gis/territorio_bootstrap.py`
   - `ensure_territorio_gis_catalog`, idempotente;
   - definizioni layer prese esattamente dalle tabelle del catalogo, gruppo per
     gruppo: `bonifica`, `colture`, `pericolosita`, `vincoli`, `idrografia`,
     `amministrativo`, `eventi`, `catasto_ufficiale`, `ortofoto`, `morfologia`;
   - `workspace=territorio`, `domain_module=gis`,
     `official_source=ras_sitr` oppure `agenzia_entrate`;
   - gruppo tematico in `metadata_json.theme`;
   - categoria di interrogabilita in `metadata_json.external.queryable`,
     registrata al seed e mai dedotta a runtime;
   - `metadata_json.export.shapefile=false` e `metadata_json.qgis.mode` a
     `not_published`;
   - permesso default `viewer` read-only, come il seed Catasto;
   - il bootstrap deve rifiutare con errore esplicito una definizione priva di
     `license` o `attribution`;
   - la descrizione di `ras_distretti_irrigui` deve dichiarare che la fonte
     autorevole per il distretto resta GAIA e che la sovrapposizione e
     informativa;
   - la descrizione di `ras_fascia_150m_fiumi` deve riportare che il dato e
     dichiarato indicativo dalla sorgente.

2. Registrazione in `backend/app/main.py` accanto ai bootstrap esistenti,
   condizionata a `GIS_EXTERNAL_LAYERS_ENABLED`.

3. `GET /gis/territorio/layers` in `backend/app/modules/gis/router.py`
   - elenco dei layer esterni visibili all'utente, raggruppati per tema;
   - configurazione gia risolta per il client: URL proxy, opacita default,
     ordine di rendering, categoria di interrogabilita, attribuzione;
   - esiste per non costringere il frontend a ricostruire la configurazione dai
     metadata grezzi.

Test:
- `backend/tests/test_gis_territorio_bootstrap.py`: idempotenza su doppia
  esecuzione, rifiuto senza licenza, rifiuto senza attribuzione, permessi
  default, raggruppamento tematico, metadata di divieto export/QGIS;
- estendere `backend/tests/test_gis_platform_api.py` per
  `GET /gis/territorio/layers`: filtro per permesso, raggruppamento, assenza di
  layer non autorizzati.

Non fare in questo passo:
- non toccare il frontend;
- non aggiungere layer non elencati nel catalogo;
- non implementare interrogazione puntuale.

Al termine aggiorna `docs/GIS_PLATFORM_MILESTONES.md` e
`docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md`.
```

### Criteri Di Accettazione

- Bootstrap idempotente: due esecuzioni consecutive non duplicano layer.
- Ogni layer del seed presente in `/gis/catalogo` con i filtri esistenti.
- Definizione senza licenza rifiutata con errore esplicito.
- `GET /gis/territorio/layers` rispetta i permessi.
- Coverage `100%`, ratchet non peggiorato.

---

## P3 - M22b Pannello Strati E Ortofoto Storiche

Branch: `feature/gis-territorio-layer-panel-m22`.
Prerequisito: P2 completato.

### Prompt

```
Contesto: il catalogo GIS espone ora i layer territoriali esterni via
`GET /gis/territorio/layers` e li serve via proxy
`GET /gis/external/{layer_id}/wms`. Vanno resi consultabili dalla mappa
Catasto.

Leggi prima:
- `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`, sezione "M22";
- `frontend/src/components/catasto/gis/MapContainer.tsx`;
- `frontend/src/components/catasto/gis/map-filters.ts`;
- `frontend/src/app/catasto/gis/page.tsx`;
- `docs/GIS_PLATFORM_ARCHITECTURE.md`, sezione "Semplificazione UX 2026-07 per
  utenti non tecnici": il linguaggio della UI deve restare coerente con quella
  impostazione.

Attenzione: `MapContainer.tsx` e gia a 1552 righe ed e sopra soglia di
complessita. La gestione dei layer esterni va estratta in un hook dedicato, non
aggiunta dentro il file.

Implementa:

1. `frontend/src/components/catasto/gis/use-territorio-layers.ts`
   - hook che carica `GET /gis/territorio/layers`, gestisce stato acceso/spento
     e opacita per layer, e registra/rimuove le sorgenti raster su MapLibre;
   - le sorgenti puntano al proxy GAIA, mai direttamente al servizio remoto;
   - stato di errore per singolo layer, isolato: un layer irraggiungibile non
     deve produrre un errore di pagina.

2. `frontend/src/components/catasto/gis/TerritorioLayerPanel.tsx`
   - pannello strati richiudibile;
   - gruppi tematici con etichette in italiano piano, non con i nomi tecnici dei
     gruppi;
   - per ogni layer: toggle, slider di opacita, legenda via GetLegendGraphic,
     badge "solo consultazione", sorgente in evidenza;
   - avviso sul singolo layer quando la sorgente non risponde.

3. `frontend/src/components/catasto/gis/OrtofotoStoricheSelector.tsx`
   - selettore anno per il gruppo `ortofoto`, usato come basemap alternativa;
   - confronto tra due annate con slider o tendina;
   - reset automatico quando si torna a OSM o satellite.

4. Attribuzione: quando almeno un layer esterno e acceso, l'attribuzione delle
   sorgenti attive deve essere visibile in mappa.

5. Ordine di rendering: i layer esterni stanno sempre sotto particelle,
   distretti, punti di consegna, canali irrigui, DUI e rete. Il dato GAIA resta
   sempre leggibile sopra il contesto.

Regole:
- stato acceso/spento e opacita sono preferenze locali dell'utente, non stato
  condiviso;
- nessuna modifica al comportamento esistente di popup, ricerca, selezioni,
  filtri e strumenti di disegno.

Test:
- `frontend/tests/unit/territorio-layer-panel.test.tsx`: toggle, opacita, stato
  di errore per singolo layer, badge sola consultazione, raggruppamento;
- `frontend/tests/unit/ortofoto-storiche-selector.test.tsx`: selezione anno,
  confronto, reset;
- `frontend/tests/unit/use-territorio-layers.test.ts`: registrazione e rimozione
  sorgenti, isolamento errori.

Non fare in questo passo:
- non implementare interrogazione puntuale;
- non modificare il popup particella esistente;
- non aggiungere layer al seed.

Al termine aggiorna `docs/GIS_PLATFORM_MILESTONES.md` e
`docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md`.
```

### Criteri Di Accettazione

- Pannello strati operativo su `/catasto/gis` con gruppi, toggle, opacita e
  legende.
- Ortofoto storiche selezionabili e confrontabili.
- Attribuzione visibile con layer esterni accesi.
- Layer esterni sempre sotto i layer GAIA.
- Un layer irraggiungibile non rompe la mappa: verificato da test.
- `npm run typecheck`, `npm run test:unit` e `npm run lint` verdi.
- Nessuna regressione su `frontend/tests/unit/gis-tools-workspace.test.tsx` e
  sugli altri test esistenti.

---

## P4 - M23a Interrogazione Puntuale Backend

Branch: `feature/gis-territorio-interrogazione-m23`.
Prerequisito: P3 completato e catalogo esterno in esercizio.

### Prompt

```
Contesto: GAIA deve rispondere alla domanda "cosa insiste su questo punto"
aggregando in un'unica risposta il dato interno GAIA, il dato catastale
ufficiale e i layer territoriali regionali. E la funzione centrale del progetto
territorio.

Leggi prima:
- `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`, sezione "M23";
- `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md`, sezione "Interrogabilita";
- `backend/app/modules/catasto/services/gis_service.py`;
- `backend/app/modules/catasto/routes/gis.py`, in particolare
  `get_particella_popup` e `select_by_geometry`;
- `backend/app/modules/gis/external_proxy.py` e `external_sources.py` da M21;
- `config/martin.toml` per le proprieta dei layer GAIA.

Attenzione: `backend/app/modules/gis/services.py` e a 3441 righe. Il codice
nuovo va in un package dedicato, non li dentro.

Implementa il package `backend/app/modules/gis/interrogazione/`:

1. `models.py` - dataclass della risposta, per livello e per sorgente, con
   stato esplicito per ogni sorgente (`ok`, `empty`, `failed`, `skipped`) e
   messaggio.

2. `local_probes.py` - sonde PostGIS locali:
   - particella da `cat_particelle_current` per `ST_Intersects`;
   - distretto da `cat_distretti`;
   - punto di consegna piu vicino entro raggio, con `ST_DWithin`;
   - tratti di `network.rete_condotte` entro raggio;
   - DUI da `cat_dui_2026_current`;
   - posizione a ruolo e utenze collegate alla particella.

3. `remote_probes.py` - sonde remote:
   - `GetFeature` WFS con filtro spaziale per i layer `wfs_queryable`;
   - `GetFeatureInfo` WMS per i layer `wms_infoable`, con normalizzazione della
     risposta;
   - i layer `wms_visual_only` non vanno mai interrogati: stato `skipped`.

4. `service.py` - orchestrazione:
   - le sonde remote girano in parallelo con timeout individuale;
   - una sonda che fallisce produce `status=failed` con messaggio, mai
     un'eccezione che interrompe la risposta complessiva;
   - il livello `gaia` non e opzionale: se fallisce, la richiesta fallisce;
   - limite massimo di layer remoti interrogabili per richiesta;
   - tempo di risposta per sorgente incluso nel risultato.

5. Endpoint `POST /gis/interroga` in `backend/app/modules/gis/router.py`:
   - corpo: `lon`, `lat`, `srid` opzionale, elenco opzionale di `layer_ids`,
     `radius_m` opzionale;
   - risposta con tre livelli: `gaia`, `catasto_ufficiale`, `territorio`;
   - sempre `200` con stati per sorgente, tranne quando fallisce il livello
     `gaia`.

6. Configurazione in `backend/app/core/config.py` e `.env.example`:
   - `GIS_INTERROGAZIONE_ENABLED` (default `false`);
   - `GIS_INTERROGAZIONE_REMOTE_TIMEOUT_SECONDS` (default `8`);
   - `GIS_INTERROGAZIONE_DEFAULT_RADIUS_M` (default `150`);
   - `GIS_INTERROGAZIONE_MAX_REMOTE_LAYERS` (default `12`).

Test:
- `backend/tests/test_gis_interrogazione_local.py`;
- `backend/tests/test_gis_interrogazione_remote.py` con client HTTP simulato,
  incluse risposte malformate e timeout;
- `backend/tests/test_gis_interrogazione_service.py`: parallelismo,
  degradazione per singola sorgente, fallimento del livello GAIA, limite layer
  remoti, layer `wms_visual_only` saltati, rispetto dei permessi.

Non fare in questo passo:
- non toccare il frontend;
- non modificare `get_particella_popup`: il popup rapido resta com'e;
- non generare PDF.

Al termine aggiorna `docs/GIS_PLATFORM_MILESTONES.md` e
`docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md`.
```

### Criteri Di Accettazione

- `POST /gis/interroga` restituisce i tre livelli in una risposta.
- Ogni sorgente ha stato esplicito e tempo di risposta.
- Con tutte le sorgenti esterne irraggiungibili la risposta resta valida e il
  livello GAIA e completo: verificato da test.
- Layer `wms_visual_only` mai interrogati.
- Permessi rispettati: layer senza `can_view` non compaiono.
- Coverage `100%`, ratchet non peggiorato.

---

## P5 - M23b Pannello Interrogazione Frontend

Branch: `feature/gis-territorio-interrogazione-ui-m23`.
Prerequisito: P4 completato.

### Prompt

```
Contesto: `POST /gis/interroga` restituisce l'intersezione multi-sorgente di un
punto. Va esposta in mappa come pannello istruttorio, affiancando il popup
particella esistente senza sostituirlo.

Leggi prima:
- `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`, sezione "M23";
- `frontend/src/components/catasto/gis/ParticellaGisDialog.tsx`;
- `frontend/src/components/catasto/gis/MapContainer.tsx`;
- `frontend/src/components/catasto/gis/SelectionPanel.tsx`;
- `docs/GIS_PLATFORM_ARCHITECTURE.md`, sezione "Semplificazione UX 2026-07".

Implementa
`frontend/src/components/catasto/gis/InterrogazionePanel.tsx`:

- pannello laterale aperto da un'azione esplicita sul clic in mappa, distinta
  dal popup particella rapido;
- tre sezioni collassabili corrispondenti ai livelli `gaia`,
  `catasto_ufficiale`, `territorio`; il livello GAIA e sempre aperto;
- dentro `territorio`, raggruppamento per tema con le stesse etichette in
  italiano piano usate nel pannello strati;
- stato per sorgente sempre visibile: in caricamento, risultato, nessun
  risultato, non disponibile. Nessuna sezione vuota silenziosa: "nessun
  risultato" e "sorgente non raggiungibile" sono messaggi diversi e vanno
  distinti;
- attribuzione della sorgente su ogni blocco di risultato esterno;
- azione verso la scheda territoriale quando la particella e identificata;
  finche M24 non esiste, l'azione resta disabilitata con etichetta esplicativa.

Regole:
- il popup particella esistente non cambia comportamento;
- il pannello non blocca l'interazione con la mappa mentre carica;
- le sorgenti lente compaiono progressivamente, non si attende la piu lenta per
  mostrare le altre.

Test:
- `frontend/tests/unit/interrogazione-panel.test.tsx`: rendering per ciascuno
  stato di sorgente, sezioni collassabili, distinzione tra risultato vuoto e
  sorgente non disponibile, attribuzione, azione scheda disabilitata.

Non fare in questo passo:
- non implementare la scheda territoriale;
- non modificare il pannello strati M22.

Al termine aggiorna `docs/GIS_PLATFORM_MILESTONES.md` e
`docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md`.
```

### Criteri Di Accettazione

- Clic su mappa apre il pannello con i tre livelli.
- Risultato vuoto e sorgente non disponibile sono visivamente distinti.
- Le sorgenti compaiono progressivamente.
- Popup particella invariato.
- `npm run typecheck`, `npm run test:unit`, `npm run lint` verdi.

---

## P6 - M24 Scheda Territoriale Particella

Branch: `feature/gis-territorio-scheda-m24`.
Prerequisito: P5 completato.

### Prompt

```
Contesto: va prodotta in PDF la sintesi territoriale di una particella, che oggi
richiede l'apertura di piu schermate diverse. E l'analogo del report di
destinazione urbanistica, ma centrato sulla particella e sul perimetro
consortile.

Leggi prima:
- `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`, sezione "M24";
- `backend/app/modules/gis/interrogazione/` da M23;
- `backend/app/modules/gis/artifact_storage.py`;
- `backend/app/modules/gis/exporter.py` e `export_scheduler.py`, per il pattern
  di generazione asincrona, audit e retention;
- `backend/alembic/versions/`, per la convenzione di naming delle migration.

Vincolo sulle dipendenze: usare `playwright` (gia dipendenza, usata dalla
pipeline SISTER) per la resa HTML verso PDF con Chromium, e `pypdf` (gia
dipendenza) per l'assemblaggio. Non aggiungere nuove librerie PDF.

Implementa il package `backend/app/modules/gis/scheda_territoriale/`:

1. `collector.py` - raccolta dati riusando le sonde M23 sul centroide e
   sull'estensione della particella, non solo su un punto.

2. `renderer.py` - template HTML e resa PDF con Chromium.

3. `service.py` - orchestrazione, permessi, audit, stati.

Contenuto della scheda:
- identificativi catastali, superficie reale e grafica, comune, distretto;
- intestatari, posizione a ruolo, utenze e punti di consegna serventi;
- coltura dichiarata in DUI a confronto con uso del suolo e colture regionali;
- vincoli e classi di pericolosita intersecanti, ciascuno con fonte e data del
  dato;
- estratto di mappa su ortofoto con scala e riferimenti;
- attribuzione di tutte le sorgenti usate;
- disclaimer in chiaro nella prima pagina, non in nota:

  "Documento prodotto da GAIA a fini istruttori interni. Non ha valore
  certificativo. I dati di fonte esterna sono riportati alla data di
  consultazione indicata e restano di titolarita dell'ente che li pubblica."

Persistenza: migration `20260901_0900_gis_schede_territoriali.py` con tabella
`gis_schede_territoriali`. Campi: id, riferimento particella, richiedente,
stato, path artifact, checksum, snapshot JSON delle sorgenti interrogate con
esito, timestamp. Lo snapshot e obbligatorio: senza non si puo ricostruire cosa
fosse disponibile al momento della generazione.

API:
- `POST /gis/scheda-territoriale` - avvia la generazione, restituisce l'id;
- `GET /gis/scheda-territoriale/{scheda_id}` - stato e metadata;
- `GET /gis/scheda-territoriale/{scheda_id}/pdf` - download.

Generazione asincrona: resa Chromium piu sonde remote non stanno in una
richiesta sincrona ragionevole.

Regole:
- richiede `can_view` sui layer coinvolti; i layer non autorizzati sono esclusi
  dalla scheda e l'esclusione va dichiarata nel documento, non taciuta;
- audit `scheda_territoriale.requested`, `.completed`, `.failed`;
- retention configurabile, sullo stesso pattern della retention export M10.

Frontend: abilitare l'azione "Genera scheda territoriale" nel pannello
interrogazione, con stato di avanzamento e download al termine.

Test:
- `backend/tests/test_gis_scheda_collector.py`;
- `backend/tests/test_gis_scheda_renderer.py` con Chromium simulato;
- `backend/tests/test_gis_scheda_service.py`: permessi, esclusione dichiarata
  dei layer non autorizzati, audit, stati, retention, snapshot sorgenti;
- `frontend/tests/unit/scheda-territoriale.test.tsx`.

Al termine aggiorna `docs/GIS_PLATFORM_MILESTONES.md`,
`docs/GIS_PLATFORM_ARCHITECTURE.md` e
`docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md`.
```

### Criteri Di Accettazione

- Scheda generabile dal pannello interrogazione.
- PDF con disclaimer in prima pagina, attribuzione e snapshot sorgenti.
- Layer non autorizzati esclusi e l'esclusione dichiarata nel documento.
- Audit completo per richiesta, completamento e fallimento.
- Migration applicabile e reversibile.
- Coverage `100%`, ratchet non peggiorato.

---

## P7 - M25 Strumenti Di Campo E Progetto QGIS

Branch: `feature/gis-territorio-strumenti-m25`.
Prerequisito: nessuno oltre M22. Non bloccante.

### Prompt

```
Contesto: rifinitura degli strumenti di mappa e propagazione dei layer
territoriali al progetto QGIS gia generato da M16.

Leggi prima:
- `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`, sezione "M25";
- `frontend/src/components/catasto/gis/DrawingTools.tsx`;
- `frontend/src/components/catasto/gis/OrtofotoStoricheSelector.tsx` da M22;
- il generatore di progetto QGIS in `backend/app/modules/gis/services.py`
  (`GET /gis/qgis/project`);
- `docs/GIS_QGIS_DESKTOP_RUNBOOK.md`.

Implementa:

1. Misura di distanze e aree su mappa, come estensione di `DrawingTools.tsx`.
   Le misure devono essere coerenti con la proiezione: calcolo geodetico, non
   euclideo sulle coordinate proiettate.

2. Confronto diacronico ortofoto con slider per annata, estendendo
   `OrtofotoStoricheSelector.tsx`.

3. Layout di stampa con scala, legenda, intestazione consortile e attribuzione
   delle sorgenti attive.

4. Inclusione dei layer territoriali visibili nel progetto QGIS generato,
   come sorgenti WMS che puntano al proxy GAIA e non al servizio remoto. Il
   progetto resta filtrato sui layer visibili all'utente richiedente.

Test:
- unit frontend per misure, confronto e layout di stampa;
- estensione dei test esistenti sul generatore di progetto QGIS per verificare
  la presenza dei layer territoriali e il filtro sui permessi.

Al termine aggiorna `docs/GIS_QGIS_DESKTOP_RUNBOOK.md`,
`docs/GIS_PLATFORM_MILESTONES.md` e
`docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md`.
```

### Criteri Di Accettazione

- Misure geodetiche corrette, verificate su un caso noto.
- Confronto ortofoto operativo.
- Layout di stampa con attribuzione.
- Progetto QGIS include i layer territoriali visibili, puntando al proxy GAIA.

---

## Riepilogo Ordine

| prompt | milestone | branch | prerequisito |
| --- | --- | --- | --- |
| P0 | - | nessuno | nessuno |
| P1 | M21 | `feature/gis-territorio-external-layers-m21` | P0 |
| P2 | M22a | `feature/gis-territorio-catalog-seed-m22` | P0, P1 |
| P3 | M22b | `feature/gis-territorio-layer-panel-m22` | P2 |
| P4 | M23a | `feature/gis-territorio-interrogazione-m23` | P3 |
| P5 | M23b | `feature/gis-territorio-interrogazione-ui-m23` | P4 |
| P6 | M24 | `feature/gis-territorio-scheda-m24` | P5 |
| P7 | M25 | `feature/gis-territorio-strumenti-m25` | P3 |

P1 e P2 sono pensati per essere eseguiti in sequenza ravvicinata: M21 senza M22
non produce nulla di osservabile.

P7 e indipendente da P4-P6 e puo slittare senza bloccare il resto.
