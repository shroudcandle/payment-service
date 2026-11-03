from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from dishka import make_async_container
from dishka_faststream import setup_dishka
from fastapi import FastAPI
from faststream.rabbit import RabbitBroker, RabbitMessage, TestRabbitBroker
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from payment_service.application.exceptions import DuplicateIdempotencyKeyError
from payment_service.domain.payment import (
    InvalidAmountError,
    InvalidStateTransitionError,
    Payment,
)
from payment_service.infrastructure.messaging.topology import (
    DLX_EXCHANGE,
    PAYMENTS_DLQ,
    PAYMENTS_RETRY_QUEUE,
    RETRY_EXCHANGE,
)
from payment_service.presentation.api.app import create_app
from payment_service.presentation.api.exception_handlers import register_exception_handlers
from payment_service.presentation.consumers.payment_events_consumer import (
    register_payment_consumer,
)
from tests.fakes.collected_message import CollectedMessage
from tests.fakes.consumer_harness import ConsumerHarness
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fakes.fake_webhook_sender import FakeWebhookSender
from tests.fakes.security_override_provider import SecurityOverrideProvider
from tests.fakes.services_override_provider import ServicesOverrideProvider
from tests.fakes.store import InMemoryStore
from tests.fakes.worker_settings_provider import WorkerSettingsOverrideProvider
from tests.helpers.payments import make_payment


@pytest.fixture
async def openapi() -> AsyncIterator[dict[str, Any]]:
    container = make_async_container(
        SecurityOverrideProvider(),
        ServicesOverrideProvider(InMemoryStore(), FakePaymentGateway(), FakeWebhookSender()),
    )
    schema = create_app(container).openapi()
    yield schema
    await container.close()


@pytest.fixture
async def failing_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/unexpected")
    async def unexpected() -> None:
        raise RuntimeError("database password leaked here")

    @app.get("/database")
    async def database() -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    @app.get("/integrity")
    async def integrity() -> None:
        raise IntegrityError("INSERT", {}, Exception("duplicate"))

    @app.get("/sqlalchemy")
    async def sqlalchemy_error() -> None:
        raise SQLAlchemyError("unexpected sqlalchemy failure")

    @app.get("/duplicate-key")
    async def duplicate_key() -> None:
        raise DuplicateIdempotencyKeyError("key-1")

    @app.get("/invalid-state")
    async def invalid_state() -> None:
        raise InvalidStateTransitionError("payment is already processed")

    @app.get("/invalid-amount")
    async def invalid_amount() -> None:
        raise InvalidAmountError("amount must be positive")

    return app


@pytest.fixture
async def client(failing_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=failing_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture
def seeded_payment(store: InMemoryStore) -> Payment:
    payment = make_payment()
    store.payments[payment.id] = payment
    return payment


@pytest.fixture
async def harness(
    store: InMemoryStore,
    webhook_sender: FakeWebhookSender,
) -> AsyncIterator[ConsumerHarness]:
    container = make_async_container(
        ServicesOverrideProvider(store, FakePaymentGateway(success=True), webhook_sender),
        WorkerSettingsOverrideProvider(),
    )
    broker = RabbitBroker()
    consumer_harness = ConsumerHarness()

    @broker.subscriber(PAYMENTS_DLQ, DLX_EXCHANGE)
    async def _collect_dead(body: dict[str, Any], message: RabbitMessage) -> None:
        consumer_harness.dead.append(CollectedMessage(body, dict(message.headers)))

    @broker.subscriber(PAYMENTS_RETRY_QUEUE, RETRY_EXCHANGE)
    async def _collect_retry(body: dict[str, Any], message: RabbitMessage) -> None:
        consumer_harness.retried.append(
            CollectedMessage(body, dict(message.headers), message.raw_message.expiration)
        )

    setup_dishka(container, broker=broker, auto_inject=True)
    register_payment_consumer(broker)
    async with TestRabbitBroker(broker) as test_broker:
        consumer_harness.broker = test_broker
        yield consumer_harness
    await container.close()
