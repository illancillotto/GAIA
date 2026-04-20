# GAIA — Modulo Catasto
## Execution Plan v1

---

## Fasi e priorità

| Fase | Scope | Stima | Prerequisiti |
|---|---|---|---|
| **1** | Foundation: DB, import, tabelle, API base, frontend tabellare | 3-4 settimane | PostGIS abilitato |
| **2** | GIS Map UI: MapLibre + Martin + mappa distretti interattiva | 2-3 settimane | Fase 1 completa, shapefile importato |
| **3** | Sister integration per intestatari anomali | 1-2 settimane | Fase 1, modulo elaborazioni operativo |
| **4** | Sentinel-2: acquisizione immagini, NDVI, classificazione | 3-4 settimane | Fase 2, account Copernicus |
| **5** | Wizard anomalie completo + segnalazioni operatori | 1-2 settimane | Fase 1, Fase 4 |

---

## Fase 1 — Foundation

### Step 1.1 — Infrastruttura DB
**File**: Alembic migration `xxxx_catasto_postgis_and_tables.py`

Operazioni:
- `CREATE EXTENSION IF NOT EXISTS postgis`
- `CREATE EXTENSION IF NOT EXISTS postgis_topology`
- Crea tutte le tabelle: `cat_particelle`, `cat_particelle_history`, `cat_distretti`,
  `cat_distretto_coefficienti`, `cat_schemi_contributo`, `cat_aliquote`,
  `cat_import_batches`, `cat_utenze_irrigue`, `cat_intestatari`, `cat_anomalie`
- Crea tutti gli indici (inclusi GIST spaziali)
- Seed dati: inserisce schemi 0648 e 0985 in `cat_schemi_contributo`

**Acceptance**:
- `alembic upgrade head` completa senza errori
- `SELECT PostGIS_version()` ritorna versione
- Tutte le tabelle presenti nel DB

---

### Step 1.2 — Script import shapefile
**File**: `scripts/import_shapefile_catasto.sh`
**File**: `backend/app/modules/catasto/services/import_shapefile.py`

Operazioni:
- Script bash: `ogr2ogr` → `cat_particelle_staging` (tabella temporanea)
- Service Python: upsert `cat_particelle_staging` → `cat_particelle` con:
  - Normalizzazione coordinate → EPSG:4326 se necessario
  - Mapping colonne shapefile → schema `cat_particelle`
  - SCD Type 2: record esistenti con `valid_to = CURRENT_DATE`, nuovi record con `is_current = TRUE`
  - Derivazione `cat_distretti` per aggregazione su `NUM_DIST` (ST_Union per distretto)
- Endpoint admin: `POST /catasto/import/shapefile/finalize`

**Acceptance**:
- Import shapefile 500MB completa in < 10 minuti
- `SELECT COUNT(*) FROM cat_particelle` ≈ 288k
- Geometrie valide: `SELECT COUNT(*) FROM cat_particelle WHERE NOT ST_IsValid(geometry)` = 0
- `cat_distretti` popolata con geometrie distretto

---

### Step 1.3 — Service validazione CF e comuni
**File**: `backend/app/modules/catasto/services/validation.py`
**File**: `backend/app/modules/catasto/data/comuni_istat.csv`

Logica:
- `validate_codice_fiscale(cf_raw) → (cf_normalized, is_valid, tipo, error_code)`
  - Normalizza a MAIUSCOLO
  - PF (16 car): usa `codicefiscale` lib per checksum
  - PG (11 cifre): check digit mod 11
  - Resto: FORMATO_SCONOSCIUTO
- `validate_comune(cod_istat, nome) → (is_valid, comune_ufficiale)`
  - CSV ISTAT caricato in memoria all'avvio
  - Match su `cod_istat` → ritorna nome ufficiale
- `validate_superficie(sup_irr, sup_cata) → (ok, delta_pct)`
- `validate_imponibile(imponibile, sup_irr, ind_sf) → (ok, delta)`
- `validate_importi(importo, imponibile, aliquota) → (ok, delta)`

**Acceptance**:
- Unit test: CF `FNDGPP63E11B354D` → valid PF
- Unit test: CF `Dnifse64c01l122y` → normalized `DNIFSE64C01L122Y`, valid PF
- Unit test: CF `00588230953` → valid PG
- Unit test: CF `XXXYYY` → FORMATO_SCONOSCIUTO
- Comuni: cod_istat `165` → `ARBOREA` found

---

### Step 1.4 — Service import Capacitas
**File**: `backend/app/modules/catasto/services/import_capacitas.py`

Logica:
1. Leggi file Excel con `pandas`, sheet `Ruoli {ANNO}`
2. Calcola SHA-256 del file → controlla idempotenza su `cat_import_batches`
3. Crea record `cat_import_batches` con status `processing`
4. Per ogni riga:
   a. Mappa colonne → dict interno
   b. Normalizza CF (MAIUSCOLO)
   c. Esegui tutti i check VAL-01..08
   d. Join lookup verso `cat_particelle` su `(cod_comune_istat, foglio, particella, subalterno)`
   e. Popola flag `anomalia_*`
   f. Crea record `cat_utenze_irrigue`
   g. Per ogni anomalia trovata: crea record `cat_anomalie`
5. Aggiorna `cat_import_batches` con contatori e `report_json`
6. Upsert `cat_schemi_contributo` + `cat_aliquote` se aliquote nuove rilevate
7. Upsert `cat_distretto_coefficienti` per anno corrente se `ind_spese_fisse` nuovi

**Performance**: Usare `bulk_save_objects` o `COPY` per insert massivo.

**Acceptance**:
- Import file esempio 24 righe completa < 2s
- Import 90k righe completa < 60s
- Tutte le anomalie conosciute rilevate (CF mixed case → normalized, validato)
- Re-import stesso file → errore idempotenza
- Re-import con `force=true` → batch precedente marcato `replaced`

---

### Step 1.5 — Routes API backend Fase 1
**File**: `backend/app/modules/catasto/routes/`

Endpoints da implementare per Fase 1:
```
GET  /catasto/distretti                    Lista + KPI base
GET  /catasto/distretti/{id}               Dettaglio
GET  /catasto/distretti/{id}/kpi           KPI per anno (query param)
GET  /catasto/particelle                   Lista paginata, filtri: distretto/anno/anomalie/cf/comune
GET  /catasto/particelle/{id}              Dettaglio
GET  /catasto/particelle/{id}/utenze       Ruoli per anno
GET  /catasto/particelle/{id}/anomalie     Anomalie
POST /catasto/import/capacitas             Upload multipart (background task)
GET  /catasto/import/{id}/status           Status + progress
GET  /catasto/import/{id}/report           Report anomalie completo (paginato)
GET  /catasto/import/history               Lista batch
GET  /catasto/anomalie                     Lista filtrata
PATCH /catasto/anomalie/{id}               Update
GET  /catasto/schemi                       Lista schemi contributo
```

**Acceptance**:
- Tutti gli endpoint restituiscono 200 con dati coerenti
- Paginazione funzionante (default 50, max 200)
- Filtri applicati correttamente
- Auth: tutti richiedono JWT valido, `POST import` richiede ruolo `admin`

---

### Step 1.6 — Frontend Fase 1: Dashboard + Import
**File**: `frontend/src/app/catasto/`

Pagine da implementare:

**`/catasto`** — Dashboard:
- KPI strip: totale particelle, distretti attivi, anomalie aperte, ultimo import
- Cards distretti con KPI essenziali (n. particelle, importo totale, n. anomalie)
- Accesso rapido: bottone Import + link Anomalie

**`/catasto/import`** — Wizard import Capacitas (3 step):
- Step 1: Upload file drag&drop, selezione anno campagna, opzione `force`
- Step 2: Progress bar con log in tempo reale (polling ogni 2s su `/status`)
- Step 3: Report anomalie con tabella filtrable per tipo, export XLSX

**`/catasto/distretti`** — Lista distretti:
- Tabella con colonne: N. distretto, Nome, N. particelle, Sup. irrigabile, Importo totale, N. anomalie
- Filtro anno campagna
- Click → `/catasto/distretti/{id}`

**`/catasto/distretti/[id]`** — Dettaglio distretto:
- Header con nome e KPI
- Tabs: Particelle | Anomalie | Storico import
- Tab Particelle: tabella con filtri inline (CF, anomalie, subalterno)

**`/catasto/particelle`** — Lista particelle:
- Tabella con filtri: comune, foglio, distretto, anno, ha_anomalie
- Highlight righe con anomalie

**`/catasto/particelle/[id]`** — Scheda particella:
- Dati catastali (foglio, particella, comune, superficie)
- Sezione proprietario con CF evidenziato (verde/rosso per validità)
- Sezione ruoli tributo per anno (tabella)
- Sezione anomalie (lista con status e azioni)
- Note libere

**`/catasto/anomalie`** — Gestione anomalie:
- Tabella con filtri: tipo, severità, distretto, anno, status, assegnato a
- Azioni bulk: assegna, chiudi, ignora
- Click → modal dettaglio con note

**Acceptance**:
- Tutte le pagine renderizzano senza errori
- Import wizard funziona end-to-end con file test
- Tabelle paginano correttamente
- Anomalie evidenziate con colori coerenti (error=rosso, warning=giallo, info=blu)

---

## Fase 2 — GIS Map UI

### Step 2.1 — Container Martin + nginx
- Aggiungi servizio `martin` a `docker-compose.yml`
- Crea `config/martin.toml`
- Aggiungi proxy in `nginx/nginx.conf` per `/tiles/`
- Test: `curl /tiles/cat_distretti/10/500/400` → risposta MVT

### Step 2.2 — Endpoints GeoJSON
```
GET /catasto/distretti/{id}/geojson
GET /catasto/particelle/{id}/geojson
GET /catasto/distretti/{id}/particelle/geojson   # tutte le particelle del distretto
```

### Step 2.3 — Pagina mappa
**`/catasto/mappa`**:
- MapLibre GL JS + npm package `maplibre-gl`
- Basemap: raster OpenStreetMap
- Layer distretti: MVT da Martin, colorati per status anomalie
- Panel laterale: click distretto → KPI + lista anomalie
- Layer particelle: caricato on-demand per distretto selezionato (GeoJSON)
- Click particella → popup con dati essenziali + link scheda
- Controlli: toggle layer FD, filtro anno, legenda

---

## Fase 3 — Sister integration

### Step 3.1 — Batch visure per anomalie CF
- Endpoint: `POST /catasto/anomalie/batch-visure-sister`
- Seleziona anomalie tipo `cf_invalido` o particelle non in ruolo
- Lancia job `elaborazioni` per visura soggetto PF/PG
- Aggiorna `cat_intestatari` con risultato

### Step 3.2 — UI: pulsante "Verifica Sister" da scheda particella e wizard anomalie

---

## Fase 4 — Sentinel-2

### Step 4.1 — openeo client setup
- `pip install openeo`
- Credenziali Copernicus Data Space in env: `COPERNICUS_CLIENT_ID`, `COPERNICUS_CLIENT_SECRET`
- Service `sentinel_service.py`: autenticazione, query per area + periodo

### Step 4.2 — Job NDVI per distretto
- Input: `distretto_id`, `data_inizio`, `data_fine` (default: 1 Maggio - 30 Settembre anno corrente)
- Per ogni particella del distretto: calcola NDVI medio tramite spatial mask
- Salva risultati in `cat_sentinel_analisi`
- Classificazione: `NDVI > 0.4` in luglio-agosto → `irrigata_probabile`

### Step 4.3 — Rilevamento presunti non paganti
- Particelle con `classe = irrigata_probabile` e NON presenti in `cat_utenze_irrigue` per anno corrente
- Crea anomalia `presunto_non_pagante` con confidence e NDVI come `dati_json`
- Particelle FD con `classe = irrigata_probabile` → anomalia `fd_irrigante_da_verificare` (severità `warning`)

### Step 4.4 — UI Sentinel
- Layer satellite su mappa (opzionale, WMS Sentinel Hub se disponibile)
- Overlay NDVI per particella (gradiente verde)
- Badge "Irrigazione rilevata" su card particella
- Filtro mappa: mostra solo `irrigata_probabile`

---

## Fase 5 — Wizard completo e segnalazioni

### Step 5.1 — Wizard revisione anomalie completo
- Implementa tutti i 6 step descritti in RF-06 del PRD
- Integrazione con Sentinel (step 5) se Fase 4 completata

### Step 5.2 — Segnalazioni operatori
- Endpoint `POST /catasto/anomalie/{id}/segnalazione` → crea segnalazione in `operazioni`
- Scheda particella mostra segnalazioni aperte con status

---

## Dipendenze esterne da preparare

| Dipendenza | Azione richiesta | Fase |
|---|---|---|
| PostGIS | Abilitare su DB GAIA esistente | Prima di Fase 1 |
| `codicefiscale` Python | `pip install codicefiscale` + `requirements.txt` | Fase 1 |
| Shapefile dal NAS | Copia shapefile in path accessibile al server GAIA | Fase 1 |
| Martin container | Aggiungere a docker-compose | Fase 2 |
| `maplibre-gl` npm | `npm install maplibre-gl` nel frontend | Fase 2 |
| Account Copernicus | Registrazione su dataspace.copernicus.eu | Fase 4 |
| `openeo` Python | `pip install openeo` | Fase 4 |
