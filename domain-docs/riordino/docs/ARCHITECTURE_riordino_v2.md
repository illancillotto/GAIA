# GAIA Riordino — Architettura funzionale e tecnica v2

## 1. Posizionamento nel sistema GAIA

Modulo applicativo del monolite modulare GAIA.

Path canonici:
- backend: `backend/app/modules/riordino/`
- frontend: `frontend/src/app/riordino/`
- componenti: `frontend/src/components/riordino/`
- docs: `domain-docs/riordino/docs/`

Dipendenze da moduli GAIA esistenti:
- **core auth**: tabella `application_users`, sistema ruoli/permessi
- **modulo utenze**: anagrafica soggetti (proprietari, intestatari)
- Nessuna dipendenza da catasto o network

---

## 2. Architettura logica

```
┌─────────────────────────────────────────────┐
│                  Frontend                    │
│  Next.js — /riordino/*                      │
│  Dashboard | Lista | Workspace | Config     │
└──────────────┬──────────────────────────────┘
               │ REST API (Bearer token)
┌──────────────▼──────────────────────────────┐
│                  Backend                     │
│  FastAPI — /api/riordino/*                   │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐  │
│  │ Routes   │ │ Services  │ │ Repos      │  │
│  │          │→│ Workflow   │→│ SQLAlchemy │  │
│  │          │ │ Issue      │ │            │  │
│  │          │ │ Document   │ │            │  │
│  │          │ │ Appeal     │ │            │  │
│  │          │ │ Dashboard  │ │            │  │
│  │          │ │ Notify     │ │            │  │
│  └──────────┘ └───────────┘ └────────────┘  │
│       ↕ auth middleware (GAIA core)          │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│  PostgreSQL — tabelle riordino_*             │
│  + FK verso users, soggetti modulo utenze    │
└─────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│  Filesystem — /data/gaia/riordino/           │
│  {practice_id}/{phase_code}/{step_code}/     │
└─────────────────────────────────────────────┘
```

---

## 3. Struttura backend

```
backend/app/modules/riordino/
├── __init__.py
├── bootstrap.py              # registrazione route nel monolite
├── enums.py                  # tutti gli enum del modulo
├── permissions.py            # permessi e decoratori ruolo
├── models/
│   ├── __init__.py
│   ├── practice.py
│   ├── phase.py
│   ├── step.py
│   ├── step_template.py
│   ├── task.py
│   ├── appeal.py             # NUOVO
│   ├── issue.py
│   ├── document.py
│   ├── parcel_link.py
│   ├── party_link.py
│   ├── gis_link.py
│   ├── event.py
│   ├── checklist.py
│   └── notification.py       # NUOVO
├── schemas/
│   ├── __init__.py
│   ├── practice.py
│   ├── workflow.py
│   ├── appeal.py             # NUOVO
│   ├── issue.py
│   ├── document.py
│   ├── gis.py
│   ├── event.py
│   ├── notification.py       # NUOVO
│   └── config.py
├── services/
│   ├── __init__.py
│   ├── practice_service.py
│   ├── workflow_service.py   # logica avanzamento, branching, validazioni
│   ├── appeal_service.py     # NUOVO
│   ├── issue_service.py
│   ├── document_service.py
│   ├── notification_service.py # NUOVO
│   └── dashboard_service.py
├── repositories/
│   ├── __init__.py
│   ├── practice_repository.py
│   ├── workflow_repository.py
│   ├── appeal_repository.py  # NUOVO
│   └── issue_repository.py
└── routes/
    ├── __init__.py
    ├── practices.py
    ├── workflow.py
    ├── appeals.py             # NUOVO
    ├── issues.py
    ├── documents.py
    ├── gis.py
    ├── dashboard.py
    ├── notifications.py       # NUOVO
    └── config.py
```

---

## 4. Struttura frontend

```
frontend/src/app/riordino/
├── page.tsx                       # dashboard modulo
├── layout.tsx                     # layout condiviso modulo
├── pratiche/
│   ├── page.tsx                   # lista pratiche
│   └── [id]/
│       └── page.tsx               # workspace pratica
└── configurazione/
    └── page.tsx                   # admin config

frontend/src/components/riordino/
├── dashboard/
│   └── DashboardCards.tsx
├── practice-list/
│   ├── PracticeTable.tsx
│   └── PracticeFilters.tsx
├── practice-detail/
│   ├── PracticeHeader.tsx
│   └── PracticeWorkspace.tsx
├── workflow/
│   ├── WorkflowStepper.tsx
│   ├── StepCard.tsx
│   └── StepDecisionForm.tsx
├── appeals/
│   └── AppealPanel.tsx
├── issues/
│   └── IssuePanel.tsx
├── documents/
│   └── DocumentPanel.tsx
├── gis/
│   └── GisPanel.tsx
├── timeline/
│   └── TimelinePanel.tsx
├── notifications/
│   └── NotificationBell.tsx
└── shared/
    ├── StatusBadge.tsx
    └── ConfirmDialog.tsx
```

---

## 5. Modello dati completo

### riordino_step_templates
Template configurabili per generazione step.

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| phase_code | VARCHAR(20) | `phase_1`, `phase_2` |
| code | VARCHAR(50) | es. `F1_STUDIO_PIANO` |
| title | VARCHAR(200) | |
| sequence_no | INTEGER | ordine nel template |
| is_required | BOOLEAN | default true |
| branch | VARCHAR(50) NULL | es. `anomalia`, NULL per step lineari |
| activation_condition | JSONB NULL | regola attivazione (outcome step precedente) |
| requires_document | BOOLEAN | default false |
| is_decision | BOOLEAN | default false |
| outcome_options | JSONB NULL | es. `["conforme","non_conforme"]` |
| is_active | BOOLEAN | default true, per disabilitare template |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### riordino_practices

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| code | VARCHAR(20) UNIQUE | `RIO-{ANNO}-{PROG}` |
| title | VARCHAR(300) | |
| description | TEXT NULL | |
| municipality | VARCHAR(100) | comune |
| grid_code | VARCHAR(50) | maglia |
| lot_code | VARCHAR(50) | lotto |
| current_phase | VARCHAR(20) | `phase_1` o `phase_2` |
| status | VARCHAR(20) | enum PracticeStatus |
| owner_user_id | INTEGER FK → application_users | responsabile |
| opened_at | TIMESTAMPTZ NULL | quando passa da draft a open |
| completed_at | TIMESTAMPTZ NULL | |
| archived_at | TIMESTAMPTZ NULL | |
| deleted_at | TIMESTAMPTZ NULL | soft-delete |
| version | INTEGER | optimistic locking, default 1 |
| created_by | INTEGER FK → application_users | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Indici: `(status)`, `(municipality)`, `(owner_user_id)`, `(current_phase)`, `(deleted_at)`

### riordino_phases

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| practice_id | UUID FK → practices | |
| phase_code | VARCHAR(20) | `phase_1`, `phase_2` |
| status | VARCHAR(20) | enum PhaseStatus |
| started_at | TIMESTAMPTZ NULL | |
| completed_at | TIMESTAMPTZ NULL | |
| approved_by | INTEGER FK → application_users NULL | chi ha approvato chiusura |
| notes | TEXT NULL | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Indici: `(practice_id)`, `(practice_id, phase_code)` UNIQUE

### riordino_steps

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| practice_id | UUID FK → practices | |
| phase_id | UUID FK → phases | |
| template_id | UUID FK → step_templates NULL | template di origine |
| code | VARCHAR(50) | |
| title | VARCHAR(200) | |
| sequence_no | INTEGER | |
| status | VARCHAR(20) | enum StepStatus |
| is_required | BOOLEAN | |
| branch | VARCHAR(50) NULL | |
| is_decision | BOOLEAN | default false |
| outcome_code | VARCHAR(50) NULL | esito per step decisionali |
| outcome_notes | TEXT NULL | |
| skip_reason | TEXT NULL | motivazione se skipped |
| requires_document | BOOLEAN | |
| owner_user_id | INTEGER FK → application_users NULL | |
| due_at | TIMESTAMPTZ NULL | |
| started_at | TIMESTAMPTZ NULL | |
| completed_at | TIMESTAMPTZ NULL | |
| version | INTEGER | optimistic locking, default 1 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Indici: `(practice_id, phase_id)`, `(practice_id, status)`, `(practice_id, code)` UNIQUE

### riordino_tasks

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| practice_id | UUID FK | |
| step_id | UUID FK → steps | sempre figlio di step |
| title | VARCHAR(200) | |
| type | VARCHAR(50) | `manual`, `technical`, `review` |
| status | VARCHAR(20) | enum TaskStatus |
| owner_user_id | INTEGER FK → application_users NULL | |
| due_at | TIMESTAMPTZ NULL | |
| completed_at | TIMESTAMPTZ NULL | |
| notes | TEXT NULL | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### riordino_appeals

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| practice_id | UUID FK | |
| phase_id | UUID FK | sempre Fase 1 |
| step_id | UUID FK → steps | step F1_RICORSI |
| appellant_subject_id | UUID NULL | FK → ana_subjects.id (UUID) |
| appellant_name | VARCHAR(200) | denormalizzato |
| filed_at | DATE | data presentazione |
| deadline_at | DATE NULL | scadenza |
| commission_name | VARCHAR(200) NULL | |
| commission_date | DATE NULL | |
| status | VARCHAR(30) | enum AppealStatus |
| resolution_notes | TEXT NULL | |
| resolved_at | TIMESTAMPTZ NULL | |
| created_by | INTEGER FK → application_users | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Indici: `(practice_id)`, `(practice_id, status)`

### riordino_issues

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| practice_id | UUID FK | |
| phase_id | UUID FK NULL | |
| step_id | UUID FK NULL | |
| type | VARCHAR(50) | configurabile |
| category | VARCHAR(30) | `administrative`, `technical`, `cadastral`, `documentary`, `gis` |
| severity | VARCHAR(20) | enum IssueSeverity |
| status | VARCHAR(20) | `open`, `in_progress`, `closed` |
| title | VARCHAR(300) | |
| description | TEXT NULL | |
| opened_by | INTEGER FK → application_users | |
| assigned_to | INTEGER FK → application_users NULL | |
| opened_at | TIMESTAMPTZ | |
| closed_at | TIMESTAMPTZ NULL | |
| resolution_notes | TEXT NULL | |
| version | INTEGER | optimistic locking |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Indici: `(practice_id)`, `(practice_id, severity, status)`, `(assigned_to, status)`

### riordino_documents

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| practice_id | UUID FK | |
| phase_id | UUID FK NULL | |
| step_id | UUID FK NULL | |
| issue_id | UUID FK NULL | |
| appeal_id | UUID FK NULL | |
| document_type | VARCHAR(50) | configurabile |
| version_no | INTEGER | default 1 |
| storage_path | VARCHAR(500) | path filesystem |
| original_filename | VARCHAR(300) | |
| mime_type | VARCHAR(100) | |
| file_size_bytes | BIGINT | |
| uploaded_by | INTEGER FK → application_users | |
| uploaded_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ NULL | soft-delete |
| notes | TEXT NULL | |
| created_at | TIMESTAMPTZ | |

Indici: `(practice_id)`, `(practice_id, document_type)`, `(step_id)`, `(appeal_id)`

### riordino_parcel_links

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| practice_id | UUID FK | |
| foglio | VARCHAR(20) | |
| particella | VARCHAR(20) | |
| subalterno | VARCHAR(20) NULL | |
| quality_class | VARCHAR(50) NULL | classe coltura |
| title_holder_name | VARCHAR(200) NULL | intestatario |
| title_holder_subject_id | UUID NULL | FK verso soggetti utenze |
| source | VARCHAR(50) NULL | `csv_import`, `manual` |
| notes | TEXT NULL | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Indici: `(practice_id)`, `(practice_id, foglio, particella)`

### riordino_party_links

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| practice_id | UUID FK | |
| subject_id | UUID | FK → ana_subjects.id (UUID) |
| role | VARCHAR(50) | `proprietario`, `intestatario`, `ricorrente`, `tecnico`, `altro` |
| notes | TEXT NULL | |
| created_at | TIMESTAMPTZ | |

Indici: `(practice_id)`, `(practice_id, subject_id)` UNIQUE

### riordino_gis_links

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| practice_id | UUID FK | |
| layer_name | VARCHAR(100) | |
| feature_id | VARCHAR(100) NULL | |
| geometry_ref | TEXT NULL | |
| sync_status | VARCHAR(20) | `manual`, `pending`, `synced` |
| last_synced_at | TIMESTAMPTZ NULL | |
| notes | TEXT NULL | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### riordino_events

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| practice_id | UUID FK | |
| phase_id | UUID FK NULL | |
| step_id | UUID FK NULL | |
| event_type | VARCHAR(50) | enum EventType |
| payload_json | JSONB NULL | dettagli strutturati |
| created_by | INTEGER FK → application_users | |
| created_at | TIMESTAMPTZ | |

Indici: `(practice_id, created_at DESC)`, `(event_type)`

Event types: `practice_created`, `practice_updated`, `practice_deleted`, `practice_archived`, `status_changed`, `owner_assigned`, `phase_started`, `phase_completed`, `step_started`, `step_completed`, `step_skipped`, `step_reopened`, `appeal_created`, `appeal_resolved`, `issue_opened`, `issue_closed`, `document_uploaded`, `document_deleted`, `gis_link_created`, `gis_updated`, `deadline_approaching`

### riordino_checklist_items

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| step_id | UUID FK → steps | |
| label | VARCHAR(300) | |
| is_checked | BOOLEAN | default false |
| is_blocking | BOOLEAN | default false |
| checked_by | INTEGER FK → application_users NULL | |
| checked_at | TIMESTAMPTZ NULL | |
| sequence_no | INTEGER | |
| created_at | TIMESTAMPTZ | |

### riordino_notifications

| Colonna | Tipo | Note |
|---------|------|------|
| id | UUID PK | |
| user_id | INTEGER FK → application_users | destinatario |
| practice_id | UUID FK NULL | |
| type | VARCHAR(50) | `deadline_warning`, `assignment`, `phase_transition`, `issue_assigned` |
| message | TEXT | |
| is_read | BOOLEAN | default false |
| created_at | TIMESTAMPTZ | |

Indici: `(user_id, is_read, created_at DESC)`

---

## 6. Transizioni workflow

### Pratica
```
draft ──→ open ──→ in_review ──→ completed ──→ archived
               ↕
            blocked
```
`draft` → soft-delete possibile

### Fase
```
not_started ──→ in_progress ──→ completed
                    ↕
                 blocked
```
Fase 2 `in_progress` richiede Fase 1 `completed`.

### Step
```
todo ──→ in_progress ──→ done
  │           ↕            │
  │        blocked         │ (reopen, solo manager)
  │                        ↓
  └──→ skipped        in_progress
```

### Appeal
```
open ──→ under_review ──→ resolved_accepted
   │                  └──→ resolved_rejected
   └──→ withdrawn
```

---

## 7. Branching condizionale Fase 2

Alla creazione pratica, tutti gli step Fase 2 vengono generati.

Quando `F2_VERIFICA` (step decisionale) viene completato:

```
F2_VERIFICA.outcome_code = 'conforme'
  → F2_FUSIONE.status = 'skipped', skip_reason = 'Verifica conforme'
  → F2_DOCTE.status = 'skipped', skip_reason = 'Verifica conforme'
  → F2_RIPRISTINO.status = 'skipped', skip_reason = 'Verifica conforme'
  → F2_ESTRATTO_MAPPA prosegue normalmente

F2_VERIFICA.outcome_code = 'non_conforme'
  → tutti gli step branch='anomalia' restano 'todo'
  → operatore attiva quelli pertinenti, skip gli altri manualmente
```

Il `workflow_service` implementa questa logica nel metodo `advance_step()`.

---

## 8. Permission model

I permessi del modulo si registrano nel sistema centralizzato GAIA. Mapping:

| Permesso | admin | manager | operator | tecnico | viewer |
|----------|-------|---------|----------|---------|--------|
| `riordino.practice.create` | ✓ | ✓ | | | |
| `riordino.practice.read` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `riordino.practice.update` | ✓ | ✓ | | | |
| `riordino.practice.delete` | ✓ | ✓ | | | |
| `riordino.practice.archive` | ✓ | ✓ | | | |
| `riordino.step.advance` | ✓ | ✓ | ✓* | ✓* | |
| `riordino.step.skip` | ✓ | ✓ | | | |
| `riordino.step.reopen` | ✓ | ✓ | | | |
| `riordino.phase.transition` | ✓ | ✓ | | | |
| `riordino.appeal.create` | ✓ | ✓ | ✓ | | |
| `riordino.appeal.resolve` | ✓ | ✓ | | | |
| `riordino.issue.create` | ✓ | ✓ | ✓ | ✓ | |
| `riordino.issue.close` | ✓ | ✓ | | ✓** | |
| `riordino.document.upload` | ✓ | ✓ | ✓ | ✓ | |
| `riordino.document.delete` | ✓ | ✓ | | | |
| `riordino.config.manage` | ✓ | | | | |
| `riordino.notification.read` | ✓ | ✓ | ✓ | ✓ | ✓ |

`*` solo step assegnati a sé
`**` solo issue con category `technical` o `cadastral`

---

## 9. Integrazioni

### GAIA Core Auth
- Tabella: `application_users`, PK `id` **Integer**
- FK `owner_user_id`, `created_by`, `assigned_to`, `opened_by`, `uploaded_by`, `checked_by`, `approved_by`, `user_id` → `ForeignKey("application_users.id")`, tipo `Mapped[int]` o `Mapped[int | None]`
- Middleware auth esistente per JWT/session
- Ruoli registrati nel sistema permessi centrale (`ApplicationUserRole`)

### Modulo Utenze (Anagrafica)
- Tabella: `ana_subjects`, PK `id` **UUID**
- `riordino_party_links.subject_id` → `ForeignKey("ana_subjects.id")`, tipo `Mapped[uuid.UUID]`
- `riordino_appeals.appellant_subject_id` → `ForeignKey("ana_subjects.id")`, tipo `Mapped[uuid.UUID | None]`
- `riordino_parcel_links.title_holder_subject_id` → `ForeignKey("ana_subjects.id")`, tipo `Mapped[uuid.UUID | None]`
- Import read-only, nessuna scrittura cross-modulo
- Base class condivisa: `from app.core.database import Base`

### GIS (futuro)
- MVP: solo `riordino_gis_links` come link manuali
- Futuro: visualizzazione mappa embedded, sync automatica

### Catasto (futuro)
- Nessuna integrazione nel primo rilascio
- Il modello `riordino_parcel_links` è predisposto per import dati catastali
