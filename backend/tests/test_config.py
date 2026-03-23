from app.core.config import Settings


def test_settings_use_expected_defaults() -> None:
    settings = Settings()

    assert settings.project_name == "NAS Access Audit Platform"
    assert settings.app_version == "0.1.0"
    assert settings.app_env == "development"
    assert settings.backend_host == "0.0.0.0"
    assert settings.backend_port == 8000
    assert settings.jwt_secret_key == "change_this_secret"
    assert settings.jwt_expire_minutes == 60
    assert settings.jwt_algorithm == "HS256"
    assert settings.nas_host == "nas.internal.local"
    assert settings.nas_port == 22
    assert settings.nas_username == "svc_naap"
    assert settings.nas_timeout == 10
    assert settings.nas_passwd_command == "getent passwd"
    assert settings.nas_group_command == "getent group"
    assert settings.nas_shares_command == "ls /volume1"
    assert settings.nas_acl_command_template == "synoacltool -get /volume1/{share}"
    assert settings.sync_live_max_attempts == 3
    assert settings.sync_live_retry_delay_seconds == 2
    assert settings.sync_schedule_enabled is False
    assert settings.sync_schedule_interval_seconds == 900
    assert settings.sync_schedule_max_cycles == 0
    assert settings.bootstrap_admin_username == "admin"
    assert settings.bootstrap_admin_email == "admin@example.local"
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_allow_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("BACKEND_PORT", "9010")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("NAS_HOST", "10.10.10.10")
    monkeypatch.setenv("NAS_TIMEOUT", "25")
    monkeypatch.setenv("NAS_SHARES_COMMAND", "ls /shares")
    monkeypatch.setenv("SYNC_LIVE_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("SYNC_SCHEDULE_ENABLED", "true")
    monkeypatch.setenv("SYNC_SCHEDULE_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "adminseed")

    settings = Settings()

    assert settings.app_env == "test"
    assert settings.backend_port == 9010
    assert settings.database_url == "sqlite:///./test.db"
    assert settings.nas_host == "10.10.10.10"
    assert settings.nas_timeout == 25
    assert settings.nas_shares_command == "ls /shares"
    assert settings.sync_live_max_attempts == 5
    assert settings.sync_schedule_enabled is True
    assert settings.sync_schedule_interval_seconds == 60
    assert settings.bootstrap_admin_username == "adminseed"
