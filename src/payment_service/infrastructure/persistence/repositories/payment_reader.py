from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.application.ports import PaymentReaderPort
from payment_service.application.views import PaymentDetailsView
from payment_service.infrastructure.persistence.mappers import PaymentMapper
from payment_service.infrastructure.persistence.tables import PaymentTable


class SqlAlchemyPaymentReader(PaymentReaderPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_view_by_id(self, payment_id: uuid.UUID) -> PaymentDetailsView | None:
        row = await self._session.get(PaymentTable, payment_id)
        return PaymentMapper.to_view(row) if row is not None else None
