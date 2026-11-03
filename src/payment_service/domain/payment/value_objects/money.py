from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from payment_service.domain.base import ValueObject
from payment_service.domain.payment.exceptions import InvalidAmountError
from payment_service.domain.payment.value_objects.currency import Currency

_MONEY_QUANTUM: Final = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money(ValueObject):
    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if not self.amount.is_finite() or self.amount <= 0:
            raise InvalidAmountError("amount must be a positive finite number")
        object.__setattr__(self, "amount", self.amount.quantize(_MONEY_QUANTUM))

    def __repr__(self) -> str:
        return f"Money({self.amount} {self.currency.value})"
