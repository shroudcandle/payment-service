from __future__ import annotations

import httpx
import pytest
from dishka import AsyncContainer
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from payment_service import __version__
from payment_service.application.commands import CreatePaymentHandler, ProcessPaymentHandler
from payment_service.application.ports import (
    EventPublisherPort,
    PaymentGatewayPort,
    UnitOfWorkFactoryPort,
    WebhookSenderPort,
)
from payment_service.application.queries import GetPaymentHandler
from payment_service.application.services import OutboxRelayService, WebhookPolicy
from payment_service.config import (
    AppSettings,
    DatabaseSettings,
    HttpClientSettings,
    RabbitMQSettings,
    SecuritySettings,
    Settings,
    WorkerSettings,
)
from payment_service.di import make_container
from payment_service.infrastructure.gateway import EmulatorPaymentGateway
from payment_service.infrastructure.http import HttpxWebhookSender
from payment_service.infrastructure.messaging import RabbitEventPublisher
from payment_service.infrastructure.persistence import SqlAlchemyUnitOfWork


async def test_container_resolves_configuration_sections(container: AsyncContainer) -> None:
    settings = await container.get(Settings)

    assert isinstance(settings, Settings)
    assert isinstance(await container.get(AppSettings), AppSettings)
    assert isinstance(await container.get(DatabaseSettings), DatabaseSettings)
    assert isinstance(await container.get(HttpClientSettings), HttpClientSettings)
    assert isinstance(await container.get(RabbitMQSettings), RabbitMQSettings)
    assert isinstance(await container.get(SecuritySettings), SecuritySettings)
    assert isinstance(await container.get(WorkerSettings), WorkerSettings)


async def test_container_resolves_infrastructure_adapters(container: AsyncContainer) -> None:
    assert isinstance(await container.get(AsyncEngine), AsyncEngine)
    assert isinstance(await container.get(async_sessionmaker[AsyncSession]), async_sessionmaker)
    assert isinstance(await container.get(httpx.AsyncClient), httpx.AsyncClient)
    assert isinstance(await container.get(RabbitBroker), RabbitBroker)
    assert isinstance(
        await container.get(PaymentGatewayPort),
        EmulatorPaymentGateway,
    )
    assert isinstance(
        await container.get(WebhookSenderPort),
        HttpxWebhookSender,
    )
    assert isinstance(
        await container.get(EventPublisherPort),
        RabbitEventPublisher,
    )


async def test_container_configures_http_client(container: AsyncContainer) -> None:
    client = await container.get(httpx.AsyncClient)

    assert client.headers["User-Agent"] == f"payment-service/{__version__}"
    assert client.timeout == httpx.Timeout(10.0, connect=5.0)


async def test_container_configures_http_client_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "7.0")
    monkeypatch.setenv("HTTP_CONNECT_TIMEOUT_SECONDS", "2.0")
    container = make_container()
    try:
        client = await container.get(httpx.AsyncClient)
    finally:
        await container.close()

    assert client.timeout == httpx.Timeout(7.0, connect=2.0)


async def test_container_resolves_handlers_and_relay(container: AsyncContainer) -> None:
    assert isinstance(await container.get(CreatePaymentHandler), CreatePaymentHandler)
    assert isinstance(await container.get(GetPaymentHandler), GetPaymentHandler)
    assert isinstance(await container.get(ProcessPaymentHandler), ProcessPaymentHandler)
    assert isinstance(await container.get(OutboxRelayService), OutboxRelayService)


async def test_container_builds_unit_of_work_factory(container: AsyncContainer) -> None:
    unit_of_work = await container.get(UnitOfWorkFactoryPort)

    assert isinstance(unit_of_work(), SqlAlchemyUnitOfWork)


async def test_container_uses_permissive_webhook_policy_in_development(
    container: AsyncContainer,
) -> None:
    policy = await container.get(WebhookPolicy)

    assert policy.strict is False


async def test_container_uses_strict_webhook_policy_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEBHOOK_ALLOWED_HOSTS", "example.com, api.example.com")
    container = make_container()
    try:
        policy = await container.get(WebhookPolicy)
    finally:
        await container.close()

    assert policy.strict is True
    assert policy.allowed_hosts == frozenset({"example.com", "api.example.com"})


async def test_container_allows_explicit_permissive_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEBHOOK_STRICT_SECURITY", "false")
    container = make_container()
    try:
        policy = await container.get(WebhookPolicy)
    finally:
        await container.close()

    assert policy.strict is False
