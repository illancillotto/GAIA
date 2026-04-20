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
    assert settings.backend_cors_origins == "http://localhost:3000,http://localhost:8080"
    assert settings.jwt_secret_key == "config-defaults-secret"
    assert settings.jwt_expire_minutes == 60
    assert settings.jwt_algorithm == "HS256"
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
    assert settings.database_url == "sqlite:///./config-defaults.db"


def test_settings_allow_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("BACKEND_PORT", "9010")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:8080,https://gaia.internal")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
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

    settings = Settings()

    assert settings.app_env == "test"
    assert settings.backend_port == 9010
    assert settings.backend_cors_origins == "http://localhost:8080,https://gaia.internal"
    assert settings.database_url == "sqlite:///./test.db"
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
