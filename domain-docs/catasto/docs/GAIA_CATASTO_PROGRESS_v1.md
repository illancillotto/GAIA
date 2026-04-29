# GAIA — Modulo Catasto
## Progress Tracker v1

---

## Stato generale

| Fase | Descrizione | Status | Note |
|---|---|---|---|
| **1** | Foundation: DB, import, API, frontend tabellare | 🟡 In corso (core pronto) | Backend+frontend Fase 1 implementati; restano ottimizzazioni/performance e alcune rifiniture UX |
| **2** | GIS Map UI: MapLibre + Martin | 🟢 Completato | Estensione GIS implementata su modulo `catasto` esistente |
| **3** | Sister integration per intestatari | 🔴 Non iniziato | Dipende da Fase 1 |
| **4** | Sentinel-2 NDVI + classificazione | 🔴 Non iniziato | Dipende da Fase 2 |
| **5** | Wizard anomalie completo + segnalazioni | 🔴 Non iniziato | Dipende da Fase 1, 4 |

Legend: 🔴 Non iniziato · 🟡 In corso · 🟢 Completato · ⚫ Bloccato

---

## Fase 1 — Foundation

### Infrastruttura e DB

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 1.1 | Alembic migration PostGIS + tutte le tabelle | 🟢 | `backend/alembic/versions/20260420_0051_catasto_phase1_postgis_and_tables.py` | Include estensioni PostGIS + tabelle `cat_*` + indici |
| 1.2 | Seed schemi contributo 0648 e 0985 | 🟢 | nella migration | Seed in `cat_schemi_contributo` |
| 1.3 | Aggiungere `geoalchemy2` a requirements.txt | 🟢 | `backend/requirements.txt` | |
| 1.4 | Aggiungere `codicefiscale` a requirements.txt | 🟢 | `backend/requirements.txt` | |

### Backend — Modelli

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 2.1 | Modello `CatParticella` | 🟢 | `backend/app/models/catasto_phase1.py` | ORM Fase 1 consolidato in `app/models/catasto_phase1.py` |
| 2.2 | Modello `CatDistretto` | 🟢 | `backend/app/models/catasto_phase1.py` | |
| 2.3 | Modello `CatImportBatch` | 🟢 | `backend/app/models/catasto_phase1.py` | |
| 2.4 | Modello `CatUtenzeIrrigua` | 🟢 | `backend/app/models/catasto_phase1.py` | |
| 2.5 | Modello `CatAnomalia` | 🟢 | `backend/app/models/catasto_phase1.py` | |
| 2.6 | Modelli rimanenti (distretto_coeff, schemi, aliquote, intestatari) | 🟢 | `backend/app/models/catasto_phase1.py` | |
| 2.7 | Selezioni GIS salvate | 🟢 | `backend/app/models/catasto_phase1.py` + `backend/alembic/versions/20260429_0069_add_cat_gis_saved_selections.py` | Persistenza per utente di selezioni importate da Excel con colore e riferimenti particella |

### Backend — Services

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 3.1 | `validate_codice_fiscale()` | 🟢 | `backend/app/modules/catasto/services/validation.py` | Include checksum CF 16 e PIVA 11; usa `codicefiscale` se installato |
| 3.2 | Comuni ISTAT CSV + `validate_comune()` | 🟢 | `backend/app/modules/catasto/data/comuni_istat.csv` + `backend/app/modules/catasto/services/validation.py` | |
| 3.3 | `validate_superficie()`, `validate_imponibile()`, `validate_importi()` | 🟢 | `backend/app/modules/catasto/services/validation.py` | |
| 3.4 | Unit test validazione | 🟡 | `backend/tests/test_catasto_phase1.py` | Test base presenti; suite specifica validazione dedicata ancora da separare se utile |
| 4.1 | `import_capacitas()` — mapping colonne + normalizzazioni | 🟢 | `backend/app/modules/catasto/services/import_capacitas.py` | |
| 4.2 | `import_capacitas()` — pipeline validazione VAL-01..08 | 🟢 | `backend/app/modules/catasto/services/import_capacitas.py` | |
| 4.3 | `import_capacitas()` — bulk insert + report_json | 🟡 | `backend/app/modules/catasto/services/import_capacitas.py` | Implementato ma non ottimizzato per 90k (manca COPY/bulk spinto) |
| 4.4 | `import_capacitas()` — idempotenza + force | 🟢 | `backend/app/modules/catasto/services/import_capacitas.py` | |
| 4.5 | `import_capacitas()` — upsert coefficienti e aliquote | 🟡 | `backend/app/modules/catasto/services/import_capacitas.py` | Da completare/allineare a execution plan (upsert automatici) |
| 5.1 | `finalize_shapefile_import()` — upsert SCD Type 2 | 🟢 | `backend/app/modules/catasto/services/import_shapefile.py` | SCD2 + history; update finale del batch differito a fine transazione per evitare lock tra finalize e progress logger su `cat_import_batches`; fast path DB vuoto ora materializza dedup, inserisce a chunk con step progressivi e alza il parallelismo SQL di sessione in modo aggressivo (`work_mem`, `temp_buffers`, `max_parallel_workers_per_gather`, costi planner, I/O concurrency) |
| 5.2 | `finalize_shapefile_import()` — deriva distretti via ST_Union | 🟢 | `backend/app/modules/catasto/services/import_shapefile.py` | Upsert `cat_distretti` |
| 5.3 | Script bash `import_shapefile_catasto.sh` | 🟢 | `scripts/import_shapefile_catasto.sh` | `ogr2ogr` → staging + finalize API; backend upload ZIP ora usa `ogr2ogr` anche lato servizio con `PG_USE_COPY=YES` e droppa `cat_particelle_staging` a fine finalize/errore |

### Backend — Routes

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 6.1 | Routes distretti (lista, dettaglio, kpi, geojson) | 🟢 | `backend/app/modules/catasto/routes/distretti.py` | GeoJSON senza hard-deps `geoalchemy2` |
| 6.2 | Routes particelle (lista, dettaglio, utenze, anomalie, geojson) | 🟢 | `backend/app/modules/catasto/routes/particelle.py` | `utenze` e `anomalie` per particella incluse |
| 6.3 | Routes import (upload, finalize, status, report, history) | 🟢 | `backend/app/modules/catasto/routes/import_routes.py` | Include finalize shapefile |
| 6.4 | Routes anomalie (lista, patch) | 🟢 | `backend/app/modules/catasto/routes/anomalie.py` | Include `PATCH /catasto/anomalie/{id}` |
| 6.5 | Registrazione router in main/catasto module | 🟢 | `backend/app/modules/catasto/routes/__init__.py` + `backend/app/modules/catasto/router.py` | Router incluso in API |

### Frontend

| # | Task | Status | File | Note |
|---|---|---|---|---|
| F1.1 | Tipi TypeScript `catasto.ts` | 🟢 | `frontend/src/types/catasto.ts` | |
| F1.2 | Client API `catastoApi` | 🟢 | `frontend/src/lib/api/catasto.ts` | Include `PATCH` anomalie + endpoints particella |
| F2.1 | Componente `AnomaliaStatusBadge` | 🟢 | `frontend/src/components/catasto/AnomaliaStatusBadge.tsx` | |
| F2.2 | Componente `CfBadge` | 🟢 | `frontend/src/components/catasto/CfBadge.tsx` | |
| F2.3 | Componente `KpiCard` | 🟢 | `frontend/src/components/catasto/KpiCard.tsx` | |
| F2.4 | Componente `ImportStatusBadge` | 🟢 | `frontend/src/components/catasto/ImportStatusBadge.tsx` | |
| F3 | Dashboard `/catasto` | 🟢 | `frontend/src/app/catasto/page.tsx` | |
| F4 | Wizard Import `/catasto/import` (3 step) | 🟢 | `frontend/src/app/catasto/import/page.tsx` | |
| F5 | Lista Distretti `/catasto/distretti` | 🟢 | `frontend/src/app/catasto/distretti/page.tsx` | |
| F6 | Dettaglio Distretto `/catasto/distretti/[id]` | 🟢 | `frontend/src/app/catasto/distretti/[id]/page.tsx` | Tab anomalie distretto collegata |
| F7 | Scheda Particella `/catasto/particelle/[id]` | 🟢 | `frontend/src/app/catasto/particelle/[id]/page.tsx` | Sezioni utenze+anomalie collegate |
| F8 | Lista Anomalie `/catasto/anomalie` | 🟢 | `frontend/src/app/catasto/anomalie/page.tsx` | Azioni rapide via `PATCH` |
| F9 | Layout + navigazione catasto | 🟢 | `frontend/src/app/catasto/layout.tsx` + sidebar | |
| F10 | Elaborazioni massive `/catasto/elaborazioni-massive` | 🟢 | `frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx` | Storico locale ultime 5 operazioni; `MULTIPLE_MATCHES` esporta tutte le particelle candidate con `match_rank` |

---

## Fase 2 — GIS Map UI

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 2.1 | Container Martin in docker-compose | 🟢 | `docker-compose.yml` | Servizio interno, non esposto su porta host |
| 2.2 | Config Martin | 🟢 | `config/martin.toml` | Config YAML compatibile con Martin v1.7, montata come `/config.toml` |
| 2.3 | Proxy nginx `/tiles/` | 🟢 | `nginx/nginx.conf` | `/tiles/catalog` e tile distretti verificati via nginx |
| 2.4 | View particelle correnti per Martin | 🟢 | `backend/alembic/versions/20260427_0066_catasto_gis_view.py` | `cat_particelle_current` con `geometry` e `ha_anomalie` |
| 2.5 | Endpoint GIS backend | 🟢 | `backend/app/modules/catasto/routes/gis.py` + `services/gis_service.py` | Select spaziale, export CSV/GeoJSON, popup particella, resolve riferimenti Excel e CRUD selezioni salvate |
| 2.6 | Dipendenze MapLibre/Draw | 🟢 | `frontend/package.json` | `maplibre-gl` già presente; aggiunto `maplibre-gl-draw` |
| 2.7 | Pagina GIS `/catasto/gis` | 🟢 | `frontend/src/app/catasto/gis/page.tsx` | Layout GIS + pannello analisi; import Excel con riepilogo, colore layer, salvataggio/caricamento selezioni e mappa più alta |
| 2.8 | Layer distretti e particelle MVT | 🟢 | `frontend/src/components/catasto/gis/MapContainer.tsx` | Distretti zoom 7+, particelle correnti zoom 13+ |
| 2.9 | Popup particella con link scheda | 🟢 | `frontend/src/components/catasto/gis/MapContainer.tsx` | Fetch dati leggeri da `/catasto/gis/particella/{id}/popup` |
| 2.10 | Overlay import Excel persistente | 🟢 | `frontend/src/components/catasto/gis/MapContainer.tsx` + `frontend/src/lib/api/catasto.ts` | Layer GeoJSON importato applicato quando la source MapLibre è pronta, `fitBounds` automatico e colore configurabile |

---

## Fase 3 — Sister Integration

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 3.1 | Endpoint batch visure per anomalie CF | 🔴 | | |
| 3.2 | Aggiornamento `cat_intestatari` da risultati Sister | 🔴 | | |
| 3.3 | UI: pulsante "Verifica Sister" in scheda particella | 🔴 | | |

---

## Fase 4 — Sentinel-2

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 4.1 | Account Copernicus Data Space | 🔴 | — | Azione manuale |
| 4.2 | `pip install openeo` + env variables | 🔴 | | |
| 4.3 | `sentinel_service.py` — auth + query | 🔴 | | |
| 4.4 | Job NDVI per distretto | 🔴 | | |
| 4.5 | Classificazione `irrigata_probabile` | 🔴 | | |
| 4.6 | Rilevamento presunti non paganti | 🔴 | | |
| 4.7 | Overlay NDVI su mappa | 🔴 | | |

---

## Fase 5 — Wizard + Segnalazioni

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 5.1 | Wizard anomalie 6 step completo | 🔴 | | |
| 5.2 | Integrazione segnalazioni con `operazioni` | 🔴 | | |

---

## Domande aperte

| ID | Domanda | Status | Risposta |
|---|---|---|---|
| OQ-01 | CCO corrisponde al wc_id White Company? | ✅ Risolto | No. Link tramite `codice_fiscale` / P.IVA |
| OQ-02 | Codici schema fissi? | ✅ Risolto | Sì: 0648 = contributo irriguo (aliquota fissa); 0985 = Quote Ordinarie (aliquota variabile da contatori, dato autoritativo Capacitas) |
| OQ-03 | EPSG shapefile? | ✅ Risolto | EPSG:3003 Monte Mario / Italy zone 1. `ogr2ogr`: `-s_srs EPSG:3003 -t_srs EPSG:4326` |
| OQ-04 | PARTIC alfanumerico? | ✅ Risolto | Sì (STRADA058 ecc.). Schema già corretto con `VARCHAR(20)` |
| OQ-05 | Anni precedenti disponibili? | ✅ Risolto | Solo 2025. Import storico non necessario in Fase 1 |

---

## Note tecniche

- PostGIS da abilitare prima di eseguire la migration Fase 1
- Lo shapefile deve essere copiato in un path accessibile dal server GAIA prima dello script `import_shapefile_catasto.sh`
- Martin si avvia automaticamente con `docker compose up` dopo aggiunta al compose
- Workspace `Elaborazioni > Capacitas`: la UI e organizzata in sezioni operative (`sync progressiva particelle`, `storico anagrafico`, `Terreni batch`) e non espone piu la ricerca anagrafica puntuale, perche i dati Capacitas vengono sincronizzati su GAIA.
- Workspace `Elaborazioni > Capacitas > Terreni`: resta solo il flusso massivo da file; la preview del file e collassata di default e mostra un campione limitato, mentre il job usa comunque tutte le righe importate; i job espongono `double_speed`, `parallel_workers` e `throttle_ms`; il backend usa i parametri sia nel job batch sia nel rerun, con parallelo fino a 2 sessioni Capacitas e pausa applicata tra righe/item Terreni
- Job Capacitas monitorabili da frontend (`Terreni` e `sync progressiva particelle`): avvio runtime con `asyncio.create_task(...)` tracciato lato backend, stato persistito su DB e recovery automatico degli orfani/stale job; la scadenza della sessione GAIA interrompe il polling UI ma non deve essere confusa con l'arresto del job backend
- `sync progressiva particelle`: al bootstrap backend i job compatibili in stato `pending/processing` vengono riconciliati in `queued_resume` e rilanciati automaticamente; il resume e guidato dal dominio (`capacitas_last_sync_at/status`) e non dal vecchio thread runtime interrotto
- `Terreni` batch: supporta `auto_resume` esplicito per i job che devono essere ripianificati automaticamente dopo restart backend; i batch manuali senza flag restano recuperabili solo via monitor/rerun esplicito
- `Storico anagrafica Capacitas`: ora usa un modello job persistente dedicato con monitor frontend, progress report incrementale, cleanup stale e auto-resume dopo restart backend
- `Catasto > Particelle`: la sync singola Capacitas è disponibile direttamente nella dialog/lista particelle e nella scheda dettaglio, con label di ultimo aggiornamento (`capacitas_last_sync_at/status/error`) e route dedicata `POST /catasto/particelle/{id}/capacitas-sync`
- `Catasto > GIS`: l'import Excel delle particelle usa `POST /catasto/gis/resolve-refs` per generare il layer GeoJSON temporaneo; le selezioni possono essere salvate lato backend con nome/colore, riaperte dalle sessioni successive e rigenerate dalle geometrie correnti delle particelle.
- `codicefiscale` Python su PyPI: https://pypi.org/project/codicefiscale/
- Copernicus Data Space gratuito per enti EU: https://dataspace.copernicus.eu
