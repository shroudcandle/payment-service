from __future__ import annotations

from typing import Self
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RabbitMQSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        env_prefix="PAYMENT_SERVICE_",
    )

    user: str = Field(default="guest", validation_alias="RABBITMQ_USER")
    password: str = Field(default="guest", validation_alias="RABBITMQ_PASSWORD")
    host: str = Field(default="rabbitmq", validation_alias="RABBITMQ_HOST")
    port: int = Field(default=5672, ge=1, le=65535, validation_alias="RABBITMQ_PORT")
    url: str = Field(default="", validation_alias="RABBITMQ_URL")

    @model_validator(mode="after")
    def _build_url(self) -> Self:
        if not self.url:
            self.url = (
                f"amqp://{quote_plus(self.user)}:{quote_plus(self.password)}"
                f"@{self.host}:{self.port}/"
            )
        return self
