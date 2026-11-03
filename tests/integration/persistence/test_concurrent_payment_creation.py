from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment_service.application.commands.create_payment.handler import CreatePaymentHandler
from payment_service.application.commands.create_payment.result import CreatePaymentResult
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.infrastructure.persistence.tables import OutboxTable, PaymentTable
from tests.factories import make_create_payment_command


async def test_concurrent_requests_with_same_key_create_one_payment(
    uow_factory: UnitOfWorkFactoryPort,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    handler = CreatePaymentHandler(uow_factory)
    command = make_create_payment_command(idempotency_key=f"race-{uuid.uuid4()}")

    results = await asyncio.gather(
        *(handler.handle(command) for _ in range(5)),
        return_exceptions=True,
    )

    assert [result for result in results if isinstance(result, BaseException)] == []
    payment_ids = {
        result.payment_id for result in results if isinstance(result, CreatePaymentResult)
    }
    assert len(payment_ids) == 1

    async with session_factory() as session:
        payments_count = await session.scalar(select(func.count()).select_from(PaymentTable))
        outbox_count = await session.scalar(select(func.count()).select_from(OutboxTable))

    assert payments_count == 1
    assert outbox_count == 1
