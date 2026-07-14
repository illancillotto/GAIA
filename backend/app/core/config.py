from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT_ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    project_name: str = "GAIA"
    app_version: str = "0.1.0"
    app_env: str = "development"

    database_url: str = Field(alias="DATABASE_URL")

    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    frontend_public_url: str = Field(default="http://localhost:3000", alias="FRONTEND_PUBLIC_URL")
    backend_cors_origins: str = Field(
        default=(
            "http://localhost:3000,"
            "http://localhost:8080,"
            "http://gaia.local,"
            "http://gaia.local:8080,"
            "http://gaia.lan,"
            "http://gaia.lan:8080"
        ),
        alias="BACKEND_CORS_ORIGINS",
    )
    credential_master_key: str | None = Field(default=None, alias="CREDENTIAL_MASTER_KEY")
    catasto_document_storage_path: str = Field(
        default="/data/catasto/documents",
        validation_alias=AliasChoices("ELABORAZIONI_DOCUMENT_STORAGE_PATH", "CATASTO_DOCUMENT_STORAGE_PATH"),
    )
    catasto_captcha_storage_path: str = Field(
        default="/data/catasto/captcha",
        validation_alias=AliasChoices("ELABORAZIONI_CAPTCHA_STORAGE_PATH", "CATASTO_CAPTCHA_STORAGE_PATH"),
    )
    catasto_websocket_poll_seconds: int = Field(
        default=2,
        validation_alias=AliasChoices("ELABORAZIONI_WEBSOCKET_POLL_SECONDS", "CATASTO_WEBSOCKET_POLL_SECONDS"),
    )
    catasto_ade_autosync_enabled: bool = Field(default=False, alias="CATASTO_ADE_AUTOSYNC_ENABLED")
    catasto_ade_autosync_cron: str = Field(default="15 3 * * *", alias="CATASTO_ADE_AUTOSYNC_CRON")
    catasto_ade_autosync_timezone: str = Field(default="Europe/Rome", alias="CATASTO_ADE_AUTOSYNC_TIMEZONE")
    catasto_ade_autosync_min_lon: float | None = Field(default=None, alias="CATASTO_ADE_AUTOSYNC_MIN_LON")
    catasto_ade_autosync_min_lat: float | None = Field(default=None, alias="CATASTO_ADE_AUTOSYNC_MIN_LAT")
    catasto_ade_autosync_max_lon: float | None = Field(default=None, alias="CATASTO_ADE_AUTOSYNC_MAX_LON")
    catasto_ade_autosync_max_lat: float | None = Field(default=None, alias="CATASTO_ADE_AUTOSYNC_MAX_LAT")
    catasto_ade_autosync_max_tile_km2: float = Field(default=4.0, alias="CATASTO_ADE_AUTOSYNC_MAX_TILE_KM2")
    catasto_ade_autosync_max_tiles: int = Field(default=400, alias="CATASTO_ADE_AUTOSYNC_MAX_TILES")
    catasto_ade_autosync_count: int = Field(default=1000, alias="CATASTO_ADE_AUTOSYNC_COUNT")
    catasto_ade_autosync_max_pages_per_tile: int = Field(
        default=20,
        alias="CATASTO_ADE_AUTOSYNC_MAX_PAGES_PER_TILE",
    )
    catasto_ade_autosync_geometry_threshold_m: float = Field(
        default=1.0,
        alias="CATASTO_ADE_AUTOSYNC_GEOMETRY_THRESHOLD_M",
    )
    catasto_ade_autosync_categories: str = Field(
        default="nuove_in_ade,geometrie_variate",
        alias="CATASTO_ADE_AUTOSYNC_CATEGORIES",
    )
    catasto_ade_autosync_allow_suppress_missing: bool = Field(
        default=False,
        alias="CATASTO_ADE_AUTOSYNC_ALLOW_SUPPRESS_MISSING",
    )
    elaborazioni_pending_start_timeout_minutes: int = Field(
        default=25,
        alias="ELABORAZIONI_PENDING_START_TIMEOUT_MINUTES",
    )
    elaborazioni_operation_window_enabled: bool = Field(
        default=False,
        alias="ELABORAZIONI_OPERATION_WINDOW_ENABLED",
    )
    elaborazioni_operation_start_hour: int = Field(
        default=0,
        alias="ELABORAZIONI_OPERATION_START_HOUR",
    )
    elaborazioni_operation_end_hour: int = Field(
        default=23,
        alias="ELABORAZIONI_OPERATION_END_HOUR",
    )
    elaborazioni_operation_timezone: str = Field(
        default="Europe/Rome",
        alias="ELABORAZIONI_OPERATION_TIMEZONE",
    )
    catasto_sister_probe_timeout_seconds: int = Field(
        default=15,
        validation_alias=AliasChoices("ELABORAZIONI_SISTER_PROBE_TIMEOUT_SECONDS", "CATASTO_SISTER_PROBE_TIMEOUT_SECONDS"),
    )
    capacitas_debug_storage_path: str = Field(
        default="/data/elaborazioni/capacitas-debug",
        alias="CAPACITAS_DEBUG_STORAGE_PATH",
    )
    capacitas_cod_cons: str = Field(
        default="090",
        alias="CAPACITAS_COD_CONS",
    )
    bonifica_oristanese_debug_storage_path: str = Field(
        default="/data/elaborazioni/bonifica-oristanese-debug",
        alias="BONIFICA_ORISTANESE_DEBUG_STORAGE_PATH",
    )
    wc_sync_default_days: int = Field(
        default=30,
        alias="WC_SYNC_DEFAULT_DAYS",
    )
    wc_sync_request_delay_ms: int = Field(
        default=100,
        alias="WC_SYNC_REQUEST_DELAY_MS",
    )
    wc_sync_detail_delay_ms: int = Field(
        default=25,
        alias="WC_SYNC_DETAIL_DELAY_MS",
    )
    wc_sync_stale_job_minutes: int = Field(
        default=30,
        alias="WC_SYNC_STALE_JOB_MINUTES",
    )
    wc_sync_user_stale_job_minutes: int = Field(
        default=360,
        alias="WC_SYNC_USER_STALE_JOB_MINUTES",
    )
    wc_sync_user_detail_concurrency: int = Field(
        default=16,
        alias="WC_SYNC_USER_DETAIL_CONCURRENCY",
    )
    wc_sync_users_role_ids: str = Field(
        default="30,29,44,45,51,10,11,2,43,6,48,40,46,47,49,50,41",
        alias="WC_SYNC_USERS_ROLE_IDS",
    )
    wc_sync_consorziati_role_id: str = Field(
        default="3",
        alias="WC_SYNC_CONSORZIATI_ROLE_ID",
    )
    wc_sync_daily_enabled: bool = Field(
        default=False,
        alias="WC_SYNC_DAILY_ENABLED",
    )
    wc_sync_daily_cron: str = Field(
        default="0 2 * * *",
        alias="WC_SYNC_DAILY_CRON",
    )
    wc_sync_daily_timezone: str = Field(
        default="Europe/Rome",
        alias="WC_SYNC_DAILY_TIMEZONE",
    )
    wc_sync_daily_lookback_days: int = Field(
        default=1,
        alias="WC_SYNC_DAILY_LOOKBACK_DAYS",
    )
    wc_sync_operazioni_live_enabled: bool = Field(
        default=True,
        alias="WC_SYNC_OPERAZIONI_LIVE_ENABLED",
    )
    wc_sync_operazioni_live_interval_seconds: int = Field(
        default=600,
        alias="WC_SYNC_OPERAZIONI_LIVE_INTERVAL_SECONDS",
    )
    wc_sync_operazioni_live_lookback_days: int = Field(
        default=1,
        alias="WC_SYNC_OPERAZIONI_LIVE_LOOKBACK_DAYS",
    )
    elaborazioni_db_backup_enabled: bool = Field(
        default=True,
        alias="ELABORAZIONI_DB_BACKUP_ENABLED",
    )
    elaborazioni_db_backup_cron: str = Field(
        default="5 2 * * *",
        alias="ELABORAZIONI_DB_BACKUP_CRON",
    )
    elaborazioni_db_backup_timezone: str = Field(
        default="Europe/Rome",
        alias="ELABORAZIONI_DB_BACKUP_TIMEZONE",
    )
    elaborazioni_db_backup_retention_count: int = Field(
        default=5,
        alias="ELABORAZIONI_DB_BACKUP_RETENTION_COUNT",
    )
    elaborazioni_db_backup_local_dir: str = Field(
        default="/tmp/gaia-db-backups",
        alias="ELABORAZIONI_DB_BACKUP_LOCAL_DIR",
    )
    elaborazioni_db_backup_remote_root: str = Field(
        default="/volume1/Backups/GAIA/db",
        alias="ELABORAZIONI_DB_BACKUP_REMOTE_ROOT",
    )
    elaborazioni_db_backup_encryption_enabled: bool = Field(
        default=False,
        alias="ELABORAZIONI_DB_BACKUP_ENCRYPTION_ENABLED",
    )
    elaborazioni_db_backup_encryption_passphrase: str = Field(
        default="",
        alias="ELABORAZIONI_DB_BACKUP_ENCRYPTION_PASSPHRASE",
    )
    gis_export_scheduler_enabled: bool = Field(
        default=False,
        alias="GIS_EXPORT_SCHEDULER_ENABLED",
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
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_expire_minutes: int = Field(default=90, alias="JWT_EXPIRE_MINUTES")
    jwt_algorithm: str = "HS256"
    user_invite_expire_hours: int = Field(default=72, alias="USER_INVITE_EXPIRE_HOURS")
    smtp_enabled: bool = Field(default=False, alias="SMTP_ENABLED")
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="", alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="GAIA CED", alias="SMTP_FROM_NAME")
    google_oauth_enabled: bool = Field(default=False, alias="GOOGLE_OAUTH_ENABLED")
    google_oauth_client_id: str = Field(default="", alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str = Field(default="", alias="GOOGLE_OAUTH_CLIENT_SECRET")
    google_oauth_redirect_uri: str = Field(default="", alias="GOOGLE_OAUTH_REDIRECT_URI")
    google_oauth_scopes: str = Field(default="openid email profile", alias="GOOGLE_OAUTH_SCOPES")
    google_oauth_authorize_url: str = Field(
        default="https://accounts.google.com/o/oauth2/v2/auth",
        alias="GOOGLE_OAUTH_AUTHORIZE_URL",
    )
    google_oauth_token_url: str = Field(
        default="https://oauth2.googleapis.com/token",
        alias="GOOGLE_OAUTH_TOKEN_URL",
    )
    google_oauth_userinfo_url: str = Field(
        default="https://openidconnect.googleapis.com/v1/userinfo",
        alias="GOOGLE_OAUTH_USERINFO_URL",
    )
    mobile_connector_token: str = Field(default="", alias="MOBILE_CONNECTOR_TOKEN")
    mobile_connector_header_name: str = Field(default="X-GAIA-Connector-Token", alias="MOBILE_CONNECTOR_HEADER_NAME")
    gate_mobile_gateway_base_url: str = Field(default="", alias="GATE_MOBILE_GATEWAY_BASE_URL")
    gate_mobile_connector_token: str = Field(default="", alias="GATE_MOBILE_CONNECTOR_TOKEN")
    gate_mobile_sync_enabled: bool = Field(default=False, alias="GATE_MOBILE_SYNC_ENABLED")
    gate_mobile_sync_timeout_seconds: float = Field(default=20.0, alias="GATE_MOBILE_SYNC_TIMEOUT_SECONDS")
    pdnd_client_id: str = Field(default="", alias="PDND_CLIENT_ID")
    pdnd_kid: str = Field(default="", alias="PDND_KID")
    pdnd_private_key_path: str = Field(default="", alias="PDND_PRIVATE_KEY_PATH")
    pdnd_private_key_pem: str = Field(default="", alias="PDND_PRIVATE_KEY_PEM")
    pdnd_auth_url: str = Field(default="https://auth.interop.pagopa.it/token.oauth2", alias="PDND_AUTH_URL")
    pdnd_client_assertion_audience: str = Field(default="", alias="PDND_CLIENT_ASSERTION_AUDIENCE")
    pdnd_audience: str = Field(default="https://interop.pagopa.it/", alias="PDND_AUDIENCE")
    anpr_base_url: str = Field(
        default="https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND",
        alias="ANPR_BASE_URL",
    )
    anpr_ca_bundle_path: str = Field(default="", alias="ANPR_CA_BUNDLE_PATH")
    anpr_ssl_verify: bool = Field(default=True, alias="ANPR_SSL_VERIFY")
    anpr_daily_call_hard_limit: int = Field(default=90, alias="ANPR_DAILY_CALL_HARD_LIMIT")
    anpr_job_batch_size: int = Field(default=10, alias="ANPR_JOB_BATCH_SIZE")
    anpr_job_start_hour: int = Field(default=8, alias="ANPR_JOB_START_HOUR")
    anpr_job_end_hour: int = Field(default=18, alias="ANPR_JOB_END_HOUR")
    anpr_job_timezone: str = Field(default="Europe/Rome", alias="ANPR_JOB_TIMEZONE")
    anpr_job_ruolo_year: int | None = Field(default=None, alias="ANPR_JOB_RUOLO_YEAR")
    pdnd_fruitore_user_id: str = Field(default="GAIA-CBO", alias="PDND_FRUITORE_USER_ID")
    pdnd_fruitore_user_location: str = Field(default="GAIA-SRV", alias="PDND_FRUITORE_USER_LOCATION")
    pdnd_loa: str = Field(default="LOW", alias="PDND_LOA")
    purpose_id_c030: str = Field(default="", alias="PURPOSE_ID_C030")
    purpose_id_c004: str = Field(default="", alias="PURPOSE_ID_C004")
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
    visure_nas_router_enabled: bool = Field(default=False, alias="VISURE_NAS_ROUTER_ENABLED")
    visure_nas_router_cron: str = Field(default="15 */2 * * *", alias="VISURE_NAS_ROUTER_CRON")
    visure_nas_router_timezone: str = Field(default="Europe/Rome", alias="VISURE_NAS_ROUTER_TIMEZONE")
    visure_nas_inbox_path: str | None = Field(default=None, alias="VISURE_NAS_INBOX_PATH")
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
    sync_live_worker_artifacts_path: str = Field(
        default="/data/sync/live-jobs",
        alias="SYNC_LIVE_WORKER_ARTIFACTS_PATH",
    )
    sync_live_pending_timeout_minutes: int = Field(
        default=10,
        alias="SYNC_LIVE_PENDING_TIMEOUT_MINUTES",
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
    network_telemetry_rollup_enabled: bool = Field(default=True, alias="NETWORK_TELEMETRY_ROLLUP_ENABLED")
    network_telemetry_rollup_cron: str = Field(default="5 * * * *", alias="NETWORK_TELEMETRY_ROLLUP_CRON")
    network_telemetry_rollup_timezone: str = Field(default="UTC", alias="NETWORK_TELEMETRY_ROLLUP_TIMEZONE")
    network_telemetry_rollup_lookback_hours: int = Field(default=6, alias="NETWORK_TELEMETRY_ROLLUP_LOOKBACK_HOURS")
    network_firewall_raw_retention_days: int = Field(default=14, alias="NETWORK_FIREWALL_RAW_RETENTION_DAYS")
    network_missing_device_alert_days: int = Field(default=15, alias="NETWORK_MISSING_DEVICE_ALERT_DAYS")
    network_snmp_communities: str = Field(default="public", alias="NETWORK_SNMP_COMMUNITIES")
    network_snmp_community_profiles: str = Field(default="[]", alias="NETWORK_SNMP_COMMUNITY_PROFILES")
    network_arp_helper_base_url: str | None = Field(default=None, alias="NETWORK_ARP_HELPER_BASE_URL")
    network_gateway_arp_host: str | None = Field(default=None, alias="NETWORK_GATEWAY_ARP_HOST")
    network_gateway_arp_port: int = Field(default=22, alias="NETWORK_GATEWAY_ARP_PORT")
    network_gateway_arp_username: str | None = Field(default=None, alias="NETWORK_GATEWAY_ARP_USERNAME")
    network_gateway_arp_password: str | None = Field(default=None, alias="NETWORK_GATEWAY_ARP_PASSWORD")
    wiki_telemetry_schedule_enabled: bool = Field(default=False, alias="WIKI_TELEMETRY_SCHEDULE_ENABLED")
    codex_lb_url: str = Field(default="http://host.docker.internal:2455/v1", alias="CODEX_LB_URL")
    codex_lb_api_key: str = Field(default="sk-codex-lb-local", alias="CODEX_LB_API_KEY")
    presenze_export_template_path: str = Field(
        default="/opt/presenze-scraper/Giornaliere/Giornaliere_2026_803_1.xlsm",
        alias="PRESENZE_EXPORT_TEMPLATE_PATH",
    )
    wiki_chat_model: str = Field(default="gpt-5.5", alias="WIKI_CHAT_MODEL")
    wiki_top_k: int = Field(default=5, alias="WIKI_TOP_K")
    wiki_telemetry_schedule_cron: str = Field(default="30 3 * * *", alias="WIKI_TELEMETRY_SCHEDULE_CRON")
    wiki_telemetry_schedule_timezone: str = Field(default="Europe/Rome", alias="WIKI_TELEMETRY_SCHEDULE_TIMEZONE")
    wiki_telemetry_schedule_lookback_days: int = Field(default=35, alias="WIKI_TELEMETRY_SCHEDULE_LOOKBACK_DAYS")
    wiki_conversation_backfill_worker_enabled: bool = Field(default=True, alias="WIKI_CONVERSATION_BACKFILL_WORKER_ENABLED")
    wiki_conversation_backfill_poll_seconds: int = Field(default=15, alias="WIKI_CONVERSATION_BACKFILL_POLL_SECONDS")
    wiki_conversation_backfill_retention_days: int = Field(default=30, alias="WIKI_CONVERSATION_BACKFILL_RETENTION_DAYS")
    wiki_review_fallback_heavy_threshold: int = Field(default=2, alias="WIKI_REVIEW_FALLBACK_HEAVY_THRESHOLD")
    wiki_review_no_match_repeated_threshold: int = Field(default=2, alias="WIKI_REVIEW_NO_MATCH_REPEATED_THRESHOLD")
    wiki_review_high_latency_ms_threshold: int = Field(default=1000, alias="WIKI_REVIEW_HIGH_LATENCY_MS_THRESHOLD")
    wiki_audit_retention_days: int = Field(default=365, alias="WIKI_AUDIT_RETENTION_DAYS")
    wiki_request_artifacts_path: str = Field(
        default=str(REPO_ROOT / "runtime-data" / "wiki" / "request-artifacts"),
        alias="WIKI_REQUEST_ARTIFACTS_PATH",
    )
    wiki_telemetry_daily_retention_days: int = Field(default=365, alias="WIKI_TELEMETRY_DAILY_RETENTION_DAYS")
    wiki_telemetry_period_retention_days: int = Field(default=730, alias="WIKI_TELEMETRY_PERIOD_RETENTION_DAYS")
    network_gateway_arp_private_key_path: str | None = Field(default=None, alias="NETWORK_GATEWAY_ARP_PRIVATE_KEY_PATH")
    network_gateway_arp_command: str = Field(
        default="ip neigh show {ip}",
        alias="NETWORK_GATEWAY_ARP_COMMAND",
    )
    network_sophos_syslog_enabled: bool = Field(default=False, alias="NETWORK_SOPHOS_SYSLOG_ENABLED")
    network_sophos_syslog_bind_host: str = Field(default="0.0.0.0", alias="NETWORK_SOPHOS_SYSLOG_BIND_HOST")
    network_sophos_syslog_port: int = Field(default=5514, alias="NETWORK_SOPHOS_SYSLOG_PORT")
    network_sophos_syslog_worker_count: int = Field(default=4, alias="NETWORK_SOPHOS_SYSLOG_WORKER_COUNT")
    network_sophos_syslog_queue_size: int = Field(default=2000, alias="NETWORK_SOPHOS_SYSLOG_QUEUE_SIZE")
    network_sophos_firewall_default_name: str = Field(default="Sophos XGS87", alias="NETWORK_SOPHOS_FIREWALL_DEFAULT_NAME")
    network_sophos_firewall_management_ip: str | None = Field(default=None, alias="NETWORK_SOPHOS_FIREWALL_MANAGEMENT_IP")
    network_sophos_snmp_enabled: bool = Field(default=False, alias="NETWORK_SOPHOS_SNMP_ENABLED")
    network_sophos_snmp_host: str | None = Field(default=None, alias="NETWORK_SOPHOS_SNMP_HOST")
    network_sophos_snmp_port: int = Field(default=161, alias="NETWORK_SOPHOS_SNMP_PORT")
    network_sophos_snmp_community: str | None = Field(default=None, alias="NETWORK_SOPHOS_SNMP_COMMUNITY")
    network_sophos_snmp_interval_seconds: int = Field(default=300, alias="NETWORK_SOPHOS_SNMP_INTERVAL_SECONDS")
    network_sophos_snmp_custom_oids: str = Field(default="[]", alias="NETWORK_SOPHOS_SNMP_CUSTOM_OIDS")
    bootstrap_admin_username: str = Field(default="admin", alias="BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_email: str = Field(default="admin@example.local", alias="BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_password: str = Field(default="change_me_admin", alias="BOOTSTRAP_ADMIN_PASSWORD")
    presenze_scraper_project_path: str = Field(
        default="/opt/presenze-scraper",
        alias="PRESENZE_SCRAPER_PROJECT_PATH",
    )
    presenze_scraper_python_path: str = Field(
        default="/opt/presenze-scraper/.venv/bin/python",
        alias="PRESENZE_SCRAPER_PYTHON_PATH",
    )
    presenze_scraper_cdp_endpoint: str = Field(
        default="http://host.docker.internal:9224",
        alias="PRESENZE_SCRAPER_CDP_ENDPOINT",
    )
    presenze_sync_artifacts_path: str = Field(
        default=str(REPO_ROOT / "runtime-data" / "presenze" / "sync"),
        alias="PRESENZE_SYNC_ARTIFACTS_PATH",
    )
    presenze_worker_poll_seconds: float = Field(
        default=5.0,
        alias="PRESENZE_WORKER_POLL_SECONDS",
    )
    presenze_sync_max_attempts: int = Field(
        default=3,
        alias="PRESENZE_SYNC_MAX_ATTEMPTS",
    )
    presenze_auto_sync_cron: str = Field(
        default="0 6,12,18 * * *",
        alias="PRESENZE_AUTO_SYNC_CRON",
    )
    presenze_auto_sync_timezone: str = Field(
        default="Europe/Rome",
        alias="PRESENZE_AUTO_SYNC_TIMEZONE",
    )
    presenze_bank_hours_guidance_allow_derived_profile: bool = Field(
        default=False,
        alias="PRESENZE_BANK_HOURS_GUIDANCE_ALLOW_DERIVED_PROFILE",
    )
    presenze_bank_hours_guidance_include_overtime_day: bool = Field(
        default=True,
        alias="PRESENZE_BANK_HOURS_GUIDANCE_INCLUDE_OVERTIME_DAY",
    )
    presenze_bank_hours_guidance_include_overtime_night: bool = Field(
        default=True,
        alias="PRESENZE_BANK_HOURS_GUIDANCE_INCLUDE_OVERTIME_NIGHT",
    )
    presenze_bank_hours_guidance_include_overtime_festive: bool = Field(
        default=True,
        alias="PRESENZE_BANK_HOURS_GUIDANCE_INCLUDE_OVERTIME_FESTIVE",
    )
    presenze_bank_hours_guidance_include_overtime_festive_night: bool = Field(
        default=True,
        alias="PRESENZE_BANK_HOURS_GUIDANCE_INCLUDE_OVERTIME_FESTIVE_NIGHT",
    )
    presenze_bank_hours_guidance_min_suggested_minutes: int = Field(
        default=60,
        alias="PRESENZE_BANK_HOURS_GUIDANCE_MIN_SUGGESTED_MINUTES",
    )

    anagrafica_delete_password: str | None = Field(default=None, alias="ANAGRAFICA_DELETE_PASSWORD")
    utenze_delete_password: str | None = Field(default=None, alias="UTENZE_DELETE_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _validate_required_secrets(self) -> "Settings":
        if not self.database_url.strip():
            raise ValueError("DATABASE_URL must be set (it cannot be empty).")
        if "change_me" in self.database_url:
            raise ValueError(
                "DATABASE_URL contains a placeholder (change_me). Update your .env with the real DB password."
            )

        if not self.jwt_secret_key.strip():
            raise ValueError("JWT_SECRET_KEY must be set (it cannot be empty).")
        if self.jwt_secret_key in {"change_this_secret", "change_me"}:
            raise ValueError(
                "JWT_SECRET_KEY contains a placeholder. Generate a strong random secret and set it in .env."
            )
        return self

    @staticmethod
    def _parse_csv_tokens(raw_value: str) -> list[str]:
        return [token.strip() for token in raw_value.split(",") if token.strip()]

    @property
    def wc_sync_users_role_id_list(self) -> list[str]:
        return self._parse_csv_tokens(self.wc_sync_users_role_ids)

    @property
    def effective_mobile_connector_token(self) -> str:
        primary = self.mobile_connector_token.strip()
        if primary:
            return primary
        return self.gate_mobile_connector_token.strip()

    @property
    def wc_sync_consorziati_role_id_value(self) -> str:
        tokens = self._parse_csv_tokens(self.wc_sync_consorziati_role_id)
        return tokens[0] if tokens else "3"

    @property
    def catasto_ade_autosync_categories_list(self) -> list[str]:
        return self._parse_csv_tokens(self.catasto_ade_autosync_categories)

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
