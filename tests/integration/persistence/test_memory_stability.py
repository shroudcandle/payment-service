from __future__ import annotations

import gc
import tracemalloc
import weakref

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment_service.application.commands.create_payment.handler import CreatePaymentHandler
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.application.services import OutboxRelayService
from payment_service.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tests.factories import make_create_payment_command
from tests.fakes.discarding_event_publisher import DiscardingEventPublisher

_MEMORY_LIMIT_BYTES = 5 * 1024 * 1024
_HANDLER_ITERATIONS = 300
_OUTBOX_EVENTS = 200


def _tracking_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UnitOfWorkFactoryPort, list[weakref.ref[SqlAlchemyUnitOfWork]]]:
    refs: list[weakref.ref[SqlAlchemyUnitOfWork]] = []

    def build() -> SqlAlchemyUnitOfWork:
        uow = SqlAlchemyUnitOfWork(session_factory)
        refs.append(weakref.ref(uow))
        return uow

    return build, refs


def _assert_refs_collected(refs: list[weakref.ref[SqlAlchemyUnitOfWork]]) -> None:
    gc.collect()
    assert [ref() for ref in refs if ref() is not None] == []


async def test_payment_handlers_do_not_retain_units_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    factory, refs = _tracking_factory(session_factory)
    handler = CreatePaymentHandler(factory)
    for index in range(10):
        await handler.handle(make_create_payment_command(idempotency_key=f"warm-{index}"))

    _measure = _start_measurement()
    for index in range(_HANDLER_ITERATIONS):
        await handler.handle(make_create_payment_command(idempotency_key=f"mem-{index}"))
    growth = _stop_measurement(_measure)

    assert growth < _MEMORY_LIMIT_BYTES
    _assert_refs_collected(refs)


async def test_outbox_relay_does_not_retain_units_of_work(
    session_factory: async_sessionmaker[AsyncSession],
    uow_factory: UnitOfWorkFactoryPort,
) -> None:
    seed_handler = CreatePaymentHandler(uow_factory)
    for index in range(_OUTBOX_EVENTS):
        await seed_handler.handle(make_create_payment_command(idempotency_key=f"outbox-{index}"))

    factory, refs = _tracking_factory(session_factory)
    relay = OutboxRelayService(
        factory,
        DiscardingEventPublisher(),
        batch_size=_OUTBOX_EVENTS,
        poll_interval=0.0,
        max_attempts=3,
        lease_seconds=30.0,
    )

    _measure = _start_measurement()
    processed = await relay.run_once()
    growth = _stop_measurement(_measure)

    assert processed == _OUTBOX_EVENTS
    assert growth < _MEMORY_LIMIT_BYTES
    _assert_refs_collected(refs)


def _start_measurement() -> int:
    gc.collect()
    tracemalloc.start()
    return tracemalloc.get_traced_memory()[0]


def _stop_measurement(baseline: int) -> int:
    gc.collect()
    current, _peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return current - baseline
