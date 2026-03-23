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
    jwt_secret_key: str = Field(default="change_this_secret", alias="JWT_SECRET_KEY")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")
    jwt_algorithm: str = "HS256"
    nas_host: str = Field(default="nas.internal.local", alias="NAS_HOST")
    nas_port: int = Field(default=22, alias="NAS_PORT")
    nas_username: str = Field(default="svc_naap", alias="NAS_USERNAME")
    nas_password: str = Field(default="change_me", alias="NAS_PASSWORD")
    nas_private_key_path: str | None = Field(default=None, alias="NAS_PRIVATE_KEY_PATH")
    nas_timeout: int = Field(default=10, alias="NAS_TIMEOUT")
    nas_passwd_command: str = Field(default="getent passwd", alias="NAS_PASSWD_COMMAND")
    nas_group_command: str = Field(default="getent group", alias="NAS_GROUP_COMMAND")
    nas_shares_command: str = Field(default="ls /volume1", alias="NAS_SHARES_COMMAND")
    nas_acl_command_template: str = Field(
        default="synoacltool -get /volume1/{share}",
        alias="NAS_ACL_COMMAND_TEMPLATE",
    )
    sync_live_max_attempts: int = Field(default=3, alias="SYNC_LIVE_MAX_ATTEMPTS")
    sync_live_retry_delay_seconds: int = Field(default=2, alias="SYNC_LIVE_RETRY_DELAY_SECONDS")
    sync_schedule_enabled: bool = Field(default=False, alias="SYNC_SCHEDULE_ENABLED")
    sync_schedule_interval_seconds: int = Field(default=900, alias="SYNC_SCHEDULE_INTERVAL_SECONDS")
    sync_schedule_max_cycles: int = Field(default=0, alias="SYNC_SCHEDULE_MAX_CYCLES")
    bootstrap_admin_username: str = Field(default="admin", alias="BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_email: str = Field(default="admin@example.local", alias="BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_password: str = Field(default="change_me_admin", alias="BOOTSTRAP_ADMIN_PASSWORD")

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
