from pydantic import Field

from app.core.gis_settings import GisSettings


class CapacitasAutoSyncSettings(GisSettings):
    capacitas_request_policy_path: str = Field(
        default="/runtime-data/capacitas/request-policy.json", alias="CAPACITAS_REQUEST_POLICY_PATH"
    )
    capacitas_request_interval_seconds: float = Field(
        default=3.0, ge=1, le=60, alias="CAPACITAS_REQUEST_INTERVAL_SECONDS"
    )
    capacitas_request_cooldown_seconds: float = Field(
        default=60.0, ge=30, le=900, alias="CAPACITAS_REQUEST_COOLDOWN_SECONDS"
    )
    capacitas_request_max_cooldown_seconds: float = Field(
        default=900.0, ge=900, le=3600, alias="CAPACITAS_REQUEST_MAX_COOLDOWN_SECONDS"
    )
    capacitas_domande_irrigue_autosync_enabled: bool = Field(
        default=False,
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_ENABLED",
    )
    capacitas_domande_irrigue_autosync_interval_minutes: int = Field(
        default=10,
        ge=1,
        le=1440,
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_INTERVAL_MINUTES",
    )
    capacitas_domande_irrigue_autosync_credential_id: int | None = Field(
        default=None,
        ge=1,
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_CREDENTIAL_ID",
    )
    capacitas_domande_irrigue_autosync_chunk_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_CHUNK_SIZE",
    )
    capacitas_domande_irrigue_autosync_window_enabled: bool = Field(
        default=True,
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_WINDOW_ENABLED",
    )
    capacitas_domande_irrigue_autosync_windows: str = Field(
        default="",
        pattern=r"^(?:|(?:[01][0-9]|2[0-3]):[0-5][0-9]-(?:[01][0-9]|2[0-3]):[0-5][0-9](?:,(?:[01][0-9]|2[0-3]):[0-5][0-9]-(?:[01][0-9]|2[0-3]):[0-5][0-9])*)$",
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_WINDOWS",
    )
    capacitas_domande_irrigue_autosync_start_hour: int = Field(
        default=20,
        ge=0,
        le=23,
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_START_HOUR",
    )
    capacitas_domande_irrigue_autosync_end_hour: int = Field(
        default=6,
        ge=0,
        le=23,
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_END_HOUR",
    )
    capacitas_domande_irrigue_autosync_timezone: str = Field(
        default="Europe/Rome",
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_TIMEZONE",
    )
    capacitas_domande_irrigue_autosync_include_details: bool = Field(
        default=True,
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_INCLUDE_DETAILS",
    )
    capacitas_domande_irrigue_autosync_throttle_ms: int = Field(
        default=250,
        ge=0,
        le=5000,
        alias="CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_THROTTLE_MS",
    )
