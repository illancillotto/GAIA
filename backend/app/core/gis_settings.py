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
    gis_qgis_server_internal_url: str = Field(
        default="http://qgis-server/ows/",
        alias="GIS_QGIS_SERVER_INTERNAL_URL",
    )
    gis_qgis_server_timeout_seconds: float = Field(
        default=12.0,
        gt=0,
        alias="GIS_QGIS_SERVER_TIMEOUT_SECONDS",
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
    gis_external_layers_enabled: bool = Field(
        default=False,
        alias="GIS_EXTERNAL_LAYERS_ENABLED",
    )
    gis_external_cache_dir: str = Field(
        default="/data/gis/external-cache",
        alias="GIS_EXTERNAL_CACHE_DIR",
    )
    gis_external_cache_max_mb: int = Field(
        default=2048,
        ge=1,
        alias="GIS_EXTERNAL_CACHE_MAX_MB",
    )
    gis_external_default_timeout_seconds: float = Field(
        default=12.0,
        gt=0,
        alias="GIS_EXTERNAL_DEFAULT_TIMEOUT_SECONDS",
    )
    gis_external_ras_vector_url: str = Field(
        default="https://webgis.regione.sardegna.it/geoserver/ows",
        alias="GIS_EXTERNAL_RAS_VECTOR_URL",
    )
    gis_external_ras_raster_url: str = Field(
        default="https://webgis.regione.sardegna.it/geoserverraster/ows",
        alias="GIS_EXTERNAL_RAS_RASTER_URL",
    )
    gis_external_ade_wms_url: str = Field(
        default="https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php",
        alias="GIS_EXTERNAL_ADE_WMS_URL",
    )
    gis_qgis_proxy_base_url: str = Field(
        default="http://localhost:8000",
        alias="GIS_QGIS_PROXY_BASE_URL",
    )
    gis_interrogazione_enabled: bool = Field(
        default=False,
        alias="GIS_INTERROGAZIONE_ENABLED",
    )
    gis_interrogazione_remote_timeout_seconds: float = Field(
        default=8.0,
        gt=0,
        alias="GIS_INTERROGAZIONE_REMOTE_TIMEOUT_SECONDS",
    )
    gis_interrogazione_default_radius_m: float = Field(
        default=150.0,
        gt=0,
        alias="GIS_INTERROGAZIONE_DEFAULT_RADIUS_M",
    )
    gis_interrogazione_max_remote_layers: int = Field(
        default=12,
        ge=1,
        alias="GIS_INTERROGAZIONE_MAX_REMOTE_LAYERS",
    )
    gis_scheda_artifact_root: str = Field(
        default="/data/gis/schede-territoriali",
        alias="GIS_SCHEDA_ARTIFACT_ROOT",
    )
    gis_scheda_retention_count: int = Field(
        default=20,
        ge=1,
        alias="GIS_SCHEDA_RETENTION_COUNT",
    )
