from pydantic import Field

from app.core.ruolo_settings import RuoloSettings


class RuoliExportSettings(RuoloSettings):
    """Weekly export of the Capacitas ruoli grids (inCASS, inBOLLETTINI) to Google Drive."""

    capacitas_ruoli_export_enabled: bool = Field(
        default=False, alias="CAPACITAS_RUOLI_EXPORT_ENABLED"
    )
    capacitas_ruoli_export_credential_id: int | None = Field(
        default=None, alias="CAPACITAS_RUOLI_EXPORT_CREDENTIAL_ID"
    )
    capacitas_ruoli_export_drive_folder_id: str = Field(
        default="1fHZcf2AHVXK7tuZiLPfSK7BwLkjenIn7", alias="CAPACITAS_RUOLI_EXPORT_DRIVE_FOLDER_ID"
    )
    # 0 = lunedi ... 6 = domenica, ora locale nel fuso indicato.
    capacitas_ruoli_export_weekday: int = Field(
        default=6, ge=0, le=6, alias="CAPACITAS_RUOLI_EXPORT_WEEKDAY"
    )
    capacitas_ruoli_export_hour: int = Field(
        default=7, ge=0, le=23, alias="CAPACITAS_RUOLI_EXPORT_HOUR"
    )
    capacitas_ruoli_export_timezone: str = Field(
        default="Europe/Rome", alias="CAPACITAS_RUOLI_EXPORT_TIMEZONE"
    )
    capacitas_ruoli_export_state_path: str = Field(
        default="/runtime-data/ruoli-export", alias="CAPACITAS_RUOLI_EXPORT_STATE_PATH"
    )
    capacitas_ruoli_export_max_attempts: int = Field(
        default=3, ge=1, le=10, alias="CAPACITAS_RUOLI_EXPORT_MAX_ATTEMPTS"
    )
    capacitas_ruoli_export_retry_base_seconds: float = Field(
        default=30.0, ge=0, le=3600, alias="CAPACITAS_RUOLI_EXPORT_RETRY_BASE_SECONDS"
    )
    capacitas_ruoli_export_progress_timeout_seconds: int = Field(
        default=1800, ge=30, le=21600, alias="CAPACITAS_RUOLI_EXPORT_PROGRESS_TIMEOUT_SECONDS"
    )
    # Refresh token of the Drive folder owner (scripts/google_drive_authorize.py);
    # empty client id/secret fall back to GOOGLE_OAUTH_CLIENT_ID/SECRET.
    google_drive_client_id: str = Field(default="", alias="GOOGLE_DRIVE_CLIENT_ID")
    google_drive_client_secret: str = Field(default="", alias="GOOGLE_DRIVE_CLIENT_SECRET")
    google_drive_refresh_token: str = Field(default="", alias="GOOGLE_DRIVE_REFRESH_TOKEN")
