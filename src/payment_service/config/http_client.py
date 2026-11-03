from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class HttpClientSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    max_connections: int = Field(default=100, gt=0, validation_alias="HTTP_MAX_CONNECTIONS")
    max_keepalive_connections: int = Field(
        default=20, ge=0, validation_alias="HTTP_MAX_KEEPALIVE_CONNECTIONS"
    )
    keepalive_expiry: float = Field(default=10.0, gt=0, validation_alias="HTTP_KEEPALIVE_EXPIRY")
    timeout_seconds: float = Field(default=10.0, gt=0, validation_alias="HTTP_TIMEOUT_SECONDS")
    connect_timeout_seconds: float = Field(
        default=5.0, gt=0, validation_alias="HTTP_CONNECT_TIMEOUT_SECONDS"
    )

    @model_validator(mode="after")
    def _validate_limits(self) -> Self:
        if self.max_keepalive_connections > self.max_connections:
            raise ValueError("HTTP_MAX_KEEPALIVE_CONNECTIONS must not exceed HTTP_MAX_CONNECTIONS")
        if self.connect_timeout_seconds > self.timeout_seconds:
            raise ValueError("HTTP_CONNECT_TIMEOUT_SECONDS must not exceed HTTP_TIMEOUT_SECONDS")
        return self
