from __future__ import annotations

from typing import Protocol

from payment_service.application.base.query import Query
from payment_service.application.base.view import View


class QueryHandler[TQuery: Query[View], TResult: View](Protocol):
    async def handle(self, query: TQuery) -> TResult: ...
