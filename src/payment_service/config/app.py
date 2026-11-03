from __future__ import annotations

from typing import Final

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOG_LEVELS: Final = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = Field(default="development", validation_alias="APP_ENV")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    run_migrations: bool = Field(default=True, validation_alias="RUN_MIGRATIONS")
    api_host: str = Field(default="127.0.0.1", validation_alias="API_HOST")
    api_port: int = Field(default=8000, ge=1, le=65535, validation_alias="API_PORT")
    rabbitmq_health_timeout_seconds: float = Field(
        default=1.0, gt=0, validation_alias="RABBITMQ_HEALTH_TIMEOUT_SECONDS"
    )
    webhook_strict_security: bool | None = Field(
        default=None, validation_alias="WEBHOOK_STRICT_SECURITY"
    )
    webhook_allowed_hosts: str = Field(default="", validation_alias="WEBHOOK_ALLOWED_HOSTS")

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in _LOG_LEVELS:
            raise ValueError(f"log_level must be one of {sorted(_LOG_LEVELS)}")
        return normalized
