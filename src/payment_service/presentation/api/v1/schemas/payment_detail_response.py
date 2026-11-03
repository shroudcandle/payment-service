from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from payment_service.domain.payment import Currency, PaymentStatus


class PaymentDetailResponse(BaseModel):
    id: uuid.UUID = Field(description="Уникальный идентификатор платежа")
    amount: Decimal = Field(description="Сумма платежа")
    currency: Currency = Field(description="Код валюты")
    description: str = Field(description="Человекочитаемое описание платежа")
    metadata: dict[str, Any] = Field(description="Произвольные JSON-метаданные")
    status: PaymentStatus = Field(description="Текущий статус платежа")
    idempotency_key: str = Field(description="Idempotency-Key, переданный при создании")
    webhook_url: str = Field(description="URL обратного вызова для статуса платежа")
    created_at: datetime = Field(description="Время создания платежа в UTC")
    processed_at: datetime | None = Field(
        default=None,
        description="Время достижения платежом финального статуса",
    )
