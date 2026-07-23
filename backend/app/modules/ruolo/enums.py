from __future__ import annotations

from enum import Enum

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11 compatibility fallback.
    class StrEnum(str, Enum):
        pass


class RuoloImportStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CodiceTributo(StrEnum):
    MANUTENZIONE = "0648"
    ISTITUZIONALE = "0985"
    IRRIGAZIONE = "0668"


class CatastoParcelSource(StrEnum):
    RUOLO_IMPORT = "ruolo_import"
    SISTER = "sister"
    CAPACITAS = "capacitas"


class RuoloTributiPaymentImportStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RuoloTributiPaymentRecordStatus(StrEnum):
    VALID = "valid"
    REVERSED = "reversed"
    DUPLICATE = "duplicate"
    TO_REVIEW = "to_review"


class RuoloTributiPaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    OVERPAID = "overpaid"
    TO_REVIEW = "to_review"


class RuoloTributiWorkflowStatus(StrEnum):
    MOROSO = "moroso"
    CONTESTATO = "contestato"
    SOSPESO = "sospeso"
    ANNULLATO = "annullato"
    NON_DOVUTO = "non_dovuto"
    RATEIZZATO = "rateizzato"


class RuoloTributiReminderStatus(StrEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    DISCARDED = "discarded"


class RuoloTributiRegisteredMailMatchStatus(StrEnum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    UNMATCHED = "unmatched"
    TO_REVIEW = "to_review"


class RuoloTributiRegisteredMailRecoveryStatus(StrEnum):
    PENDING = "pending"
    READY_ON_PAYMENT = "ready_on_payment"
    RECOVERED = "recovered"
    NOT_RECOVERABLE = "not_recoverable"
