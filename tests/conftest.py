from __future__ import annotations

from pathlib import Path

import pytest

from payment_service.application.ports import UnitOfWorkFactoryPort
from tests.fakes.fake_event_publisher import FakeEventPublisher
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fakes.fake_webhook_sender import FakeWebhookSender
from tests.fakes.in_memory_unit_of_work import InMemoryUnitOfWork
from tests.fakes.store import InMemoryStore


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        parts = Path(str(item.path)).parts
        if "unit" in parts:
            marker = pytest.mark.unit
        elif "architecture" in parts:
            marker = pytest.mark.architecture
        elif "e2e" in parts:
            marker = pytest.mark.e2e
        elif "integration" in parts and "persistence" in parts:
            marker = pytest.mark.integration
        elif "integration" in parts:
            marker = pytest.mark.api
        else:
            continue
        item.add_marker(marker)


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def uow_factory(store: InMemoryStore) -> UnitOfWorkFactoryPort:
    def build() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(store)

    return build


@pytest.fixture
def gateway() -> FakePaymentGateway:
    return FakePaymentGateway()


@pytest.fixture
def webhook_sender() -> FakeWebhookSender:
    return FakeWebhookSender()


@pytest.fixture
def publisher() -> FakeEventPublisher:
    return FakeEventPublisher()
