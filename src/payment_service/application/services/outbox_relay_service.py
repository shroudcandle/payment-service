from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from payment_service.application.exceptions import EventPublishError
from payment_service.application.ports import (
    EventPublisherPort,
    UnitOfWorkFactoryPort,
    UnitOfWorkPort,
)
from payment_service.domain.outbox import (
    DEFAULT_RETRY_BASE,
    DEFAULT_RETRY_CAP,
    OutboxEvent,
    decide_retry,
)

logger = logging.getLogger(__name__)


class OutboxRelayService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryPort,
        publisher: EventPublisherPort,
        *,
        batch_size: int,
        poll_interval: float,
        max_attempts: int,
        lease_seconds: float,
        retry_base: float = DEFAULT_RETRY_BASE,
        retry_cap: float = DEFAULT_RETRY_CAP,
    ) -> None:
        self._uow_factory = uow_factory
        self._publisher = publisher
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._max_attempts = max_attempts
        self._lease_seconds = lease_seconds
        self._retry_base = retry_base
        self._retry_cap = retry_cap

    async def run_forever(self) -> None:
        while True:
            published = await self.run_once()
            if published == 0:
                await asyncio.sleep(self._poll_interval)

    async def run_once(self) -> int:
        claimed = await self._claim()

        outcomes: list[tuple[OutboxEvent, str | None]] = []
        for event in claimed:
            try:
                await self._publisher.publish(event)
            except EventPublishError as exc:
                logger.warning("Failed to publish outbox event %s: %s", event.id, exc)
                outcomes.append((event, str(exc)))
            else:
                outcomes.append((event, None))

        await self._record(outcomes)
        return len(claimed)

    async def _claim(self) -> list[OutboxEvent]:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            events = await uow.outbox.claim_pending(self._batch_size, now, self._lease_seconds)
            await uow.commit()
        return events

    async def _record(self, outcomes: list[tuple[OutboxEvent, str | None]]) -> None:
        if not outcomes:
            return
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            for event, error in outcomes:
                if error is None:
                    await uow.outbox.mark_published(event.id, now)
                else:
                    await self._mark_failure(uow, event, error, now)
            await uow.commit()

    async def _mark_failure(
        self,
        uow: UnitOfWorkPort,
        event: OutboxEvent,
        error: str,
        now: datetime,
    ) -> None:
        decision = decide_retry(
            event.retry_count, self._max_attempts, self._retry_base, self._retry_cap
        )
        if decision.should_retry:
            await uow.outbox.mark_retry(
                event.id, error, now + timedelta(seconds=decision.delay_seconds)
            )
        else:
            logger.error(
                "Outbox event %s exhausted %s attempts: %s",
                event.id,
                self._max_attempts,
                error,
            )
            await uow.outbox.mark_failed(event.id, error, now)
