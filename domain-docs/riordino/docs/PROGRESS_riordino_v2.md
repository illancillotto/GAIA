# GAIA Riordino — Progress Tracking v2

## Stato generale
- Modulo: Riordino
- Stato complessivo: **backend core done, frontend base in progress, hardening backend done**
- Owner: TBD
- Ultimo aggiornamento: 2026-04-09

---

## Milestone

| Milestone | Stato | Target | Note |
|---|---|---|---|
| M0 Analisi e design | ✅ done | — | PRD v2, Architecture v2, Execution Plan v2 completi |
| M1 Fondazione backend | ✅ done | — | Struttura modulo, modelli, migration, CRUD pratiche, dashboard, test backend base |
| M2 Workflow Fase 1 | ✅ done | — | Workflow service, ricorsi, documenti, issue, notifiche, timeline, test backend |
| M3 Workflow Fase 2 | ✅ done | — | Branching `F2_VERIFICA`, GIS links, particelle, party links, chiusura pratica, configurazione persistente backend e test verdi |
| M4 Frontend | 🟡 partial | — | Dashboard, lista pratiche, workspace pratica operativo con workflow, pannelli dati, notification bell, configurazione admin base e UX di conferma/stato; restano affinamenti visuali finali |
| M5 Hardening | ✅ done | — | Enablement modulo, section gating backend, export, seed demo e test integrazione end-to-end completati |

---

## Checklist tecnica

### M0 — Analisi
- [x] PRD v2 approvato
- [x] Architecture v2 definita
- [x] Matrice step template definita (25 step)
- [x] Modello branching deciso (skip)
- [x] Entità appeal definita
- [x] Gerarchia territoriale definita (Comune/Maglia/Lotto)
- [x] Storage documenti definito (filesystem locale)
- [x] GIS MVP definito (link manuale)
- [x] Sistema scadenze/notifiche definito
- [x] Execution plan v2 pronto
- [x] Prompt codex backend/frontend/fullstack v2 pronti

### M1 — Fondazione backend
- [x] `enums.py` creato
- [x] 14 modelli SQLAlchemy creati
- [x] Migration Alembic creata
- [x] Seed 25 step template presente in migration
- [x] `bootstrap.py` registrato nel monolite
- [x] `PracticeRepository` implementato
- [x] `PracticeService` implementato (CRUD + generazione fasi/step)
- [x] `DashboardService` implementato
- [x] Route CRUD pratiche funzionanti
- [x] Route dashboard funzionante
- [x] Test M1 verdi nel pacchetto `backend/tests/riordino/`

### M2 — Workflow Fase 1
- [x] `WorkflowService.advance_step()` implementato
- [x] `WorkflowService.skip_step()` implementato
- [x] `WorkflowService.reopen_step()` implementato
- [x] `WorkflowService.complete_phase()` implementato
- [x] `WorkflowService.start_phase()` implementato
- [x] `AppealService` implementato
- [x] `DocumentService` implementato (upload filesystem)
- [x] `IssueService` implementato
- [x] `NotificationService` implementato
- [x] Route workflow funzionanti
- [x] Route ricorsi funzionanti
- [x] Route documenti funzionanti (upload/download/delete)
- [x] Route issue funzionanti
- [x] Route notifiche funzionanti
- [x] Route timeline funzionante
- [x] Test M2 verdi nel pacchetto `backend/tests/riordino/`

### M3 — Workflow Fase 2
- [x] Branching condizionale F2_VERIFICA implementato
- [x] Auto-skip step branch=anomalia se conforme
- [x] Route particelle (CRUD + import CSV)
- [x] Route party links
- [x] Route GIS links
- [x] Chiusura pratica implementata
- [x] CRUD persistente tipologie documento
- [x] CRUD persistente tipologie issue
- [x] Endpoint municipalities da pratiche reali
- [x] Test M3 core verdi nel pacchetto `backend/tests/riordino/`

### M4 — Frontend
- [x] Types TypeScript (`riordino.ts`)
- [x] API client (`riordino-api.ts`)
- [x] Layout modulo + navigazione
- [x] Dashboard page + DashboardCards
- [x] Lista pratiche + PracticeTable + PracticeFilters base
- [x] Workspace pratica sintetico + PracticeHeader base
- [x] WorkflowStepper + StepCard + StepDecisionForm base
- [x] AppealPanel
- [x] IssuePanel
- [x] DocumentPanel (upload base)
- [x] GisPanel
- [x] TimelinePanel
- [x] NotificationBell
- [x] StatusBadge + ConfirmDialog
- [x] Configurazione admin base collegata alle API reali
- [x] `npm run lint` verde
- [x] `npx tsc --noEmit` verde

### M5 — Hardening
- [x] Middleware permessi/modulo su tutti endpoint `riordino`
- [x] Test permessi modulo/sezione backend
- [x] Export ZIP dossier pratica
- [x] Export CSV riepilogo
- [x] Seed demo (5 pratiche)
- [x] Test integrazione caso standard Fase 1 → Fase 2
- [x] Test integrazione caso con ricorso
- [x] Test integrazione caso anomalia catastale
- [x] Test verifica audit trail
- [x] Enablement modulo `riordino` su `application_users`, bootstrap admin, home GAIA e sidebar piattaforma
- [x] Seed sezioni `riordino` in `bootstrap_sections.py`
- [x] PROGRESS aggiornato

---

## Ultimo avanzamento backend

- Creato il modulo `backend/app/modules/riordino/` con models, schemas, repositories, services e routes.
- Registrato il router del modulo in `backend/app/api/router.py` e i modelli in `backend/app/db/base.py`.
- Aggiunta la migration `20260407_0033_riordino_module_tables.py` con seed iniziale degli step template.
- Aggiunta la migration `20260409_0034_add_riordino_module_flag.py` per abilitazione modulo su `application_users`.
- Aggiunta la migration `20260409_0035_riordino_config_types.py` per tipologie documento e issue persistenti.
- Aggiunto il pacchetto test `backend/tests/riordino/` con test backend su creazione pratica, workflow, branching, ricorsi, documenti, dashboard, optimistic locking, particelle e party links.
- Estese le route `config` con CRUD reale per `document-types` e `issue-types`, oltre ai comuni derivati dalle pratiche.
- Applicato gating backend con `require_module("riordino")` e `require_section(...)` sui router del dominio.
- Aggiunti export backend per `summary.csv` e `dossier.zip` della pratica con copertura test dedicata.
- Aggiunto il seed demo `backend/app/scripts/seed_riordino_demo.py` con 5 pratiche idempotenti in stati utili al collaudo manuale.
- Estesa la suite backend con test integrazione end-to-end su caso standard, caso con ricorso, caso anomalia catastale e verifica audit trail completo.

## Ultimo avanzamento frontend e piattaforma

- Aggiunte le superfici `frontend/src/app/riordino/` per dashboard, lista pratiche, dettaglio pratica e configurazione base.
- Aggiunti i componenti `frontend/src/components/riordino/` e il client tipizzato `frontend/src/lib/riordino-api.ts`.
- Integrato il modulo `riordino` nella home GAIA, nella platform sidebar e nella sidebar modulo.
- Estesa la gestione utenti GAIA con il flag `module_riordino` su backend e frontend.
- Esteso il workspace pratica con azioni workflow principali, pannelli ricorsi, issue, documenti, GIS e timeline.
- Collegata la pagina configurazione admin al CRUD reale di tipologie documento e issue.
- Allineata la pagina configurazione anche a `requiredSection="riordino.config"` lato frontend.
- Aggiunte CTA frontend nel workspace pratica per export CSV riepilogo e dossier ZIP.
- Rifinita la UX del workspace con badge stato leggibili, evidenza scadenze, dialoghi di conferma per azioni sensibili su fasi, step, issue, ricorsi e documenti, oltre a messaggistica esplicita su conflitti `409`.
- Stato residuo: collaudo manuale finale e rifiniture visuali minori.

---

## Decision log

| Data | Decisione | Motivazione |
|---|---|---|
| 2026-04-07 | Branching: tutti step presenti, skip per rami non pertinenti | Semplicità implementativa, trasparenza flusso |
| 2026-04-07 | Ricorsi: entità dedicata RiordinoAppeal | Dati specifici (ricorrente, commissione, scadenza, esito) non modellabili come issue |
| 2026-04-07 | Scadenze: calcolo automatico + notifica in-app | Operatori necessitano alert proattivi |
| 2026-04-07 | PREGEO/DOCTE/estratto mappa: step workflow + doc obbligatorio | Tracciabilità azione + documento prodotto |
| 2026-04-07 | GIS MVP: solo link manuale | Mappa embedded rimandata |
| 2026-04-07 | Storage: filesystem locale | Sufficiente per primo rilascio, migrabile a object storage |
| 2026-04-07 | Gerarchia: Comune → Maglia → Lotto | Riflette struttura operativa reale |
| 2026-04-07 | Soggetti via modulo utenze (FK read-only) | Evita duplicazione anagrafica |

---

## Blocker

| Data | Blocco | Severità | Azione |
|---|---|---|---|
| 2026-04-07 | ~~Verificare struttura application_users~~ | ✅ risolto | PK Integer, modello `ApplicationUser` |
| 2026-04-07 | ~~Verificare tabella soggetti utenze~~ | ✅ risolto | `ana_subjects`, PK UUID |
