from __future__ import annotations

from payment_service.application.base.request import Request
from payment_service.application.base.view import View


class Query[TResult: View](Request[TResult]):
    __slots__ = ()
