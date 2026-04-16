# GAIA Ruolo — Progress Tracking v1.0

## Stato generale

- Modulo: Ruolo
- Stato complessivo: **implementazione completata M1–M5 (hardening parziale)**
- Owner: TBD
- Ultimo aggiornamento: 2026-04-16

---

## Milestone

| Milestone | Stato | Note |
|-----------|-------|------|
| M0 Analisi e design | ✅ done | PRD v1, Execution Plan v1, Prompt Codex prodotti |
| M1 Fondazione backend | ✅ done | Migration, modelli, enums, parser (14 test), import service |
| M2 API e query layer | ✅ done | Repository, schemas, route import + query, router.py |
| M3 Bootstrap e integrazione | ✅ done | Section keys, flag module_ruolo, router registrato in api/router.py |
| M4 Frontend | ✅ done | Dashboard, avvisi, dettaglio, stats, import, widget soggetto |
| M5 Hardening | 🔄 parziale | Permessi require_module attivi; test API e integration test pendenti |

---

## Checklist tecnica

### M0 — Analisi
- [x] PRD v1 prodotto
- [x] Execution Plan v1 prodotto
- [x] Prompt Codex prodotto
- [x] Formato file `.dmp` analizzato (sample 2 partite)
- [x] Modello dati definito (4 tabelle `ruolo_*` + `catasto_parcels`)
- [x] Logica temporale particelle definita (`valid_from`/`valid_to`)
- [x] Pattern job asincrono definito (su modello `wc_sync_job`)
- [x] Integrazione con `ana_subjects` via CF/PIVA definita
- [x] Unità SUP.CATA. verificata con dominio — **are** (1 ara = 100 mq)
- [x] Dipendenza `pypdf==5.4.0` aggiunta in requirements

### M1 — Fondazione backend
- [x] Migration Alembic creata e applicata (`20260416_0048_add_ruolo_module.py`)
  - [x] `ruolo_import_jobs`
  - [x] `ruolo_avvisi`
  - [x] `ruolo_partite`
  - [x] `ruolo_particelle`
  - [x] `catasto_parcels`
- [x] Modelli ORM in `backend/app/modules/ruolo/models.py`
- [x] Modello `CatastoParcel` aggiunto in `backend/app/models/catasto.py`
- [x] Enumerazioni in `ruolo/enums.py`
- [x] Parser `ruolo/services/parser.py`
  - [x] Split partite per marcatore `<inizio>` / `<-fine->`
  - [x] Estrazione codice CNC
  - [x] Parse riga N2 (CF/PIVA + extra)
  - [x] Parse nominativo, domicilio, residenza
  - [x] Parse partite catastali (codice, comune, tributi)
  - [x] Parse co-intestati (opzionale)
  - [x] Parse righe particelle positional (con gestione subalterni letterali)
  - [x] Parse righe N4 (totali + codice utenza)
  - [x] Fault-tolerance: errore per-partita senza interruzione
- [x] Test unitari parser — **14 test, tutti passanti** (`backend/tests/ruolo/test_parser.py`)
- [x] Import service `ruolo/services/import_service.py`
  - [x] Background task con sessione DB indipendente
  - [x] Estrazione testo da PDF (+ fallback `.dmp` grezzo)
  - [x] Loop import con contatori
  - [x] Upsert avvisi idempotente
  - [x] Risoluzione soggetto via CF/PIVA
  - [x] Upsert `catasto_parcels` con logica temporale
  - [x] Gestione `SubjectNotFound` → skipped
  - [x] Finalizzazione job (status, contatori, error_detail, finished_at)

### M2 — API e query layer
- [x] Schemas Pydantic in `ruolo/schemas.py`
- [x] Repository in `ruolo/repositories.py`
- [x] `ruolo/routes/import_routes.py`
  - [x] `POST /ruolo/import/upload`
  - [x] `GET /ruolo/import/jobs`
  - [x] `GET /ruolo/import/jobs/{job_id}`
- [x] `ruolo/routes/query_routes.py`
  - [x] `GET /ruolo/avvisi`
  - [x] `GET /ruolo/avvisi/export` (CSV)
  - [x] `GET /ruolo/avvisi/{avviso_id}`
  - [x] `GET /ruolo/soggetti/{subject_id}/avvisi`
  - [x] `GET /ruolo/particelle`
  - [x] `GET /ruolo/stats`
  - [x] `GET /ruolo/stats/comuni`
  - [x] `GET /catasto/parcels`
  - [x] `GET /catasto/parcels/{parcel_id}/history`
- [x] `ruolo/router.py` — aggregazione router con prefisso `/ruolo`

### M3 — Bootstrap e integrazione
- [x] `ruolo/bootstrap.py` con 4 section keys
- [x] Flag `module_ruolo` su `ApplicationUser` (ORM + enabled_modules)
- [x] `CurrentUser` e `ApplicationUser` TypeScript aggiornati con `module_ruolo`
- [x] `backend/app/scripts/bootstrap_sections.py` aggiornato
- [x] Router registrato in `backend/app/api/router.py`
- [x] Navigazione frontend aggiornata (platform-sidebar, module-sidebar, sidebar)
- [x] Integrazione scheda soggetto anagrafica
  - [x] Endpoint `GET /ruolo/soggetti/{subject_id}/avvisi` accessibile
  - [x] Componente `RuoloAvvisiSection` nella pagina soggetti utenze
  - [x] Link da avviso → dettaglio funzionante

### M4 — Frontend
- [x] `frontend/src/types/ruolo.ts`
- [x] `frontend/src/lib/ruolo-api.ts`
- [x] `frontend/src/components/ruolo/module-page.tsx`
- [x] Layout modulo `frontend/src/app/ruolo/layout.tsx`
- [x] `/ruolo` — dashboard con stats per anno + ultimi job
- [x] `/ruolo/import` — upload + lista job + polling automatico
- [x] `/ruolo/avvisi` — lista con filtri URL-driven + paginazione
- [x] `/ruolo/avvisi/[id]` — dettaglio completo con partite espandibili
- [x] `/ruolo/stats` — statistiche per anno e per comune interattive
- [x] Integrazione scheda soggetto `RuoloAvvisiSection`
- [x] Nessun errore lint (`ReadLints` verde)

### M5 — Hardening
- [x] `backend/tests/ruolo/test_parser.py` — **14 test passanti**
- [x] Permessi `require_module("ruolo")` applicati su tutti gli endpoint
- [x] Export CSV `GET /ruolo/avvisi/export` implementato
- [ ] `backend/tests/ruolo/test_import.py` — import, idempotenza, orfani (pendente)
- [ ] `backend/tests/ruolo/test_api.py` — endpoint principali (pendente)
- [ ] `backend/tests/ruolo/test_catasto_parcels.py` — logica temporale (pendente)
- [ ] Import completo file Ruolo 2024 (~9.810 partite) su dati reali (pendente)

---

## Decisioni aperte

| # | Decisione | Stato | Note |
|---|-----------|-------|------|
| D1 | Unità colonna `SUP.CATA.` | **✅ CHIUSA** | Are (1 ara = 100 mq = 0,01 ha). Colonne: `sup_catastale_are` (valore letto) + `sup_catastale_ha` (are / 100). |
| D2 | Libreria estrazione testo PDF (`pypdf` vs `pdfminer.six`) | Aperta | Verificare quale è già in requirements; se nessuna, aggiungere `pypdf` |
| D6 | Campo `1.679.520` riga N4 | **✅ CHIUSA** | Significato non determinato. Salvare as-is in `n4_campo_sconosciuto` (VARCHAR 30, nullable). Analisi futura. |
| D3 | Significato campi `00000000 00 N` riga N2 | Aperta | Conservati in `n2_extra_raw`; analisi futura |
| D4 | Co-intestati come FK in MVP vs testo libero | **Deciso: testo libero** | Post-MVP collegare come FK verso `ana_subjects` |
| D5 | Blocco automatico re-import anno già presente | **Deciso: avvertimento senza blocco** | L'operatore vede warning, non viene bloccato |

---

## Change log

### 2026-04-16
- PRD v1, Execution Plan v1, Prompt Codex e Progress v1 prodotti.
- Formato file `.dmp` analizzato su sample Ruolo 2024 (2 partite CNC).
- Modello dati definito: 4 tabelle `ruolo_*` + `catasto_parcels` con logica temporale.
- Decisione architetturale: `ruolo` modulo autonomo (non sub-modulo di `utenze`).
- Decisione: co-intestati come testo libero nel MVP.
- Decisione: avvertimento (non blocco) su re-import anno già presente.
- Punto aperto D1 (unità superfici) identificato come prerequisito critico per M1.

### 2026-04-16 (aggiornamento)
- D1 chiusa: SUP.CATA. confermata in are. Colonne DB: `sup_catastale_are` + `sup_catastale_ha`.
- Aggiornati PRD, Execution Plan e Prompt Codex con unità corretta.

### 2026-04-16 (implementazione M1–M5)
- M1 completata: migration applicata, modelli ORM, enums, parser con 14 test unitari, import service asincrono.
- M2 completata: schemas Pydantic, repository, 10 endpoint REST (import + query + export CSV + catasto parcels).
- M3 completata: bootstrap section keys, flag `module_ruolo` su ApplicationUser, router registrato.
- M4 completata: 5 pagine frontend (`/ruolo`, `/ruolo/avvisi`, `/ruolo/avvisi/[id]`, `/ruolo/stats`, `/ruolo/import`), widget soggetto, navigazione aggiornata.
- M5 parziale: permessi `require_module` attivi; test di integrazione API pendenti.
