# Prompt Codex — Backend modulo GAIA Riordino v2

Lavora nel repository GAIA rispettando rigorosamente queste regole:

- backend unico monolitico modulare
- nuovo codice backend SOLO in `backend/app/modules/riordino/`
- nessun servizio backend separato
- migrazioni solo in `backend/alembic/versions/`
- stile coerente con gli altri moduli GAIA
- non rompere moduli esistenti

## Documenti di riferimento obbligatori
Prima di scrivere codice, leggi:
- `domain-docs/riordino/docs/PRD_riordino_v2.md` — requisiti completi
- `domain-docs/riordino/docs/ARCHITECTURE_riordino_v2.md` — modello dati, struttura, indici
- `domain-docs/riordino/docs/EXECUTION_PLAN_riordino_v2.md` — ordine implementazione
- `backend/app/MONOLITH_MODULAR.md` — convenzioni monolite

## Contesto funzionale
Modulo per gestione digitale del riordino catastale. Due macrofasi:
- Fase 1: Approvazione Decreto (13 step, inclusi ricorsi)
- Fase 2: Attuazione Decreto (12 step, con branching condizionale)

Gerarchia territoriale: Comune → Maglia → Lotto → Particelle.

## Dipendenze esterne al modulo — FK CRITICHE
- **Users**: tabella `application_users`, PK `id` è **Integer** (non UUID!)
  - Tutti i campi `owner_user_id`, `created_by`, `assigned_to`, `opened_by`, `uploaded_by`, `checked_by`, `approved_by`, `user_id` → `ForeignKey("application_users.id")`, tipo `Mapped[int]` o `Mapped[int | None]`
- **Soggetti**: tabella `ana_subjects`, PK `id` è **UUID**
  - Campi `appellant_subject_id`, `title_holder_subject_id`, `subject_id` → `ForeignKey("ana_subjects.id")`, tipo `Mapped[uuid.UUID | None]`
- **Base class**: `from app.core.database import Base`
- NON importare modelli da altri moduli direttamente. Usa solo FK stringa.

## Cosa devi costruire

### 1. Struttura modulo
```
backend/app/modules/riordino/
├── __init__.py
├── bootstrap.py
├── enums.py
├── permissions.py
├── models/ (14 modelli)
├── schemas/
├── services/ (7 service)
├── repositories/ (4 repository)
└── routes/ (9 route files)
```

### 2. Enum (enums.py)
```python
class PracticeStatus(str, Enum):
    draft = "draft"
    open = "open"
    in_review = "in_review"
    blocked = "blocked"
    completed = "completed"
    archived = "archived"

class PhaseStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    blocked = "blocked"
    completed = "completed"

class StepStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"
    skipped = "skipped"

class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"

class IssueSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    blocking = "blocking"

class IssueCategory(str, Enum):
    administrative = "administrative"
    technical = "technical"
    cadastral = "cadastral"
    documentary = "documentary"
    gis = "gis"

class AppealStatus(str, Enum):
    open = "open"
    under_review = "under_review"
    resolved_accepted = "resolved_accepted"
    resolved_rejected = "resolved_rejected"
    withdrawn = "withdrawn"

class EventType(str, Enum):
    practice_created = "practice_created"
    practice_updated = "practice_updated"
    practice_deleted = "practice_deleted"
    practice_archived = "practice_archived"
    status_changed = "status_changed"
    owner_assigned = "owner_assigned"
    phase_started = "phase_started"
    phase_completed = "phase_completed"
    step_started = "step_started"
    step_completed = "step_completed"
    step_skipped = "step_skipped"
    step_reopened = "step_reopened"
    appeal_created = "appeal_created"
    appeal_resolved = "appeal_resolved"
    issue_opened = "issue_opened"
    issue_closed = "issue_closed"
    document_uploaded = "document_uploaded"
    document_deleted = "document_deleted"
    gis_link_created = "gis_link_created"
    gis_updated = "gis_updated"
    deadline_approaching = "deadline_approaching"
```

### 3. Modelli SQLAlchemy
Implementa TUTTI i 14 modelli esattamente come da ARCHITECTURE v2 sezione 5.
Regole:
- Usa UUID come PK (come altri moduli GAIA)
- Usa `TIMESTAMPTZ` per tutti i timestamp
- Aggiungi indici come specificato
- Campo `version` INTEGER su practice, step, issue per optimistic locking
- Soft-delete (`deleted_at`) su practice e document
- JSONB per `activation_condition`, `outcome_options`, `payload_json`

### 4. Migration Alembic
Una singola migration con:
- Tutte le 14 tabelle `riordino_*`
- Tutti gli indici
- Seed dei 25 step template (13 Fase 1 + 12 Fase 2) da PRD v2 sezione 8.1

### 5. Workflow service — regole critiche

#### advance_step(practice_id, step_id, outcome_code=None)
1. Verifica step sia `todo` o `in_progress`
2. Se `is_decision` e `outcome_code` non fornito → 422
3. Se `requires_document` e nessun doc allegato allo step → 422
4. Se issue `blocking` collegata allo step → 403 con messaggio
5. Se checklist_item `is_blocking` non checked → 403
6. Cambia stato a `done`, salva `outcome_code`, `outcome_notes`, `completed_at`
7. Se step è `F2_VERIFICA` e outcome = `conforme` → auto-skip step branch=`anomalia`
8. Genera evento audit `step_completed`
9. Return step aggiornato

#### complete_phase(practice_id, phase_id, approved_by)
1. Verifica tutti step obbligatori `done` o `skipped`
2. Se Fase 1: verifica nessun appeal `open` o `under_review`
3. Verifica nessuna issue `blocking` aperta nella fase
4. Cambia stato fase a `completed`
5. Genera evento `phase_completed`

#### start_phase(practice_id, phase_id)
1. Se Fase 2: verifica Fase 1 `completed`
2. Cambia stato a `in_progress`
3. Genera evento `phase_started`

### 6. Code generation pratica
Formato: `RIO-{ANNO}-{PROGRESSIVO:04d}`
Es: `RIO-2026-0001`, `RIO-2026-0002`
Progressivo: max(code per anno) + 1, con lock per evitare duplicati.

### 7. Storage documenti
- Path: `/data/gaia/riordino/{practice_id}/{phase_code}/{step_code}/{uuid}.{ext}`
- Se `step_code` è NULL, usare `_general`
- Max 50MB per file
- MIME accettati: pdf, doc, docx, xls, xlsx, csv, jpg, png, tif, dwg, dxf, zip
- Validazione MIME e dimensione nel service, non nella route

### 8. Notifiche
Job periodico (o check su advance_step):
- Calcola scadenze da step `F1_OSSERVAZIONI` (pubblicazione_at + 90gg) e `F1_TRASCRIZIONE` (decreto_at + 30gg)
- Crea notification a 30gg, 7gg, 1g dalla scadenza
- Crea notification su assegnazione step/pratica

### 9. Test minimi obbligatori
```
test_create_practice_generates_phases_and_steps
test_create_practice_generates_correct_step_count
test_delete_practice_only_draft
test_advance_step_ok
test_advance_decision_step_without_outcome_fails
test_advance_step_with_blocking_issue_fails
test_advance_step_requires_document_fails_without_doc
test_complete_phase1_with_open_appeal_fails
test_complete_phase1_ok
test_start_phase2_without_phase1_complete_fails
test_branching_conforme_skips_anomalia_steps
test_branching_non_conforme_keeps_anomalia_steps
test_create_appeal
test_resolve_appeal
test_upload_document
test_soft_delete_document
test_optimistic_locking_conflict
test_dashboard_counts
```

## Vincoli importanti
- Non creare microservizi
- Non importare modelli cross-modulo (solo FK UUID)
- Non introdurre dipendenze pesanti
- Mantieni codice leggibile
- Commenta solo la logica di business non ovvia
- Ogni modifica genera evento in `riordino_events`

## Output atteso
- Codice backend completo e funzionante
- Migration Alembic con seed
- Tutti gli endpoint documentati
- Test essenziali verdi
