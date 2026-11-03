from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from payment_service.domain.base import ValueObject
from payment_service.domain.payment.exceptions import InvalidIdempotencyKeyError


@dataclass(frozen=True, slots=True)
class IdempotencyKey(ValueObject):
    MAX_LENGTH: ClassVar[int] = 255

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise InvalidIdempotencyKeyError("idempotency key must not be empty")
        if len(self.value) > self.MAX_LENGTH:
            raise InvalidIdempotencyKeyError(
                f"idempotency key must be at most {self.MAX_LENGTH} characters"
            )

    def __str__(self) -> str:
        return self.value
