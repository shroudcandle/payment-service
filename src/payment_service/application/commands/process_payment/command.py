from __future__ import annotations

import uuid
from dataclasses import dataclass

from payment_service.application.base.command import Command


@dataclass(frozen=True, slots=True)
class ProcessPaymentCommand(Command[None]):
    payment_id: uuid.UUID
    correlation_id: str | None = None
