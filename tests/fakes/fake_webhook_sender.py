from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from payment_service.application.ports import WebhookSenderPort


@dataclass
class FakeWebhookSender(WebhookSenderPort):
    error: Exception | None = None
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    correlation_ids: list[str | None] = field(default_factory=list)

    async def send(
        self,
        url: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        self.calls.append((url, payload))
        self.correlation_ids.append(correlation_id)
        if self.error is not None:
            raise self.error
