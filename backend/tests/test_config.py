from app.core.config import Settings


def test_settings_use_expected_defaults() -> None:
    settings = Settings()

    assert settings.project_name == "NAS Access Audit Platform"
    assert settings.app_version == "0.1.0"
    assert settings.app_env == "development"
    assert settings.backend_host == "0.0.0.0"
    assert settings.backend_port == 8000
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_allow_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("BACKEND_PORT", "9010")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")

    settings = Settings()

    assert settings.app_env == "test"
    assert settings.backend_port == 9010
    assert settings.database_url == "sqlite:///./test.db"
