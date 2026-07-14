from app.core.config import Settings


def test_settings_use_expected_defaults(monkeypatch) -> None:
    for env_name in [
        "APP_ENV",
        "BACKEND_PORT",
        "BACKEND_CORS_ORIGINS",
        "DATABASE_URL",
        "NAS_HOST",
        "NAS_PORT",
        "NAS_USERNAME",
        "NAS_TIMEOUT",
        "NAS_PASSWD_COMMAND",
        "NAS_GROUP_COMMAND",
        "NAS_SHARES_COMMAND",
        "NAS_SHARE_SUBPATHS_COMMAND",
        "NAS_SHARE_SUBPATHS_FULL_COMMAND",
        "NAS_ACL_COMMAND_TEMPLATE",
        "JWT_SECRET_KEY",
        "JWT_EXPIRE_MINUTES",
        "MOBILE_CONNECTOR_TOKEN",
        "MOBILE_CONNECTOR_HEADER_NAME",
        "GATE_MOBILE_GATEWAY_BASE_URL",
        "GATE_MOBILE_CONNECTOR_TOKEN",
        "GATE_MOBILE_SYNC_ENABLED",
        "GATE_MOBILE_SYNC_TIMEOUT_SECONDS",
        "PDND_CLIENT_ID",
        "PDND_KID",
        "PDND_PRIVATE_KEY_PATH",
        "PDND_PRIVATE_KEY_PEM",
        "PDND_AUTH_URL",
        "PDND_CLIENT_ASSERTION_AUDIENCE",
        "PDND_AUDIENCE",
        "ANPR_BASE_URL",
        "ANPR_CA_BUNDLE_PATH",
        "ANPR_SSL_VERIFY",
        "ANPR_DAILY_CALL_HARD_LIMIT",
        "ANPR_JOB_BATCH_SIZE",
        "ANPR_JOB_START_HOUR",
        "ANPR_JOB_END_HOUR",
        "ANPR_JOB_TIMEZONE",
        "ANPR_JOB_RUOLO_YEAR",
        "PDND_FRUITORE_USER_ID",
        "PDND_FRUITORE_USER_LOCATION",
        "PDND_LOA",
        "PURPOSE_ID_C030",
        "PURPOSE_ID_C004",
        "SYNC_LIVE_MAX_ATTEMPTS",
        "SYNC_LIVE_RETRY_DELAY_SECONDS",
        "SYNC_LIVE_BACKOFF_MODE",
        "SYNC_LIVE_BACKOFF_MULTIPLIER",
        "SYNC_LIVE_BACKOFF_MAX_DELAY_SECONDS",
        "SYNC_LIVE_BACKOFF_JITTER_ENABLED",
        "SYNC_LIVE_BACKOFF_JITTER_RATIO",
        "SYNC_SCHEDULE_ENABLED",
        "SYNC_SCHEDULE_INTERVAL_SECONDS",
        "SYNC_SCHEDULE_MAX_CYCLES",
        "BOOTSTRAP_ADMIN_USERNAME",
        "BOOTSTRAP_ADMIN_EMAIL",
        "WC_SYNC_DAILY_ENABLED",
        "WC_SYNC_DAILY_CRON",
        "WC_SYNC_DAILY_TIMEZONE",
        "WC_SYNC_DAILY_LOOKBACK_DAYS",
        "ELABORAZIONI_DB_BACKUP_ENABLED",
        "ELABORAZIONI_DB_BACKUP_CRON",
        "ELABORAZIONI_DB_BACKUP_TIMEZONE",
        "ELABORAZIONI_DB_BACKUP_RETENTION_COUNT",
        "ELABORAZIONI_DB_BACKUP_LOCAL_DIR",
        "ELABORAZIONI_DB_BACKUP_REMOTE_ROOT",
    ]:
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./config-defaults.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "config-defaults-secret")
    settings = Settings(_env_file=None)

    assert settings.project_name == "GAIA"
    assert settings.app_version == "0.1.0"
    assert settings.app_env == "development"
    assert settings.backend_host == "0.0.0.0"
    assert settings.backend_port == 8000
    assert settings.backend_cors_origins == (
        "http://localhost:3000,"
        "http://localhost:8080,"
        "http://gaia.local,"
        "http://gaia.local:8080,"
        "http://gaia.lan,"
        "http://gaia.lan:8080"
    )
    assert settings.jwt_secret_key == "config-defaults-secret"
    assert settings.jwt_expire_minutes == 90
    assert settings.jwt_algorithm == "HS256"
    assert settings.mobile_connector_token == ""
    assert settings.effective_mobile_connector_token == ""
    assert settings.mobile_connector_header_name == "X-GAIA-Connector-Token"
    assert settings.gate_mobile_gateway_base_url == ""
    assert settings.gate_mobile_connector_token == ""
    assert settings.gate_mobile_sync_enabled is False
    assert settings.gate_mobile_sync_timeout_seconds == 20.0
    assert settings.pdnd_client_id == ""
    assert settings.pdnd_kid == ""
    assert settings.pdnd_private_key_path == ""
    assert settings.pdnd_private_key_pem == ""
    assert settings.pdnd_auth_url == "https://auth.interop.pagopa.it/token.oauth2"
    assert settings.pdnd_client_assertion_audience == ""
    assert settings.pdnd_audience == "https://interop.pagopa.it/"
    assert settings.anpr_base_url == "https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND"
    assert settings.anpr_ca_bundle_path == ""
    assert settings.anpr_ssl_verify is True
    assert settings.anpr_daily_call_hard_limit == 90
    assert settings.anpr_job_batch_size == 10
    assert settings.anpr_job_start_hour == 8
    assert settings.anpr_job_end_hour == 18
    assert settings.anpr_job_timezone == "Europe/Rome"
    assert settings.anpr_job_ruolo_year is None
    assert settings.pdnd_fruitore_user_id == "GAIA-CBO"
    assert settings.pdnd_fruitore_user_location == "GAIA-SRV"
    assert settings.pdnd_loa == "LOW"
    assert settings.purpose_id_c030 == ""
    assert settings.purpose_id_c004 == ""
    assert settings.nas_host == "nas.internal.local"
    assert settings.nas_port == 22
    assert settings.nas_username == "svc_naap"
    assert settings.nas_timeout == 10
    assert settings.nas_passwd_command == "getent passwd"
    assert settings.nas_group_command == "getent group"
    assert settings.nas_shares_command == "ls /volume1"
    assert settings.nas_share_subpaths_command == "find /volume1/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -maxdepth 2 -type d -print 2>/dev/null || true"
    assert settings.nas_share_subpaths_full_command == "find /volume1/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true"
    assert settings.nas_acl_command_template == "synoacltool -get /volume1/{share}"
    assert settings.sync_live_max_attempts == 3
    assert settings.sync_live_retry_delay_seconds == 2
    assert settings.sync_live_backoff_mode == "fixed"
    assert settings.sync_live_backoff_multiplier == 2.0
    assert settings.sync_live_backoff_max_delay_seconds == 30
    assert settings.sync_live_backoff_jitter_enabled is False
    assert settings.sync_live_backoff_jitter_ratio == 0.2
    assert settings.sync_schedule_enabled is False
    assert settings.sync_schedule_interval_seconds == 900
    assert settings.sync_schedule_max_cycles == 0
    assert settings.bootstrap_admin_username == "admin"
    assert settings.bootstrap_admin_email == "admin@example.local"
    assert settings.wc_sync_daily_enabled is False
    assert settings.wc_sync_daily_cron == "0 2 * * *"
    assert settings.wc_sync_daily_timezone == "Europe/Rome"
    assert settings.wc_sync_daily_lookback_days == 1
    assert settings.elaborazioni_db_backup_enabled is True
    assert settings.elaborazioni_db_backup_cron == "5 2 * * *"
    assert settings.elaborazioni_db_backup_timezone == "Europe/Rome"
    assert settings.elaborazioni_db_backup_retention_count == 5
    assert settings.elaborazioni_db_backup_local_dir == "/tmp/gaia-db-backups"
    assert settings.elaborazioni_db_backup_remote_root == "/volume1/Backups/GAIA/db"
    assert settings.elaborazioni_db_backup_encryption_enabled is False
    assert settings.elaborazioni_db_backup_encryption_passphrase == ""
    assert settings.gis_export_scheduler_enabled is False
    assert settings.gis_export_scheduler_cron == "30 2 * * *"
    assert settings.gis_export_scheduler_timezone == "Europe/Rome"
    assert settings.gis_export_retention_count == 5
    assert settings.gis_export_max_layers_per_run == 50
    assert settings.database_url == "sqlite:///./config-defaults.db"


def test_settings_allow_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("BACKEND_PORT", "9010")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:8080,https://gaia.internal")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("MOBILE_CONNECTOR_TOKEN", "connector-secret")
    monkeypatch.setenv("MOBILE_CONNECTOR_HEADER_NAME", "X-Test-Connector")
    monkeypatch.setenv("GATE_MOBILE_GATEWAY_BASE_URL", "https://gateway.example.test")
    monkeypatch.setenv("GATE_MOBILE_CONNECTOR_TOKEN", "gate-token")
    monkeypatch.setenv("GATE_MOBILE_SYNC_ENABLED", "true")
    monkeypatch.setenv("GATE_MOBILE_SYNC_TIMEOUT_SECONDS", "8.5")
    monkeypatch.setenv("PDND_CLIENT_ID", "client-123")
    monkeypatch.setenv("PDND_KID", "kid-456")
    monkeypatch.setenv("PDND_PRIVATE_KEY_PATH", "/tmp/pdnd.pem")
    monkeypatch.setenv("PDND_PRIVATE_KEY_PEM", "pem-inline")
    monkeypatch.setenv("PDND_AUTH_URL", "https://auth.example.test/token")
    monkeypatch.setenv("PDND_CLIENT_ASSERTION_AUDIENCE", "auth.example.test/client-assertion")
    monkeypatch.setenv("PDND_AUDIENCE", "https://audience.example.test/")
    monkeypatch.setenv("ANPR_BASE_URL", "https://anpr.example.test")
    monkeypatch.setenv("ANPR_CA_BUNDLE_PATH", "/tmp/anpr-ca.pem")
    monkeypatch.setenv("ANPR_SSL_VERIFY", "false")
    monkeypatch.setenv("ANPR_DAILY_CALL_HARD_LIMIT", "45")
    monkeypatch.setenv("ANPR_JOB_BATCH_SIZE", "6")
    monkeypatch.setenv("ANPR_JOB_START_HOUR", "9")
    monkeypatch.setenv("ANPR_JOB_END_HOUR", "17")
    monkeypatch.setenv("ANPR_JOB_TIMEZONE", "UTC")
    monkeypatch.setenv("ANPR_JOB_RUOLO_YEAR", "2027")
    monkeypatch.setenv("PDND_FRUITORE_USER_ID", "GAIA-TEST")
    monkeypatch.setenv("PDND_FRUITORE_USER_LOCATION", "GAIA-TEST-SRV")
    monkeypatch.setenv("PDND_LOA", "HIGH")
    monkeypatch.setenv("PURPOSE_ID_C030", "purpose-c030")
    monkeypatch.setenv("PURPOSE_ID_C004", "purpose-c004")
    monkeypatch.setenv("NAS_HOST", "10.10.10.10")
    monkeypatch.setenv("NAS_TIMEOUT", "25")
    monkeypatch.setenv("NAS_SHARES_COMMAND", "ls /shares")
    monkeypatch.setenv("NAS_SHARE_SUBPATHS_COMMAND", "find /shares/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -maxdepth 2 -type d -print 2>/dev/null || true")
    monkeypatch.setenv("NAS_SHARE_SUBPATHS_FULL_COMMAND", "find /shares/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true")
    monkeypatch.setenv("SYNC_LIVE_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("SYNC_LIVE_BACKOFF_MODE", "exponential")
    monkeypatch.setenv("SYNC_LIVE_BACKOFF_MULTIPLIER", "3")
    monkeypatch.setenv("SYNC_LIVE_BACKOFF_JITTER_ENABLED", "true")
    monkeypatch.setenv("SYNC_LIVE_BACKOFF_JITTER_RATIO", "0.35")
    monkeypatch.setenv("SYNC_SCHEDULE_ENABLED", "true")
    monkeypatch.setenv("SYNC_SCHEDULE_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "adminseed")
    monkeypatch.setenv("WC_SYNC_DAILY_ENABLED", "true")
    monkeypatch.setenv("WC_SYNC_DAILY_CRON", "30 1 * * *")
    monkeypatch.setenv("WC_SYNC_DAILY_TIMEZONE", "UTC")
    monkeypatch.setenv("WC_SYNC_DAILY_LOOKBACK_DAYS", "2")
    monkeypatch.setenv("ELABORAZIONI_DB_BACKUP_ENABLED", "false")
    monkeypatch.setenv("ELABORAZIONI_DB_BACKUP_CRON", "15 2 * * *")
    monkeypatch.setenv("ELABORAZIONI_DB_BACKUP_TIMEZONE", "Europe/Rome")
    monkeypatch.setenv("ELABORAZIONI_DB_BACKUP_RETENTION_COUNT", "7")
    monkeypatch.setenv("ELABORAZIONI_DB_BACKUP_LOCAL_DIR", "/var/backups/gaia")
    monkeypatch.setenv("ELABORAZIONI_DB_BACKUP_REMOTE_ROOT", "/volume1/Backups/GAIA/prod-db")
    monkeypatch.setenv("ELABORAZIONI_DB_BACKUP_ENCRYPTION_ENABLED", "true")
    monkeypatch.setenv("ELABORAZIONI_DB_BACKUP_ENCRYPTION_PASSPHRASE", "backup-passphrase")
    monkeypatch.setenv("GIS_EXPORT_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("GIS_EXPORT_SCHEDULER_CRON", "45 1 * * *")
    monkeypatch.setenv("GIS_EXPORT_SCHEDULER_TIMEZONE", "UTC")
    monkeypatch.setenv("GIS_EXPORT_RETENTION_COUNT", "8")
    monkeypatch.setenv("GIS_EXPORT_MAX_LAYERS_PER_RUN", "3")

    settings = Settings()

    assert settings.app_env == "test"
    assert settings.backend_port == 9010
    assert settings.backend_cors_origins == "http://localhost:8080,https://gaia.internal"
    assert settings.database_url == "sqlite:///./test.db"
    assert settings.mobile_connector_token == "connector-secret"
    assert settings.effective_mobile_connector_token == "connector-secret"
    assert settings.mobile_connector_header_name == "X-Test-Connector"
    assert settings.gate_mobile_gateway_base_url == "https://gateway.example.test"
    assert settings.gate_mobile_connector_token == "gate-token"
    assert settings.gate_mobile_sync_enabled is True
    assert settings.gate_mobile_sync_timeout_seconds == 8.5
    assert settings.pdnd_client_id == "client-123"
    assert settings.pdnd_kid == "kid-456"
    assert settings.pdnd_private_key_path == "/tmp/pdnd.pem"
    assert settings.pdnd_private_key_pem == "pem-inline"
    assert settings.pdnd_auth_url == "https://auth.example.test/token"
    assert settings.pdnd_client_assertion_audience == "auth.example.test/client-assertion"
    assert settings.pdnd_audience == "https://audience.example.test/"
    assert settings.anpr_base_url == "https://anpr.example.test"
    assert settings.anpr_ca_bundle_path == "/tmp/anpr-ca.pem"
    assert settings.anpr_ssl_verify is False
    assert settings.anpr_daily_call_hard_limit == 45
    assert settings.anpr_job_batch_size == 6
    assert settings.anpr_job_start_hour == 9
    assert settings.anpr_job_end_hour == 17
    assert settings.anpr_job_timezone == "UTC"
    assert settings.anpr_job_ruolo_year == 2027
    assert settings.pdnd_fruitore_user_id == "GAIA-TEST"
    assert settings.pdnd_fruitore_user_location == "GAIA-TEST-SRV"
    assert settings.pdnd_loa == "HIGH"
    assert settings.purpose_id_c030 == "purpose-c030"
    assert settings.purpose_id_c004 == "purpose-c004"
    assert settings.nas_host == "10.10.10.10"
    assert settings.nas_timeout == 25
    assert settings.nas_shares_command == "ls /shares"
    assert settings.nas_share_subpaths_command == "find /shares/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -maxdepth 2 -type d -print 2>/dev/null || true"
    assert settings.nas_share_subpaths_full_command == "find /shares/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true"
    assert settings.sync_live_max_attempts == 5
    assert settings.sync_live_backoff_mode == "exponential"
    assert settings.sync_live_backoff_multiplier == 3
    assert settings.sync_live_backoff_jitter_enabled is True
    assert settings.sync_live_backoff_jitter_ratio == 0.35
    assert settings.sync_schedule_enabled is True
    assert settings.sync_schedule_interval_seconds == 60
    assert settings.bootstrap_admin_username == "adminseed"
    assert settings.wc_sync_daily_enabled is True
    assert settings.wc_sync_daily_cron == "30 1 * * *"
    assert settings.wc_sync_daily_timezone == "UTC"
    assert settings.wc_sync_daily_lookback_days == 2
    assert settings.elaborazioni_db_backup_enabled is False
    assert settings.elaborazioni_db_backup_cron == "15 2 * * *"
    assert settings.elaborazioni_db_backup_timezone == "Europe/Rome"
    assert settings.elaborazioni_db_backup_retention_count == 7
    assert settings.elaborazioni_db_backup_local_dir == "/var/backups/gaia"
    assert settings.elaborazioni_db_backup_remote_root == "/volume1/Backups/GAIA/prod-db"
    assert settings.elaborazioni_db_backup_encryption_enabled is True
    assert settings.elaborazioni_db_backup_encryption_passphrase == "backup-passphrase"
    assert settings.gis_export_scheduler_enabled is True
    assert settings.gis_export_scheduler_cron == "45 1 * * *"
    assert settings.gis_export_scheduler_timezone == "UTC"
    assert settings.gis_export_retention_count == 8
    assert settings.gis_export_max_layers_per_run == 3


def test_settings_mobile_connector_token_falls_back_to_gate_token(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "config-secret")
    monkeypatch.setenv("MOBILE_CONNECTOR_TOKEN", "")
    monkeypatch.setenv("GATE_MOBILE_CONNECTOR_TOKEN", "gate-token")

    settings = Settings(_env_file=None)

    assert settings.mobile_connector_token == ""
    assert settings.gate_mobile_connector_token == "gate-token"
    assert settings.effective_mobile_connector_token == "gate-token"


def test_settings_validators_reject_missing_or_placeholder_secrets(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("JWT_SECRET_KEY", "config-secret")
    try:
        Settings(_env_file=None)
        raise AssertionError("expected empty DATABASE_URL to fail")
    except ValueError as exc:
        assert "DATABASE_URL must be set" in str(exc)

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:change_me@db/gaia")
    try:
        Settings(_env_file=None)
        raise AssertionError("expected placeholder DATABASE_URL to fail")
    except ValueError as exc:
        assert "DATABASE_URL contains a placeholder" in str(exc)

    monkeypatch.setenv("DATABASE_URL", "sqlite:///./ok.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    try:
        Settings(_env_file=None)
        raise AssertionError("expected empty JWT_SECRET_KEY to fail")
    except ValueError as exc:
        assert "JWT_SECRET_KEY must be set" in str(exc)

    monkeypatch.setenv("JWT_SECRET_KEY", "change_this_secret")
    try:
        Settings(_env_file=None)
        raise AssertionError("expected placeholder JWT_SECRET_KEY to fail")
    except ValueError as exc:
        assert "JWT_SECRET_KEY contains a placeholder" in str(exc)


def test_settings_helper_properties_parse_tokens_and_fallbacks(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "config-secret")
    monkeypatch.setenv("WC_SYNC_USERS_ROLE_IDS", " 30, 49 ,, ")
    monkeypatch.setenv("WC_SYNC_CONSORZIATI_ROLE_ID", "")
    monkeypatch.setenv("CATASTO_ADE_AUTOSYNC_CATEGORIES", " nuove_in_ade, geometrie_variate ,, ")
    monkeypatch.setenv("MOBILE_CONNECTOR_TOKEN", "connector-token")
    monkeypatch.setenv("GATE_MOBILE_CONNECTOR_TOKEN", "gate-token")

    settings = Settings(_env_file=None)

    assert settings.wc_sync_users_role_id_list == ["30", "49"]
    assert settings.wc_sync_consorziati_role_id_value == "3"
    assert settings.catasto_ade_autosync_categories_list == ["nuove_in_ade", "geometrie_variate"]
    assert settings.effective_mobile_connector_token == "connector-token"
