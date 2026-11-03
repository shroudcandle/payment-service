from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class PaymentCreatedMessage(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    payment_id: uuid.UUID
    correlation_id: str | None = None
