from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from payment_service.application.base import View
from payment_service.domain.payment import PaymentStatus


@dataclass(frozen=True, slots=True)
class CreatePaymentResult(View):
    payment_id: uuid.UUID
    status: PaymentStatus
    created_at: datetime
