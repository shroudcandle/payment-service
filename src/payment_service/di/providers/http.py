from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from dishka import Provider, Scope, provide

from payment_service import __version__
from payment_service.application.ports import WebhookSenderPort
from payment_service.config import HttpClientSettings, WorkerSettings
from payment_service.infrastructure.http import HttpxWebhookSender

_USER_AGENT = f"payment-service/{__version__}"


class HttpProvider(Provider):
    scope = Scope.APP

    @provide
    async def http_client(self, settings: HttpClientSettings) -> AsyncIterator[httpx.AsyncClient]:
        limits = httpx.Limits(
            max_connections=settings.max_connections,
            max_keepalive_connections=settings.max_keepalive_connections,
            keepalive_expiry=settings.keepalive_expiry,
        )
        timeout = httpx.Timeout(
            settings.timeout_seconds,
            connect=settings.connect_timeout_seconds,
        )
        async with httpx.AsyncClient(
            headers={"User-Agent": _USER_AGENT},
            limits=limits,
            timeout=timeout,
        ) as client:
            yield client

    @provide
    def webhook_sender(
        self,
        client: httpx.AsyncClient,
        settings: WorkerSettings,
    ) -> WebhookSenderPort:
        return HttpxWebhookSender(
            client,
            timeout_seconds=settings.webhook_timeout_seconds,
        )
