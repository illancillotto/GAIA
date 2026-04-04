from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "NAS Access Audit Platform"
    app_version: str = "0.1.0"
    app_env: str = "development"

    database_url: str = Field(
        default="postgresql+psycopg://naap_app:change_me@postgres:5432/naap",
        alias="DATABASE_URL",
    )

    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    backend_cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        alias="BACKEND_CORS_ORIGINS",
    )
    credential_master_key: str | None = Field(default=None, alias="CREDENTIAL_MASTER_KEY")
    catasto_document_storage_path: str = Field(
        default="/data/catasto/documents",
        alias="CATASTO_DOCUMENT_STORAGE_PATH",
    )
    catasto_captcha_storage_path: str = Field(
        default="/data/catasto/captcha",
        alias="CATASTO_CAPTCHA_STORAGE_PATH",
    )
    catasto_websocket_poll_seconds: int = Field(
        default=2,
        alias="CATASTO_WEBSOCKET_POLL_SECONDS",
    )
    catasto_sister_probe_timeout_seconds: int = Field(
        default=15,
        alias="CATASTO_SISTER_PROBE_TIMEOUT_SECONDS",
    )
    capacitas_debug_storage_path: str = Field(
        default="/data/elaborazioni/capacitas-debug",
        alias="CAPACITAS_DEBUG_STORAGE_PATH",
    )
    jwt_secret_key: str = Field(default="change_this_secret", alias="JWT_SECRET_KEY")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")
    jwt_algorithm: str = "HS256"
    nas_host: str = Field(default="nas.internal.local", alias="NAS_HOST")
    nas_port: int = Field(default=22, alias="NAS_PORT")
    nas_username: str = Field(default="svc_naap", alias="NAS_USERNAME")
    nas_password: str = Field(default="change_me", alias="NAS_PASSWORD")
    nas_private_key_path: str | None = Field(default=None, alias="NAS_PRIVATE_KEY_PATH")
    nas_timeout: int = Field(default=10, alias="NAS_TIMEOUT")
    anagrafica_nas_archive_root: str = Field(
        default="/volume1/settore catasto/ARCHIVIO",
        alias="ANAGRAFICA_NAS_ARCHIVE_ROOT",
    )
    utenze_nas_archive_root: str | None = Field(
        default=None,
        alias="UTENZE_NAS_ARCHIVE_ROOT",
    )
    anagrafica_document_storage_path: str = Field(
        default="/data/anagrafica/documents",
        alias="ANAGRAFICA_DOCUMENT_STORAGE_PATH",
    )
    utenze_document_storage_path: str | None = Field(
        default=None,
        alias="UTENZE_DOCUMENT_STORAGE_PATH",
    )
    nas_passwd_command: str = Field(default="getent passwd", alias="NAS_PASSWD_COMMAND")
    nas_group_command: str = Field(default="getent group", alias="NAS_GROUP_COMMAND")
    nas_shares_command: str = Field(default="ls /volume1", alias="NAS_SHARES_COMMAND")
    nas_share_subpaths_command: str = Field(
        default="find /volume1/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -maxdepth 2 -type d -print 2>/dev/null || true",
        alias="NAS_SHARE_SUBPATHS_COMMAND",
    )
    nas_share_subpaths_full_command: str = Field(
        default="find /volume1/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true",
        alias="NAS_SHARE_SUBPATHS_FULL_COMMAND",
    )
    nas_acl_command_template: str = Field(
        default="synoacltool -get /volume1/{share}",
        alias="NAS_ACL_COMMAND_TEMPLATE",
    )
    sync_live_max_attempts: int = Field(default=3, alias="SYNC_LIVE_MAX_ATTEMPTS")
    sync_live_retry_delay_seconds: int = Field(default=2, alias="SYNC_LIVE_RETRY_DELAY_SECONDS")
    sync_live_backoff_mode: str = Field(default="fixed", alias="SYNC_LIVE_BACKOFF_MODE")
    sync_live_backoff_multiplier: float = Field(default=2.0, alias="SYNC_LIVE_BACKOFF_MULTIPLIER")
    sync_live_backoff_max_delay_seconds: int = Field(
        default=30,
        alias="SYNC_LIVE_BACKOFF_MAX_DELAY_SECONDS",
    )
    sync_live_backoff_jitter_enabled: bool = Field(
        default=False,
        alias="SYNC_LIVE_BACKOFF_JITTER_ENABLED",
    )
    sync_live_backoff_jitter_ratio: float = Field(
        default=0.2,
        alias="SYNC_LIVE_BACKOFF_JITTER_RATIO",
    )
    sync_schedule_enabled: bool = Field(default=False, alias="SYNC_SCHEDULE_ENABLED")
    sync_schedule_interval_seconds: int = Field(default=900, alias="SYNC_SCHEDULE_INTERVAL_SECONDS")
    sync_schedule_max_cycles: int = Field(default=0, alias="SYNC_SCHEDULE_MAX_CYCLES")
    network_range: str = Field(default="192.168.1.0/24", alias="NETWORK_RANGE")
    network_scan_enabled: bool = Field(default=False, alias="NETWORK_SCAN_ENABLED")
    network_scan_interval_seconds: int = Field(default=900, alias="NETWORK_SCAN_INTERVAL_SECONDS")
    network_scan_ping_timeout_ms: int = Field(default=1000, alias="NETWORK_SCAN_PING_TIMEOUT_MS")
    network_scan_ports: str = Field(default="22,80,161,443,445,3389", alias="NETWORK_SCAN_PORTS")
    network_enrichment_timeout_seconds: float = Field(default=1.0, alias="NETWORK_ENRICHMENT_TIMEOUT_SECONDS")
    network_missing_device_alert_days: int = Field(default=15, alias="NETWORK_MISSING_DEVICE_ALERT_DAYS")
    network_snmp_communities: str = Field(default="public", alias="NETWORK_SNMP_COMMUNITIES")
    network_snmp_community_profiles: str = Field(default="[]", alias="NETWORK_SNMP_COMMUNITY_PROFILES")
    network_arp_helper_base_url: str | None = Field(default=None, alias="NETWORK_ARP_HELPER_BASE_URL")
    network_gateway_arp_host: str | None = Field(default=None, alias="NETWORK_GATEWAY_ARP_HOST")
    network_gateway_arp_port: int = Field(default=22, alias="NETWORK_GATEWAY_ARP_PORT")
    network_gateway_arp_username: str | None = Field(default=None, alias="NETWORK_GATEWAY_ARP_USERNAME")
    network_gateway_arp_password: str | None = Field(default=None, alias="NETWORK_GATEWAY_ARP_PASSWORD")
    network_gateway_arp_private_key_path: str | None = Field(default=None, alias="NETWORK_GATEWAY_ARP_PRIVATE_KEY_PATH")
    network_gateway_arp_command: str = Field(
        default="ip neigh show {ip}",
        alias="NETWORK_GATEWAY_ARP_COMMAND",
    )
    bootstrap_admin_username: str = Field(default="admin", alias="BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_email: str = Field(default="admin@example.local", alias="BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_password: str = Field(default="change_me_admin", alias="BOOTSTRAP_ADMIN_PASSWORD")

    anagrafica_delete_password: str | None = Field(default=None, alias="ANAGRAFICA_DELETE_PASSWORD")
    utenze_delete_password: str | None = Field(default=None, alias="UTENZE_DELETE_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
