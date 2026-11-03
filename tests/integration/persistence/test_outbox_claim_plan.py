from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, insert, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment_service.domain.outbox import OutboxStatus
from payment_service.infrastructure.persistence.repositories.outbox_repository import (
    SqlAlchemyOutboxRepository,
    claim_pending_query,
)
from payment_service.infrastructure.persistence.tables import OutboxTable

_BACKLOG_SIZE = 20_000
_PENDING_SIZE = 50


async def test_claim_pending_uses_index_and_leases_rows(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        await session.execute(
            insert(OutboxTable),
            [
                _outbox_row(OutboxStatus.PUBLISHED, now - timedelta(days=1))
                for _ in range(_BACKLOG_SIZE)
            ],
        )
        await session.execute(
            insert(OutboxTable),
            [_outbox_row(OutboxStatus.PENDING, now) for _ in range(_PENDING_SIZE)],
        )
        await session.execute(text("ANALYZE outbox"))
        await session.commit()

        statement = claim_pending_query(_PENDING_SIZE, now).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        plan = (await session.execute(text(f"EXPLAIN (FORMAT JSON) {statement}"))).scalar_one()
        plan_text = plan if isinstance(plan, str) else json.dumps(plan)
        assert "Seq Scan" not in plan_text
        assert "ix_outbox" in plan_text

        repository = SqlAlchemyOutboxRepository(session)
        claimed = await repository.claim_pending(_PENDING_SIZE, now, lease_seconds=30.0)
        await session.commit()
        leased_again = await repository.claim_pending(_PENDING_SIZE, now, lease_seconds=30.0)

        statuses = await session.execute(
            select(OutboxTable.status, func.count()).group_by(OutboxTable.status)
        )

    assert len(claimed) == _PENDING_SIZE
    assert leased_again == []
    counts = dict(statuses.all())
    assert counts[OutboxStatus.PENDING.value] == _PENDING_SIZE
    assert counts[OutboxStatus.PUBLISHED.value] == _BACKLOG_SIZE


def _outbox_row(status: OutboxStatus, created_at: datetime) -> dict[str, object]:
    event_id = uuid.uuid4()
    return {
        "id": event_id,
        "event_type": "payment.created",
        "routing_key": "payment.created",
        "payload": {"payment_id": str(event_id)},
        "status": status.value,
        "retry_count": 0,
        "error_log": None,
        "created_at": created_at,
        "processed_at": None,
        "next_attempt_at": None,
    }
