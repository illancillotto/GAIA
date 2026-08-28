from pydantic import Field

from app.core.storage_settings import StorageSettings


class GisSettings(StorageSettings):
    gis_export_scheduler_enabled: bool = Field(
        default=False,
        alias="GIS_EXPORT_SCHEDULER_ENABLED",
    )
    gis_export_scheduler_register_in_api: bool = Field(
        default=True,
        alias="GIS_EXPORT_SCHEDULER_REGISTER_IN_API",
    )
    gis_export_scheduler_cron: str = Field(
        default="30 2 * * *",
        alias="GIS_EXPORT_SCHEDULER_CRON",
    )
    gis_export_scheduler_timezone: str = Field(
        default="Europe/Rome",
        alias="GIS_EXPORT_SCHEDULER_TIMEZONE",
    )
    gis_export_retention_count: int = Field(
        default=5,
        alias="GIS_EXPORT_RETENTION_COUNT",
    )
    gis_export_max_layers_per_run: int = Field(
        default=50,
        alias="GIS_EXPORT_MAX_LAYERS_PER_RUN",
    )
    gis_martin_health_url: str = Field(
        default="http://martin:3000/catalog",
        alias="GIS_MARTIN_HEALTH_URL",
    )
    gis_qgis_server_health_url: str | None = Field(
        default=None,
        alias="GIS_QGIS_SERVER_HEALTH_URL",
    )
    gis_qgis_server_db_username: str = Field(
        default="gaia_gis_qgis_server",
        alias="GIS_QGIS_SERVER_DB_USERNAME",
    )
    gis_qgis_server_db_password: str = Field(
        default="",
        alias="GIS_QGIS_SERVER_DB_PASSWORD",
    )
    gis_qgis_server_project_dir: str = Field(
        default="/srv/qgis",
        alias="GIS_QGIS_SERVER_PROJECT_DIR",
    )
    gis_nas_health_path: str = Field(
        default="/volume1/Settore Catasto/ARCHIVIO/Backups/GAIA/gis",
        alias="GIS_NAS_HEALTH_PATH",
    )
    gis_nas_transport: str = Field(
        default="local",
        alias="GIS_NAS_TRANSPORT",
    )
    gis_runtime_health_timeout_seconds: float = Field(
        default=2.0,
        alias="GIS_RUNTIME_HEALTH_TIMEOUT_SECONDS",
    )
