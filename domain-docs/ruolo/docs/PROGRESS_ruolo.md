# GAIA Ruolo — Progress Tracking v1.0

## Stato generale

- Modulo: Ruolo
- Stato complessivo: **design completato — implementazione non avviata**
- Owner: TBD
- Ultimo aggiornamento: 2026-04-16

---

## Milestone

| Milestone | Stato | Note |
|-----------|-------|------|
| M0 Analisi e design | ✅ done | PRD v1, Execution Plan v1, Prompt Codex prodotti |
| M1 Fondazione backend | ⬜ todo | Migration, modelli, parser, import job |
| M2 API e query layer | ⬜ todo | Repository, schemas, endpoint |
| M3 Bootstrap e integrazione | ⬜ todo | Section keys, flag modulo, scheda soggetto |
| M4 Frontend | ⬜ todo | Tutte le pagine + integrazione anagrafica |
| M5 Hardening | ⬜ todo | Test, permessi, export, validazione dati reali |

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
- [ ] Dipendenza `pypdf` / `pdfminer.six` verificata in requirements

### M1 — Fondazione backend
- [ ] Migration Alembic creata e applicata
  - [ ] `ruolo_import_jobs`
  - [ ] `ruolo_avvisi`
  - [ ] `ruolo_partite`
  - [ ] `ruolo_particelle`
  - [ ] `catasto_parcels`
- [ ] Modelli ORM in `backend/app/modules/ruolo/models.py`
- [ ] Modello `CatastoParcel` aggiunto in catasto
- [ ] Enumerazioni in `ruolo/enums.py`
- [ ] Parser `ruolo/services/parser.py`
  - [ ] Split partite per marcatore `<inizio>` / `<-fine->`
  - [ ] Estrazione codice CNC
  - [ ] Parse riga N2 (CF/PIVA + extra)
  - [ ] Parse nominativo, domicilio, residenza
  - [ ] Parse partite catastali (codice, comune, tributi)
  - [ ] Parse co-intestati (opzionale)
  - [ ] Parse righe particelle (con gestione subalterni letterali)
  - [ ] Parse righe N4 (totali + codice utenza)
  - [ ] Fault-tolerance: errore per-partita senza interruzione
- [ ] Test unitari parser (6+ test su sample reale)
- [ ] Import service `ruolo/services/import_service.py`
  - [ ] Background task con sessione DB indipendente
  - [ ] Estrazione testo da PDF (+ fallback `.dmp` grezzo)
  - [ ] Loop import con contatori
  - [ ] Upsert avvisi idempotente
  - [ ] Risoluzione soggetto via CF/PIVA
  - [ ] Upsert `catasto_parcels` con logica temporale
  - [ ] Gestione `SubjectNotFound` → skipped
  - [ ] Finalizzazione job (status, contatori, error_detail, finished_at)

### M2 — API e query layer
- [ ] Schemas Pydantic in `ruolo/schemas.py`
- [ ] Repository in `ruolo/repositories.py`
- [ ] `ruolo/routes/import_routes.py`
  - [ ] `POST /ruolo/import/upload`
  - [ ] `GET /ruolo/import/jobs`
  - [ ] `GET /ruolo/import/jobs/{job_id}`
- [ ] `ruolo/routes/query_routes.py`
  - [ ] `GET /ruolo/avvisi`
  - [ ] `GET /ruolo/avvisi/{avviso_id}`
  - [ ] `GET /ruolo/soggetti/{subject_id}/avvisi`
  - [ ] `GET /ruolo/particelle`
  - [ ] `GET /ruolo/stats`
  - [ ] `GET /ruolo/stats/comuni`
- [ ] `ruolo/router.py` — aggregazione router con prefisso `/ruolo`
- [ ] Test API base

### M3 — Bootstrap e integrazione
- [ ] `ruolo/bootstrap.py` con 4 section keys
- [ ] Flag `module_ruolo` su `ApplicationUser`
- [ ] Aggiornamento `enabled_modules` e schemi auth/users
- [ ] `backend/app/scripts/bootstrap_sections.py` aggiornato
- [ ] Router registrato in `backend/app/api/router.py`
- [ ] Navigazione frontend aggiornata (home moduli, sidebar, menu)
- [ ] Integrazione scheda soggetto anagrafica
  - [ ] Endpoint `GET /ruolo/soggetti/{subject_id}/avvisi` accessibile
  - [ ] Componente frontend sezione "Ruolo Consortile"
  - [ ] Link da avviso → dettaglio funzionante

### M4 — Frontend
- [ ] `frontend/src/types/ruolo.ts`
- [ ] `frontend/src/lib/api/ruolo.ts`
- [ ] Layout modulo + navigazione `/ruolo`
- [ ] `/ruolo/import` — upload + lista job
- [ ] `/ruolo/import/[job_id]` — log dettagliato
- [ ] `/ruolo/avvisi` — lista con filtri
- [ ] `/ruolo/avvisi/[avviso_id]` — dettaglio completo
- [ ] `/ruolo` — dashboard
- [ ] `/ruolo/stats` — statistiche
- [ ] Integrazione scheda soggetto (componente "Ruolo Consortile")
- [ ] `npm run lint` verde
- [ ] `npx tsc --noEmit` verde

### M5 — Hardening
- [ ] `backend/tests/ruolo/test_parser.py` — 6+ test
- [ ] `backend/tests/ruolo/test_import.py` — import, idempotenza, orfani
- [ ] `backend/tests/ruolo/test_api.py` — endpoint principali
- [ ] `backend/tests/ruolo/test_catasto_parcels.py` — logica temporale
- [ ] Permessi section gating verificati per ruolo
- [ ] Export CSV `GET /ruolo/avvisi/export`
- [ ] Import completo file Ruolo 2024 (~9.810 partite) su test
  - [ ] Durata < 5 minuti
  - [ ] Contatore `skipped` plausibile
  - [ ] Nessun crash su edge case
  - [ ] `catasto_parcels` popolata correttamente

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
