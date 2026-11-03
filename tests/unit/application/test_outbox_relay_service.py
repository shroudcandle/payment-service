from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from payment_service.application.exceptions import EventPublishError
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.application.services import OutboxRelayService
from payment_service.domain.outbox import OutboxEvent, OutboxStatus
from tests.fakes.fake_event_publisher import FakeEventPublisher


async def test_publishes_and_marks_event_as_published(
    outbox_event: OutboxEvent,
    uow_factory: UnitOfWorkFactoryPort,
    publisher: FakeEventPublisher,
) -> None:
    relay = OutboxRelayService(
        uow_factory,
        publisher,
        batch_size=10,
        poll_interval=0.0,
        max_attempts=3,
        lease_seconds=30.0,
    )

    processed = await relay.run_once()

    assert processed == 1
    assert publisher.published == [outbox_event]
    assert outbox_event.status is OutboxStatus.PUBLISHED
    assert outbox_event.processed_at is not None


async def test_failure_schedules_retry_then_fails(
    outbox_event: OutboxEvent,
    uow_factory: UnitOfWorkFactoryPort,
    publisher: FakeEventPublisher,
) -> None:
    publisher.error = EventPublishError(outbox_event.id, "broker down")
    relay = OutboxRelayService(
        uow_factory,
        publisher,
        batch_size=10,
        poll_interval=0.0,
        max_attempts=1,
        lease_seconds=30.0,
    )

    await relay.run_once()

    assert outbox_event.status is OutboxStatus.PENDING
    assert outbox_event.retry_count == 1
    assert outbox_event.error_log is not None
    assert outbox_event.next_attempt_at is not None

    outbox_event.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    await relay.run_once()

    assert outbox_event.status is OutboxStatus.FAILED
    assert outbox_event.retry_count == 2


async def test_empty_outbox_returns_zero(
    uow_factory: UnitOfWorkFactoryPort,
    publisher: FakeEventPublisher,
) -> None:
    relay = OutboxRelayService(
        uow_factory,
        publisher,
        batch_size=10,
        poll_interval=0.0,
        max_attempts=3,
        lease_seconds=30.0,
    )

    assert await relay.run_once() == 0


async def test_run_forever_publishes_until_cancelled(
    outbox_event: OutboxEvent,
    uow_factory: UnitOfWorkFactoryPort,
    publisher: FakeEventPublisher,
) -> None:
    relay = OutboxRelayService(
        uow_factory,
        publisher,
        batch_size=10,
        poll_interval=0.01,
        max_attempts=3,
        lease_seconds=30.0,
    )

    task = asyncio.create_task(relay.run_forever())
    await asyncio.sleep(0.05)
    assert not task.done()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert publisher.published == [outbox_event]
