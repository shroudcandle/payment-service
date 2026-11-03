from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ComponentStatus = Literal["connected", "disconnected"]
OverallStatus = Literal["ok", "degraded"]


class HealthResponse(BaseModel):
    status: OverallStatus = Field(
        description="Общий статус сервиса: ok только при доступности всех зависимостей"
    )
    postgres: ComponentStatus = Field(description="Статус подключения к PostgreSQL")
    rabbitmq: ComponentStatus = Field(description="Статус подключения к RabbitMQ")
