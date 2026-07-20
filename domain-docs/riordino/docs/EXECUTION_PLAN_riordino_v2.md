# GAIA Riordino — Execution Plan v2

## Principi
- Backend first, poi frontend
- Rilascio incrementale e testabile
- Nessun refactor moduli esistenti
- Ogni fase ha "done when" verificabile
- Il perimetro dei blocchi parte sempre dalle particelle Agenzia delle Entrate (`CatAdeParticella`)

---

## Roadmap estensione blocchi e Fase 1 dati catastali

Ordine consigliato: `M0 → M1 → M2 → M4 → M5 → M3 → M6 → M7 → M8 → M9`.

| Milestone | Obiettivo | Done when |
|---|---|---|
| M0 Riallineamento PRD/architettura | Aggiornare docs e decision log su blocchi, AdE, Capacitas, Sister, GIS | Docs aggiornate e coerenti con codice |
| M1 Blocco di riordino | Tabelle, API e snapshot AdE da comune/lotto/lista/GIS | Blocco creabile da AdE, assegnabile, auditato |
| M2 Dashboard blocchi | Vista admin/coordinatore/operatore dei blocchi assegnati | Dashboard mostra blocchi, dettaglio e creazione admin con preview |
| M3 Workspace blocco e GIS | Lista particelle, stato match, apertura mappa | Operatore vede particelle e apre GIS se match |
| M4 Fase 1 confronto AdE vs Capacitas | Classificazione match/disallineamenti | Ogni snapshot ha stato Catasto consortile e Capacitas |
| M5 Fase 1 visure Sister | Richiesta/scarico/associazione visura per particella | Stato visura tracciato, batch Elaborazioni/SISTER accodato e documento associabile dopo download |
| M6 Procedura guidata operatori | Task guidati per confronto, visura, anomalie | Operatore lavora per step e il sistema traccia |
| M7 Coordinamento e audit | Vista coordinatore su operatori e operazioni | Coordinatore vede blocchi, attività e audit |
| M8 Fase 2 e chiusura riordino | Collegamento blocchi a pratiche Fase 2/PREGEO/DOCTE/GIS finale | Pratica Fase 2 generabile da blocco, con particelle importate |
| M9 Report/export/collaudo | Export e collaudo end-to-end | Export CSV blocco/pratica, test, coverage, docs e Graphify aggiornati |

---

## Fase 1 — Fondazione backend (M1)

### 1.1 Setup struttura modulo
- Creare namespace `backend/app/modules/riordino/` con tutte le sottocartelle
- Creare `__init__.py`, `enums.py`, `permissions.py`, `bootstrap.py`
- Registrare il modulo nel router principale GAIA

### 1.2 Enum e costanti
Implementare in `enums.py`:
- `PracticeStatus`: draft, open, in_review, blocked, completed, archived
- `PhaseStatus`: not_started, in_progress, blocked, completed
- `StepStatus`: todo, in_progress, blocked, done, skipped
- `TaskStatus`: todo, in_progress, blocked, done
- `IssueSeverity`: low, medium, high, blocking
- `IssueCategory`: administrative, technical, cadastral, documentary, gis
- `AppealStatus`: open, under_review, resolved_accepted, resolved_rejected, withdrawn
- `EventType`: tutti i tipi evento definiti in ARCHITECTURE
- `DocumentType`, `PartyRole`, `GisSyncStatus`

### 1.3 Models SQLAlchemy
Implementare tutti i modelli da ARCHITECTURE v2 sezione 5:
1. `RiordinoStepTemplate`
2. `RiordinoPractice`
3. `RiordinoPhase`
4. `RiordinoStep`
5. `RiordinoTask`
6. `RiordinoAppeal`
7. `RiordinoIssue`
8. `RiordinoDocument`
9. `RiordinoParcelLink`
10. `RiordinoPartyLink`
11. `RiordinoGisLink`
12. `RiordinoEvent`
13. `RiordinoChecklistItem`
14. `RiordinoNotification`

### 1.4 Migration Alembic
- Una migration per tutte le tabelle `riordino_*`
- Seed dei `riordino_step_templates` (25 step template da PRD v2 sezione 8.1)
- Seed dizionari: `document_types`, `issue_types`, `municipalities` (come dati in step_templates o tabelle config separate)

### 1.5 Repository layer
- `PracticeRepository`: CRUD base con filtri (status, municipality, owner, phase)
- `WorkflowRepository`: query step/fasi per pratica, bulk update step status
- `AppealRepository`: CRUD ricorsi per pratica
- `IssueRepository`: CRUD issue con filtri severity/status

### 1.6 Service layer base
- `PracticeService`:
  - `create_practice()`: crea pratica + 2 fasi + tutti step da template + evento audit
  - `update_practice()`: con optimistic locking
  - `delete_practice()`: solo draft, soft-delete
  - `archive_practice()`: solo completed
- `DashboardService`:
  - `get_summary()`: conteggi per stato, fase, issue, ultimi N eventi

### 1.7 Routes base
- `POST /api/riordino/practices`
- `GET /api/riordino/practices` (con query params filtri)
- `GET /api/riordino/practices/{id}` (dettaglio completo con fasi, step, conteggi issue/doc)
- `PATCH /api/riordino/practices/{id}`
- `DELETE /api/riordino/practices/{id}`
- `GET /api/riordino/dashboard`

### 1.8 Test
- test create practice → verifica fasi e step generati
- test delete practice in stato open → 403
- test dettaglio pratica → struttura completa
- test dashboard → conteggi corretti

### Done when
- Pratica creabile via API con 2 fasi e 25 step generati da template
- Dettaglio pratica restituisce struttura completa
- Dashboard restituisce conteggi
- Test verdi

---

## Fase 2 — Workflow Fase 1 (M2)

### 2.1 WorkflowService
- `advance_step()`: valida prerequisiti, cambia stato, genera evento
  - Se step decisionale: richiede `outcome_code`
  - Se step con `requires_document`: verifica almeno 1 documento allegato
  - Se issue blocking sullo step: blocca
  - Se checklist_item blocking non checked: blocca
- `skip_step()`: solo manager, richiede `skip_reason`
- `reopen_step()`: solo manager, genera evento
- `start_phase()`: Fase 1 auto-start quando pratica passa a `open`
- `complete_phase()`: valida tutti step obbligatori done/skipped, no issue blocking, no appeal open

### 2.2 AppealService
- `create_appeal()`: crea ricorso collegato a F1_RICORSI
- `update_appeal()`: aggiorna dati
- `resolve_appeal()`: chiude con esito, genera evento

### 2.3 DocumentService
- `upload_document()`: salva file su filesystem, crea record, genera evento
  - Path: `/data/gaia/riordino/{practice_id}/{phase_code}/{step_code}/{uuid}.{ext}`
  - Validazione MIME e dimensione
- `list_documents()`: filtri per pratica/fase/step/tipo/appeal
- `soft_delete_document()`: solo manager

### 2.4 NotificationService
- `check_deadlines()`: job periodico che controlla scadenze e crea notifiche
  - F1_OSSERVAZIONI: notifica a 30gg, 7gg, 1g dalla scadenza
  - F1_TRASCRIZIONE: notifica a 7gg, 1g
  - Step con due_at: notifica a 7gg, 1g
- `list_notifications()`: per utente, non lette first
- `mark_read()`: segna come letta

### 2.5 IssueService base
- `create_issue()`: collegata a pratica/fase/step
- `close_issue()`: con resolution_notes
- `list_issues()`: filtri severity/status/category

### 2.6 Routes Fase 1
- `POST /api/riordino/practices/{id}/steps/{step_id}/advance`
- `POST /api/riordino/practices/{id}/steps/{step_id}/skip`
- `POST /api/riordino/practices/{id}/steps/{step_id}/reopen`
- `POST /api/riordino/practices/{id}/phases/{phase_id}/start`
- `POST /api/riordino/practices/{id}/phases/{phase_id}/complete`
- `POST /api/riordino/practices/{id}/appeals`
- `GET /api/riordino/practices/{id}/appeals`
- `PATCH /api/riordino/practices/{id}/appeals/{appeal_id}`
- `POST /api/riordino/practices/{id}/appeals/{appeal_id}/resolve`
- `POST /api/riordino/practices/{id}/documents` (multipart upload)
- `GET /api/riordino/practices/{id}/documents`
- `GET /api/riordino/documents/{doc_id}/download`
- `DELETE /api/riordino/documents/{doc_id}`
- `POST /api/riordino/practices/{id}/issues`
- `GET /api/riordino/practices/{id}/issues`
- `POST /api/riordino/practices/{id}/issues/{issue_id}/close`
- `GET /api/riordino/practices/{id}/events`
- `GET /api/riordino/notifications`
- `POST /api/riordino/notifications/{id}/read`

### 2.7 Test
- test advance step F1_STUDIO_PIANO → ok
- test advance step decisionale senza outcome → 422
- test advance step con issue blocking → 403
- test complete Fase 1 con appeal open → 403
- test complete Fase 1 con tutti step done → ok
- test skip step con motivazione → ok
- test upload documento → file su disco + record db
- test create/resolve appeal → status transitions

### Done when
- Fase 1 interamente percorribile via API
- Ricorsi gestibili end-to-end
- Documenti caricabili e scaricabili
- Passaggio a Fase 2 bloccato se prerequisiti mancanti
- Scadenze calcolate e notifiche create
- Test verdi

---

## Fase 3 — Workflow Fase 2 (M3)

### 3.1 Branching condizionale nel WorkflowService
Estendere `advance_step()`:
- Quando `F2_VERIFICA` viene completato con outcome:
  - `conforme`: auto-skip step branch=`anomalia`
  - `non_conforme`: step branch=`anomalia` restano `todo`

### 3.2 ParcelLink management
- `POST /api/riordino/practices/{id}/parcels` — crea link
- `POST /api/riordino/practices/{id}/parcels/import-csv` — import CSV
- `GET /api/riordino/practices/{id}/parcels` — lista
- `DELETE /api/riordino/practices/{id}/parcels/{parcel_id}`

### 3.3 PartyLink management
- `POST /api/riordino/practices/{id}/parties`
- `GET /api/riordino/practices/{id}/parties`
- `DELETE /api/riordino/practices/{id}/parties/{party_id}`

### 3.4 GIS links
- `POST /api/riordino/practices/{id}/gis-links`
- `GET /api/riordino/practices/{id}/gis-links`
- `PATCH /api/riordino/gis-links/{link_id}`

### 3.5 Chiusura pratica
- `POST /api/riordino/practices/{id}/complete`:
  - Fase 2 completed
  - No issue aperte
  - Approvazione manager
  - Status → completed
  - Evento audit

### 3.6 Test
- test branching conforme → step anomalia skipped
- test branching non_conforme → step anomalia attivi
- test import CSV particelle
- test chiusura pratica con issue aperta → 403
- test chiusura pratica ok → completed

### Done when
- Fase 2 percorribile caso standard e anomalo
- Import CSV particelle
- GIS links manuali
- Chiusura pratica end-to-end
- Test verdi

---

## Fase 4 — Frontend (M4)

### 4.1 Setup
- Route `/riordino`, `/riordino/pratiche`, `/riordino/pratiche/[id]`, `/riordino/configurazione`
- Layout modulo con navigazione
- Typed API client per tutti gli endpoint

### 4.2 Dashboard
- `DashboardCards`: conteggi pratiche per stato, fase, issue, ultimi eventi

### 4.3 Lista pratiche
- `PracticeTable`: tabella con sort/filtri (stato, fase, comune, responsabile, periodo)
- `PracticeFilters`: pannello filtri
- Paginazione server-side

### 4.4 Workspace pratica
- `PracticeHeader`: codice, titolo, stato, fase, owner, comune/maglia/lotto, azioni principali
- `WorkflowStepper`: stepper visuale con colori per stato, indicatore fase corrente
- `StepCard`: dettaglio step con azioni (advance, skip, upload doc, checklist)
- `StepDecisionForm`: form per step decisionali con outcome selection
- `AppealPanel`: lista ricorsi, creazione, risoluzione (solo Fase 1)
- `IssuePanel`: lista issue, creazione, chiusura
- `DocumentPanel`: lista documenti per fase/step, upload, download, soft-delete
- `GisPanel`: lista link GIS, creazione
- `TimelinePanel`: eventi ordinati cronologicamente
- `NotificationBell`: icona con conteggio non lette, dropdown lista

### 4.5 Configurazione (admin)
- CRUD step templates
- CRUD document types
- CRUD issue types

### 4.6 Test frontend
- `npm run lint`
- `npx tsc --noEmit`
- Verifica flusso pratica completo manualmente

### Done when
- Operatore gestisce pratica completa da UI
- Dashboard funzionante
- Notifiche visibili
- Lint e type check verdi

---

## Fase 5 — Hardening (M5)

### 5.1 Permessi fini
- Implementare middleware permessi su tutti gli endpoint
- Verificare matrice permessi con test

### 5.2 Export
- `GET /api/riordino/practices/{id}/export` → ZIP dossier pratica (metadati JSON + documenti)
- `GET /api/riordino/practices/export-csv` → CSV riepilogo pratiche

### 5.3 Seed demo
- Script seed con 5-10 pratiche in stati diversi
- Dati demo per test UAT

### 5.4 Test integrazione
- Caso standard Fase 1 → Fase 2 → chiusura
- Caso con ricorso
- Caso con anomalia catastale
- Verifica permessi per ruolo
- Verifica audit trail completo

### Done when
- Suite test completa verde
- Permessi verificati
- Seed demo funzionante
- Dossier export funzionante

---

## Backlog tecnico ordinato

### Backend (ordine implementazione)
1. enums.py
2. models (tutti)
3. migration Alembic + seed step templates
4. repositories
5. practice_service + routes CRUD
6. dashboard_service + route
7. workflow_service + routes
8. appeal_service + routes
9. document_service + routes
10. issue_service + routes
11. notification_service + routes
12. parcel/party/gis routes
13. branching condizionale F2
14. chiusura pratica
15. export
16. permessi fini
17. test unitari per ogni service
18. test integrazione

### Frontend (ordine implementazione)
1. API client tipizzato
2. Layout modulo + route
3. Dashboard
4. Lista pratiche + filtri
5. Workspace pratica (header + stepper)
6. StepCard + DecisionForm
7. DocumentPanel + upload
8. AppealPanel
9. IssuePanel
10. TimelinePanel
11. GisPanel
12. NotificationBell
13. Configurazione admin
14. Lint + typecheck

---

## Rischi e mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| Step template troppo rigidi | Tabella configurabile, admin può aggiungere/modificare |
| Branching F2 complesso | Logica centralizzata in workflow_service, testata unitariamente |
| Performance dashboard con molte pratiche | Indici dedicati, query ottimizzate, conteggi cached se necessario |
| Integrazione auth GAIA non chiara | Verificare struttura users/ruoli prima di iniziare M1 |
| Storage filesystem non scalabile | Sufficiente per primo rilascio, migrazione a object storage futura |
