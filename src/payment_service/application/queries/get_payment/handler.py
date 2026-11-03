from __future__ import annotations

from payment_service.application.base import QueryHandler
from payment_service.application.exceptions import PaymentNotFoundError
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.application.queries.get_payment.query import GetPaymentQuery
from payment_service.application.views import PaymentDetailsView


class GetPaymentHandler(QueryHandler[GetPaymentQuery, PaymentDetailsView]):
    def __init__(self, uow_factory: UnitOfWorkFactoryPort) -> None:
        self._uow_factory = uow_factory

    async def handle(self, query: GetPaymentQuery) -> PaymentDetailsView:
        async with self._uow_factory() as uow:
            view = await uow.payment_reader.get_view_by_id(query.payment_id)
        if view is None:
            raise PaymentNotFoundError(query.payment_id)
        return view
