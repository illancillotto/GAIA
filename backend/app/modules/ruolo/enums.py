from __future__ import annotations

from enum import Enum

try:
    from enum import StrEnum
except ImportError:
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
