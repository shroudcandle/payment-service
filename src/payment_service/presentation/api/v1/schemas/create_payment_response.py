from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from payment_service.domain.payment import PaymentStatus


class CreatePaymentResponse(BaseModel):
    payment_id: uuid.UUID = Field(description="Уникальный идентификатор платежа")
    status: PaymentStatus = Field(description="Текущий статус платежа")
    created_at: datetime = Field(description="Время создания платежа в UTC")
