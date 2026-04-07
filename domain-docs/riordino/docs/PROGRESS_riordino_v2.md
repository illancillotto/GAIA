# GAIA Riordino — Progress Tracking v2

## Stato generale
- Modulo: Riordino
- Stato complessivo: **ready for development**
- Owner: TBD
- Ultimo aggiornamento: 2026-04-07

---

## Milestone

| Milestone | Stato | Target | Note |
|---|---|---|---|
| M0 Analisi e design | ✅ done | — | PRD v2, Architecture v2, Execution Plan v2 completi |
| M1 Fondazione backend | 🔲 todo | — | Enum, modelli, migration, CRUD pratiche, dashboard |
| M2 Workflow Fase 1 | 🔲 todo | — | Workflow service, ricorsi, documenti, notifiche |
| M3 Workflow Fase 2 | 🔲 todo | — | Branching, particelle, GIS, chiusura pratica |
| M4 Frontend | 🔲 todo | — | Dashboard, lista, workspace, pannelli |
| M5 Hardening | 🔲 todo | — | Permessi fini, export, test integrazione |

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
- [ ] `enums.py` creato
- [ ] 14 modelli SQLAlchemy creati
- [ ] Migration Alembic creata
- [ ] Seed 25 step template
- [ ] `bootstrap.py` registrato nel monolite
- [ ] `PracticeRepository` implementato
- [ ] `PracticeService` implementato (CRUD + generazione fasi/step)
- [ ] `DashboardService` implementato
- [ ] Route CRUD pratiche funzionanti
- [ ] Route dashboard funzionante
- [ ] Test M1 verdi (4 test)

### M2 — Workflow Fase 1
- [ ] `WorkflowService.advance_step()` implementato
- [ ] `WorkflowService.skip_step()` implementato
- [ ] `WorkflowService.reopen_step()` implementato
- [ ] `WorkflowService.complete_phase()` implementato
- [ ] `WorkflowService.start_phase()` implementato
- [ ] `AppealService` implementato
- [ ] `DocumentService` implementato (upload filesystem)
- [ ] `IssueService` implementato
- [ ] `NotificationService` implementato
- [ ] Route workflow funzionanti
- [ ] Route ricorsi funzionanti
- [ ] Route documenti funzionanti (upload/download/delete)
- [ ] Route issue funzionanti
- [ ] Route notifiche funzionanti
- [ ] Route timeline funzionante
- [ ] Test M2 verdi (12 test)

### M3 — Workflow Fase 2
- [ ] Branching condizionale F2_VERIFICA implementato
- [ ] Auto-skip step branch=anomalia se conforme
- [ ] Route particelle (CRUD + import CSV)
- [ ] Route party links
- [ ] Route GIS links
- [ ] Chiusura pratica implementata
- [ ] Test M3 verdi (5 test)

### M4 — Frontend
- [ ] Types TypeScript (`riordino.ts`)
- [ ] API client (`riordino-api.ts`)
- [ ] Layout modulo + navigazione
- [ ] Dashboard page + DashboardCards
- [ ] Lista pratiche + PracticeTable + PracticeFilters
- [ ] Workspace pratica + PracticeHeader
- [ ] WorkflowStepper + StepCard + StepDecisionForm
- [ ] AppealPanel
- [ ] IssuePanel
- [ ] DocumentPanel (upload drag-and-drop)
- [ ] GisPanel
- [ ] TimelinePanel
- [ ] NotificationBell
- [ ] StatusBadge + ConfirmDialog
- [ ] Configurazione admin
- [ ] `npm run lint` verde
- [ ] `npx tsc --noEmit` verde

### M5 — Hardening
- [ ] Middleware permessi su tutti endpoint
- [ ] Test permessi per ruolo
- [ ] Export ZIP dossier pratica
- [ ] Export CSV riepilogo
- [ ] Seed demo (5-10 pratiche)
- [ ] Test integrazione caso standard Fase 1 → Fase 2
- [ ] Test integrazione caso con ricorso
- [ ] Test integrazione caso anomalia catastale
- [ ] Test verifica audit trail
- [ ] PROGRESS aggiornato

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
