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
| M1 Fondazione backend | ✅ done | Migration, modelli, enums, parser (23 test), import service |
| M2 API e query layer | ✅ done | Repository, schemas, route import + query, router.py |
| M3 Bootstrap e integrazione | ✅ done | Section keys, flag module_ruolo, router registrato in api/router.py |
| M4 Frontend | ✅ done | Dashboard, avvisi, dettaglio, stats, import, widget soggetto |
| M5 Hardening | ✅ completo | Permessi require_module attivi; test API, parser/import realistici e catasto parcels coperti |

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
- [x] Test unitari parser — **23 test, tutti passanti** (`backend/tests/ruolo/test_parser.py`)
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
- [x] `/ruolo` — CTA stato vuoto apre import in modale con fallback `Apri pagina`
- [x] `/ruolo` — dashboard riallineata al pattern UI/UX dei moduli maturi (hero workspace, KPI, action cards, pannelli)
- [x] `/ruolo/import` — upload + lista job + polling automatico, riallineata al pattern UI/UX dei moduli maturi
- [x] `/ruolo/avvisi` — lista con filtri URL-driven + paginazione, riallineata al pattern UI/UX dei moduli maturi
- [x] `/ruolo/avvisi` — ricerca unificata live (`q`) con debounce, soglia minima 3 caratteri, toggle `Solo avvisi non collegati` inline e dettaglio avviso in modale embedded
- [x] `/ruolo/avvisi/[id]` — dettaglio completo con partite espandibili, riallineato al pattern UI/UX dei moduli maturi
- [x] `/ruolo/stats` — statistiche per anno e per comune interattive, riallineate al pattern UI/UX dei moduli maturi
- [x] Integrazione scheda soggetto `RuoloAvvisiSection`, riallineata al pattern UI/UX del modulo con hero compatta, mini-stat e CTA coerenti
- [x] Nessun errore lint (`ReadLints` verde)

### M5 — Hardening
- [x] `backend/tests/ruolo/test_parser.py` — **23 test passanti**
- [x] Permessi `require_module("ruolo")` applicati su tutti gli endpoint
- [x] Fix permessi admin esistenti: migration di backfill `module_ruolo` per account `admin` / `super_admin` creati prima del modulo
- [x] Export CSV `GET /ruolo/avvisi/export` implementato
- [x] Compatibilità Pydantic v2/UUID sugli endpoint `GET /ruolo/import/jobs`, `GET /ruolo/import/jobs/{job_id}` e sui response model `ruolo/schemas.py`
  - Fixato il mismatch tra UUID ORM nativi e campi `str` nei model di risposta, mantenendo serializzazione JSON string verso il frontend
  - Aggiunto test API dedicato `backend/tests/ruolo/test_api.py`
- [x] Allineamento parser/import ai file DMP reali 2025 di Capacitàs
  - Lo split delle `Partita CNC` ora supporta sia il primo header con prefisso `<qm500>--` sia i blocchi successivi con header `---------Partita CNC ...`
  - Normalizzato `catasto_comuni.codice_sister` composito (es. `F272#MOGORO#0#0`) al codice catastale corto usabile in `catasto_parcels.comune_codice`
  - Normalizzati i comuni di partita catastale da DMP: rimozione quote tra parentesi e alias storici (`SILI'*ORISTANO`, `OLLASTRA SIMAXIS`, `SAN NICOLO ARCIDANO`)
  - Hardening del parser particelle: le righe legenda/header (`DOM.=DOMANDA IRRIGUA`, `FOG.=FOGLIO CATASTALE`, `CONSUMI DA CONTATORE`, separatori) non possono alimentare `catasto_parcels`
  - Risoluzione comune solo con match esatto case-insensitive; eliminato il fallback parziale `ILIKE '%nome%'` per evitare casi come `ARBOREA` risolto in `PALMAS ARBOREA`
  - Fallback risoluzione codice comune da `cat_particelle` quando `catasto_comuni` non contiene il comune ma la particella GAIA esiste in modo univoco
  - Aggiunti test `backend/tests/ruolo/test_parser.py` e `backend/tests/ruolo/test_import_helpers.py`
- [x] Report job Ruolo persistito e consultabile da UI
  - `params_json` del job contiene `report_summary` e `report_preview` con motivazioni dei casi `skipped` / `error`
  - In `/ruolo/import` ogni card job espone una modale “Apri report” con riepilogo e dettaglio operativo
  - Semantica esplicitata: `records_skipped` = avvisi importati ma non collegati a un soggetto in Anagrafica
- [x] Collegamento risolto `ruolo_particelle -> cat_particelle`
  - Aggiunta FK nullable `cat_particella_id` verso `cat_particelle.id`
  - L'import ruolo valorizza la FK solo per match univoci su codice catastale, foglio, particella e subalterno
  - Se il ruolo ha un subalterno ma `cat_particelle` ha solo la particella base, il match e consentito solo se la base e univoca e viene marcato `base_without_sub`
  - Aggiunto script `backend/scripts/backfill_ruolo_cat_particella_id.py` per allineare i dati gia importati
  - Aggiunto script `backend/scripts/repair_ruolo_catasto_parcels.py` per normalizzare dati gia importati, ricostruire `catasto_parcels` mancanti e rimuovere orfani sporchi con foglio/particella non numerici
  - Bonifica locale 2026-05-13: `catasto_parcel_not_resolved` ridotti da 4.099 a 3; eliminati 536 `catasto_parcels` orfani sporchi; export aggiornato in `exports/report_backfill_ruolo_cat_particella.md`
  - Bonifica mismatch comune 2026-05-13: riparate 5.520 righe con codice comune errato; 5.234 sono diventate collegate a `cat_particelle`; non collegate residue ridotte a 2.583
  - Estesa al Ruolo la regola storica gia usata da sync Terreni Capacitas per lo scambio Arborea/Terralba: se la particella non esiste sul comune sorgente, il resolver prova l'altro comune della coppia e marca il match con `swapped_arborea_terralba`; recuperate 249 righe ulteriori, non collegate residue a 2.334
  - Allineata la risoluzione Ruolo delle frazioni catastali di Oristano alla logica Capacitas/Agenzia: `SILI -> sezione E`, `NURAXINIEDDU -> D`, `MASSAMA -> C`, `DONIGALA -> B`. Il repair `--repair-oristano-frazione-sections` ricalcola anche righe gia collegate per evitare match permissivi su solo `G113 + foglio + particella`.
- [x] `backend/tests/ruolo/test_import.py` — import service, report job, skipped/error preview
- [x] `backend/tests/ruolo/test_api.py` — filtro unificato `GET /ruolo/avvisi?q=...` su nominativo, CF, comune, anno e codice utenza
- [x] `backend/tests/ruolo/test_catasto_parcels.py` — logica temporale `catasto_parcels`
- [x] `backend/tests/ruolo/test_import_integration.py` — smoke `integration-light` su blocchi DMP 2025 realistici con parser reale, merge duplicati, skipped report e filtro sezioni `CONSUMI`
- [x] `frontend/tests/e2e/ruolo-avvisi.spec.ts` — soglia minima 3 caratteri, debounce live search e apertura modale dettaglio
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

### 2026-04-17
- Allineata anche l'integrazione embedded `RuoloAvvisiSection` nella scheda soggetto del dominio utenze, con visual language coerente al workspace `ruolo` e CTA operative uniformate.
- Ridotta l'altezza della hero di `/ruolo/import` quando aperta in modale (`embedded=1`), per migliorare leggibilità e densità del workspace rapido.
- Compattata anche la KPI row del workspace rapido `/ruolo/import` in modalità embedded, con gap e tile più bassi per aumentare spazio utile sopra il fold.
- `/ruolo/import` ora prova a rilevare automaticamente l'anno tributario dal file selezionato (contenuto PDF/testo o filename) e consente comunque override manuale.
- Euristica anno `ruolo` resa deterministica: priorità a filename `R2024...`, poi pattern `Partita CNC 01.02021000039305` da cui viene estratto `2021`, infine fallback testuali.
- Aumentato il limite upload Nginx del progetto per supportare file `ruolo` fino a 128 MB senza errore `413 Request Entity Too Large`.

### 2026-05-15
- `GET /ruolo/avvisi` e `GET /ruolo/avvisi/export` supportano ora il parametro `q`, con matching su `codice_cnc`, `nominativo_raw`, `codice_fiscale_raw`, `codice_utenza`, `anno_tributario` e `comune_nome` delle partite collegate.
- `/ruolo/avvisi` e stata riallineata alla UX di `utenze`: campo singolo di ricerca, stato iniziale “Ricerca pronta”, avvio automatico dopo 3 caratteri, debounce client-side e aggiornamento URL con `router.replace` per evitare raffiche di chiamate.
- Le card avviso aprono una modale con iframe embedded del dettaglio; `/ruolo/avvisi/[id]` nasconde il top header quando riceve `?embedded=1`.
- Aggiunti test backend sul filtro `q` e test Playwright sul comportamento live search + apertura modale.
