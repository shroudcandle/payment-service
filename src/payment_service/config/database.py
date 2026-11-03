from __future__ import annotations

from typing import Self
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        env_prefix="PAYMENT_SERVICE_",
    )

    user: str = Field(default="postgres", validation_alias="POSTGRES_USER")
    password: str = Field(default="postgres", validation_alias="POSTGRES_PASSWORD")
    database: str = Field(default="payments_db", validation_alias="POSTGRES_DB")
    host: str = Field(default="postgres", validation_alias="POSTGRES_HOST")
    port: int = Field(default=5432, ge=1, le=65535, validation_alias="POSTGRES_PORT")
    url: str = Field(default="", validation_alias="DATABASE_URL")
    echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")

    @model_validator(mode="after")
    def _build_url(self) -> Self:
        if not self.url:
            self.url = (
                f"postgresql+asyncpg://{quote_plus(self.user)}:{quote_plus(self.password)}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        return self
