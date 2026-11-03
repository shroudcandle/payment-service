from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from payment_service.domain.outbox import DEFAULT_RETRY_BASE, DEFAULT_RETRY_CAP


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    outbox_poll_interval: float = Field(default=0.5, gt=0, validation_alias="OUTBOX_POLL_INTERVAL")
    outbox_batch_size: int = Field(default=50, gt=0, validation_alias="OUTBOX_BATCH_SIZE")
    outbox_lease_seconds: float = Field(default=30.0, gt=0, validation_alias="OUTBOX_LEASE_SECONDS")
    relay_restart_delay_seconds: float = Field(
        default=5.0, gt=0, validation_alias="RELAY_RESTART_DELAY_SECONDS"
    )
    webhook_timeout_seconds: float = Field(
        default=5.0, gt=0, validation_alias="WEBHOOK_TIMEOUT_SECONDS"
    )
    gateway_min_delay: float = Field(default=2.0, ge=0, validation_alias="GATEWAY_MIN_DELAY")
    gateway_max_delay: float = Field(default=5.0, ge=0, validation_alias="GATEWAY_MAX_DELAY")
    gateway_success_rate: float = Field(
        default=0.9, ge=0.0, le=1.0, validation_alias="GATEWAY_SUCCESS_RATE"
    )
    max_delivery_attempts: int = Field(default=3, gt=0, validation_alias="MAX_DELIVERY_ATTEMPTS")
    retry_base: float = Field(default=DEFAULT_RETRY_BASE, gt=0, validation_alias="RETRY_BASE")
    retry_cap: float = Field(default=DEFAULT_RETRY_CAP, gt=0, validation_alias="RETRY_CAP")

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.gateway_max_delay < self.gateway_min_delay:
            raise ValueError("GATEWAY_MAX_DELAY must be greater than or equal to GATEWAY_MIN_DELAY")
        if self.retry_cap < self.retry_base:
            raise ValueError("RETRY_CAP must be greater than or equal to RETRY_BASE")
        return self
