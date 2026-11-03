from __future__ import annotations

import uuid
from dataclasses import dataclass

from payment_service.application.base import Query
from payment_service.application.views import PaymentDetailsView


@dataclass(frozen=True, slots=True)
class GetPaymentQuery(Query[PaymentDetailsView]):
    payment_id: uuid.UUID
