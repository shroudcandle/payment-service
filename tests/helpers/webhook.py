from __future__ import annotations

import httpx

from payment_service.infrastructure.http import HttpxWebhookSender


def make_webhook_sender(client: httpx.AsyncClient) -> HttpxWebhookSender:
    return HttpxWebhookSender(client, timeout_seconds=1.0)
