from __future__ import annotations

import pytest

from payment_service.infrastructure.persistence.tables import OutboxTable
from payment_service.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tests.fakes.uow_fake_session_factory import UowFakeSessionFactory
from tests.helpers.payments import make_payment


async def test_commit_persists_aggregate_events_to_outbox() -> None:
    factory = UowFakeSessionFactory()
    payment = make_payment()

    async with SqlAlchemyUnitOfWork(factory) as uow:
        await uow.payments.add(payment)
        await uow.commit()

    session = factory.sessions[0]
    assert session.committed
    assert any(isinstance(item, OutboxTable) for item in session.added)
    assert payment.events.peek() == ()


async def test_exit_with_exception_rolls_back_and_closes() -> None:
    factory = UowFakeSessionFactory()

    with pytest.raises(ValueError, match="boom"):
        async with SqlAlchemyUnitOfWork(factory) as uow:
            await uow.payments.add(make_payment())
            raise ValueError("boom")

    session = factory.sessions[0]
    assert session.rolled_back
    assert session.closed
    assert not session.committed


async def test_rollback_clears_tracked_aggregates() -> None:
    factory = UowFakeSessionFactory()

    async with SqlAlchemyUnitOfWork(factory) as uow:
        await uow.payments.add(make_payment())
        await uow.rollback()

    session = factory.sessions[0]
    assert session.rolled_back
    assert not any(isinstance(item, OutboxTable) for item in session.added)


async def test_exit_without_exception_only_closes() -> None:
    factory = UowFakeSessionFactory()

    async with SqlAlchemyUnitOfWork(factory):
        pass

    session = factory.sessions[0]
    assert session.closed
    assert not session.rolled_back


async def test_commit_outside_context_raises() -> None:
    uow = SqlAlchemyUnitOfWork(UowFakeSessionFactory())

    with pytest.raises(RuntimeError, match="outside"):
        await uow.commit()

    with pytest.raises(RuntimeError, match="outside"):
        await uow.rollback()
