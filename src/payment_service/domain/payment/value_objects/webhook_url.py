from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from payment_service.domain.base import ValueObject
from payment_service.domain.payment.exceptions import InvalidWebhookUrlError


@dataclass(frozen=True, slots=True)
class WebhookUrl(ValueObject):
    value: str

    def __post_init__(self) -> None:
        parsed = urlparse(self.value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise InvalidWebhookUrlError("webhook_url must be a valid http(s) URL")

    def __str__(self) -> str:
        return self.value
