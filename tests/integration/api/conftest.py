from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from dishka import make_async_container
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from payment_service.presentation.api.app import create_app
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fakes.fake_webhook_sender import FakeWebhookSender
from tests.fakes.security_override_provider import SecurityOverrideProvider
from tests.fakes.services_override_provider import ServicesOverrideProvider
from tests.fakes.store import InMemoryStore


@pytest.fixture
async def api_app(
    store: InMemoryStore,
    gateway: FakePaymentGateway,
    webhook_sender: FakeWebhookSender,
) -> AsyncIterator[FastAPI]:
    container = make_async_container(
        SecurityOverrideProvider(),
        ServicesOverrideProvider(store, gateway, webhook_sender),
    )
    yield create_app(container)
    await container.close()


@pytest.fixture
async def client(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
