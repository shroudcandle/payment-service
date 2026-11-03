from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.application.services import OutboxRelayService
from payment_service.domain.outbox import OutboxStatus
from payment_service.infrastructure.persistence.tables import OutboxTable
from tests.fakes.fake_event_publisher import FakeEventPublisher
from tests.helpers.persistence import make_outbox_table


async def test_concurrent_relays_publish_each_event_exactly_once(
    uow_factory: UnitOfWorkFactoryPort,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add_all([make_outbox_table() for _ in range(300)])
        await session.commit()

    publisher = FakeEventPublisher()
    relays = [
        OutboxRelayService(
            uow_factory,
            publisher,
            batch_size=100,
            poll_interval=0.0,
            max_attempts=3,
            lease_seconds=30.0,
        )
        for _ in range(3)
    ]

    claimed_counts = await asyncio.gather(*(relay.run_once() for relay in relays))

    assert sum(claimed_counts) == 300
    published_ids = [event.id for event in publisher.published]
    assert len(published_ids) == 300
    assert len(set(published_ids)) == 300

    async with session_factory() as session:
        published = await session.scalar(
            select(func.count())
            .select_from(OutboxTable)
            .where(OutboxTable.status == OutboxStatus.PUBLISHED.value)
        )

    assert published == 300
