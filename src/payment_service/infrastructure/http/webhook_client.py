from __future__ import annotations

from typing import Any

import httpx

from payment_service.application.exceptions import (
    NonRetryableWebhookError,
    WebhookDeliveryError,
)
from payment_service.application.ports import WebhookSenderPort


class HttpxWebhookSender(WebhookSenderPort):
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        timeout_seconds: float,
    ) -> None:
        self._client = client
        self._timeout_seconds = timeout_seconds

    async def send(
        self,
        url: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        headers = {"X-Correlation-ID": correlation_id} if correlation_id is not None else None
        try:
            response = await self._client.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout_seconds,
                follow_redirects=False,
            )
        except httpx.TransportError as exc:
            raise WebhookDeliveryError(url, str(exc)) from exc

        status = response.status_code
        if response.is_success:
            return
        if response.is_client_error:
            raise NonRetryableWebhookError(url, status)
        raise WebhookDeliveryError(url, f"receiver responded with {status}")
