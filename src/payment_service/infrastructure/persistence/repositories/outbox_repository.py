from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import Select, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.application.ports import OutboxRepositoryPort
from payment_service.domain.outbox import OutboxEvent, OutboxStatus
from payment_service.infrastructure.persistence.mappers import OutboxMapper
from payment_service.infrastructure.persistence.tables import OutboxTable


def claim_pending_query(limit: int, now: datetime) -> Select[OutboxTable]:
    return (
        select(OutboxTable)
        .where(
            OutboxTable.status == OutboxStatus.PENDING.value,
            or_(
                OutboxTable.next_attempt_at.is_(None),
                OutboxTable.next_attempt_at <= now,
            ),
        )
        .order_by(OutboxTable.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


class SqlAlchemyOutboxRepository(OutboxRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_pending(
        self, limit: int, now: datetime, lease_seconds: float
    ) -> list[OutboxEvent]:
        rows = list((await self._session.scalars(claim_pending_query(limit, now))).all())
        lease_until = now + timedelta(seconds=lease_seconds)
        for row in rows:
            row.next_attempt_at = lease_until
        await self._session.flush()
        return [OutboxMapper.to_domain(row) for row in rows]

    async def mark_published(self, event_id: uuid.UUID, now: datetime) -> None:
        await self._session.execute(
            update(OutboxTable)
            .where(OutboxTable.id == event_id)
            .values(
                status=OutboxStatus.PUBLISHED.value,
                processed_at=now,
                error_log=None,
                next_attempt_at=None,
            )
        )

    async def mark_retry(self, event_id: uuid.UUID, error: str, next_attempt_at: datetime) -> None:
        await self._session.execute(
            update(OutboxTable)
            .where(OutboxTable.id == event_id)
            .values(
                status=OutboxStatus.PENDING.value,
                retry_count=OutboxTable.retry_count + 1,
                error_log=error,
                next_attempt_at=next_attempt_at,
            )
        )

    async def mark_failed(self, event_id: uuid.UUID, error: str, now: datetime) -> None:
        await self._session.execute(
            update(OutboxTable)
            .where(OutboxTable.id == event_id)
            .values(
                status=OutboxStatus.FAILED.value,
                retry_count=OutboxTable.retry_count + 1,
                error_log=error,
                processed_at=now,
                next_attempt_at=None,
            )
        )
