"""All enum definitions for the Riordino module."""

from enum import Enum


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


class DocumentType(str, Enum):
    atto_pubblicazione = "atto_pubblicazione"
    decreto = "decreto"
    nota_trascrizione = "nota_trascrizione"
    attestazione_conservatoria = "attestazione_conservatoria"
    ricevuta_voltura = "ricevuta_voltura"
    ricorso = "ricorso"
    verbale_commissione = "verbale_commissione"
    csv_particelle = "csv_particelle"
    estratto_mappa = "estratto_mappa"
    istanza_fusione = "istanza_fusione"
    documento_docte = "documento_docte"
    file_pregeo = "file_pregeo"
    mappale_unito = "mappale_unito"
    atti_rt = "atti_rt"
    documento_finale = "documento_finale"
    altro = "altro"


class PartyRole(str, Enum):
    proprietario = "proprietario"
    intestatario = "intestatario"
    ricorrente = "ricorrente"
    tecnico = "tecnico"
    altro = "altro"


class GisSyncStatus(str, Enum):
    manual = "manual"
    pending = "pending"
    synced = "synced"


class TaskType(str, Enum):
    manual = "manual"
    technical = "technical"
    review = "review"


class NotificationType(str, Enum):
    deadline_warning = "deadline_warning"
    assignment = "assignment"
    phase_transition = "phase_transition"
    issue_assigned = "issue_assigned"


# Phase codes
PHASE_1 = "phase_1"
PHASE_2 = "phase_2"

# Allowed MIME types for document upload
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "application/acad",
    "application/dxf",
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",
}

# Max file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Document storage root
DOCUMENT_STORAGE_ROOT = "/data/gaia/riordino"

# Deadline notification thresholds (days before)
DEADLINE_THRESHOLDS = {
    "F1_OSSERVAZIONI": [30, 7, 1],
    "F1_TRASCRIZIONE": [7, 1],
    "default": [7, 1],
}
