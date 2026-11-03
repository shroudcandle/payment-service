from __future__ import annotations

from typing import Any, Protocol


class WebhookSenderPort(Protocol):
    async def send(
        self,
        url: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None: ...
