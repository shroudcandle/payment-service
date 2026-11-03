from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Final

from pydantic import BaseModel, Field, HttpUrl, field_validator

from payment_service.domain.payment import Currency

_AMOUNT_MAX_DIGITS: Final = 12
_AMOUNT_DECIMAL_PLACES: Final = 2
_DESCRIPTION_MAX_LENGTH: Final = 1024
MAX_METADATA_BYTES = 65_536
MAX_METADATA_DEPTH = 10
MAX_METADATA_KEYS = 256


def _contains_nul(value: Any) -> bool:
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, dict):
        return any(_contains_nul(key) or _contains_nul(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_nul(item) for item in value)
    return False


def _depth(value: Any) -> int:
    if isinstance(value, dict):
        return 1 + max((_depth(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((_depth(item) for item in value), default=0)
    return 1


def _key_count(value: Any) -> int:
    if isinstance(value, dict):
        return len(value) + sum(_key_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(_key_count(item) for item in value)
    return 0


class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(
        gt=0,
        max_digits=_AMOUNT_MAX_DIGITS,
        decimal_places=_AMOUNT_DECIMAL_PLACES,
        description="Сумма платежа: больше нуля, не более 2 знаков после запятой",
        examples=["1000.50"],
    )
    currency: Currency = Field(
        description="Код валюты ISO 4217",
        examples=["RUB"],
    )
    description: str = Field(
        min_length=1,
        max_length=_DESCRIPTION_MAX_LENGTH,
        pattern=r"^[^\x00]*$",
        description="Человекочитаемое описание платежа",
        examples=["Order #123"],
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Произвольные JSON-метаданные, сохраняемые с платежом",
        examples=[{"order_id": 123}],
    )
    webhook_url: HttpUrl = Field(
        description="URL обратного вызова для получения финального статуса платежа",
        examples=["https://example.com/webhooks/payments"],
    )

    @field_validator("metadata")
    @classmethod
    def _validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if _contains_nul(value):
            raise ValueError("metadata must not contain NUL bytes")
        if _depth(value) > MAX_METADATA_DEPTH:
            raise ValueError(f"metadata must not be deeper than {MAX_METADATA_DEPTH} levels")
        if _key_count(value) > MAX_METADATA_KEYS:
            raise ValueError(f"metadata must not contain more than {MAX_METADATA_KEYS} keys")
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
            raise ValueError(f"metadata must not exceed {MAX_METADATA_BYTES} bytes")
        return value
