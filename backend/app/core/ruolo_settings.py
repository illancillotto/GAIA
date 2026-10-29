from pathlib import Path

from pydantic import Field

from app.core.td896_settings import Td896Settings

REPO_ROOT = Path(__file__).resolve().parents[3]


class RuoloSettings(Td896Settings):
    """Generated reminder PDFs outside the utenza NAS folder; /runtime-data survives container rebuilds."""

    ruolo_reminder_storage_path: str = Field(
        default=str(REPO_ROOT / "runtime-data" / "ruolo" / "solleciti"),
        alias="RUOLO_REMINDER_STORAGE_PATH",
    )
