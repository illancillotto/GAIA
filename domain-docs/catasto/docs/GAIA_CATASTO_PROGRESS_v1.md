# GAIA — Modulo Catasto
## Progress Tracker v1

---

## Stato generale

| Fase | Descrizione | Status | Note |
|---|---|---|---|
| **1** | Foundation: DB, import, API, frontend tabellare | 🔴 Non iniziato | |
| **2** | GIS Map UI: MapLibre + Martin | 🔴 Non iniziato | Dipende da Fase 1 |
| **3** | Sister integration per intestatari | 🔴 Non iniziato | Dipende da Fase 1 |
| **4** | Sentinel-2 NDVI + classificazione | 🔴 Non iniziato | Dipende da Fase 2 |
| **5** | Wizard anomalie completo + segnalazioni | 🔴 Non iniziato | Dipende da Fase 1, 4 |

Legend: 🔴 Non iniziato · 🟡 In corso · 🟢 Completato · ⚫ Bloccato

---

## Fase 1 — Foundation

### Infrastruttura e DB

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 1.1 | Alembic migration PostGIS + tutte le tabelle | 🔴 | `alembic/versions/xxxx_catasto_postgis_tables.py` | |
| 1.2 | Seed schemi contributo 0648 e 0985 | 🔴 | nella migration | |
| 1.3 | Aggiungere `geoalchemy2` a requirements.txt | 🔴 | `backend/requirements.txt` | |
| 1.4 | Aggiungere `codicefiscale` a requirements.txt | 🔴 | `backend/requirements.txt` | |

### Backend — Modelli

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 2.1 | Modello `CatParticella` | 🔴 | `modules/catasto/models/registry.py` | |
| 2.2 | Modello `CatDistretto` | 🔴 | `modules/catasto/models/registry.py` | |
| 2.3 | Modello `CatImportBatch` | 🔴 | `modules/catasto/models/registry.py` | |
| 2.4 | Modello `CatUtenzeIrrigua` | 🔴 | `modules/catasto/models/registry.py` | |
| 2.5 | Modello `CatAnomalia` | 🔴 | `modules/catasto/models/registry.py` | |
| 2.6 | Modelli rimanenti (distretto_coeff, schemi, aliquote, intestatari) | 🔴 | `modules/catasto/models/registry.py` | |

### Backend — Services

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 3.1 | `validate_codice_fiscale()` | 🔴 | `services/validation.py` | |
| 3.2 | Comuni ISTAT CSV + `validate_comune()` | 🔴 | `data/comuni_istat.csv` + `services/validation.py` | |
| 3.3 | `validate_superficie()`, `validate_imponibile()`, `validate_importi()` | 🔴 | `services/validation.py` | |
| 3.4 | Unit test validazione | 🔴 | `tests/catasto/test_validation.py` | |
| 4.1 | `import_capacitas()` — mapping colonne + normalizzazioni | 🔴 | `services/import_capacitas.py` | |
| 4.2 | `import_capacitas()` — pipeline validazione VAL-01..08 | 🔴 | `services/import_capacitas.py` | |
| 4.3 | `import_capacitas()` — bulk insert + report_json | 🔴 | `services/import_capacitas.py` | |
| 4.4 | `import_capacitas()` — idempotenza + force | 🔴 | `services/import_capacitas.py` | |
| 4.5 | `import_capacitas()` — upsert coefficienti e aliquote | 🔴 | `services/import_capacitas.py` | |
| 5.1 | `finalize_shapefile_import()` — upsert SCD Type 2 | 🔴 | `services/import_shapefile.py` | |
| 5.2 | `finalize_shapefile_import()` — deriva distretti via ST_Union | 🔴 | `services/import_shapefile.py` | |
| 5.3 | Script bash `import_shapefile_catasto.sh` | 🔴 | `scripts/import_shapefile_catasto.sh` | |

### Backend — Routes

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 6.1 | Routes distretti (lista, dettaglio, kpi, geojson) | 🔴 | `routes/distretti.py` | |
| 6.2 | Routes particelle (lista, dettaglio, utenze, anomalie, geojson) | 🔴 | `routes/particelle.py` | |
| 6.3 | Routes import (upload, finalize, status, report, history) | 🔴 | `routes/import_routes.py` | |
| 6.4 | Routes anomalie (lista, patch) | 🔴 | `routes/anomalie.py` | |
| 6.5 | Registrazione router in main/catasto module | 🔴 | | |

### Frontend

| # | Task | Status | File | Note |
|---|---|---|---|---|
| F1.1 | Tipi TypeScript `catasto.ts` | 🔴 | `src/types/catasto.ts` | |
| F1.2 | Client API `catastoApi` | 🔴 | `src/lib/api/catasto.ts` | |
| F2.1 | Componente `AnomaliaStatusBadge` | 🔴 | `components/catasto/` | |
| F2.2 | Componente `CfBadge` | 🔴 | `components/catasto/` | |
| F2.3 | Componente `KpiCard` | 🔴 | `components/catasto/` | |
| F2.4 | Componente `ImportStatusBadge` | 🔴 | `components/catasto/` | |
| F3 | Dashboard `/catasto` | 🔴 | `app/catasto/page.tsx` | |
| F4 | Wizard Import `/catasto/import` (3 step) | 🔴 | `app/catasto/import/page.tsx` | |
| F5 | Lista Distretti `/catasto/distretti` | 🔴 | `app/catasto/distretti/page.tsx` | |
| F6 | Dettaglio Distretto `/catasto/distretti/[id]` | 🔴 | `app/catasto/distretti/[id]/page.tsx` | |
| F7 | Scheda Particella `/catasto/particelle/[id]` | 🔴 | `app/catasto/particelle/[id]/page.tsx` | |
| F8 | Lista Anomalie `/catasto/anomalie` | 🔴 | `app/catasto/anomalie/page.tsx` | |
| F9 | Layout + navigazione catasto | 🔴 | `app/catasto/layout.tsx` | |

---

## Fase 2 — GIS Map UI

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 2.1 | Container Martin in docker-compose | 🔴 | `docker-compose.yml` | |
| 2.2 | Config `martin.toml` | 🔴 | `config/martin.toml` | |
| 2.3 | Proxy nginx `/tiles/` | 🔴 | `nginx/nginx.conf` | |
| 2.4 | Endpoints GeoJSON distretti + particelle | 🔴 | `routes/distretti.py` | |
| 2.5 | `npm install maplibre-gl` | 🔴 | `frontend/package.json` | |
| 2.6 | Pagina mappa `/catasto/mappa` | 🔴 | `app/catasto/mappa/page.tsx` | |
| 2.7 | Layer distretti MVT cliccabili | 🔴 | | |
| 2.8 | Layer particelle GeoJSON on-demand | 🔴 | | |
| 2.9 | Popup particella con link scheda | 🔴 | | |

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
- `codicefiscale` Python su PyPI: https://pypi.org/project/codicefiscale/
- Copernicus Data Space gratuito per enti EU: https://dataspace.copernicus.eu
