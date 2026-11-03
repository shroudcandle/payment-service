from __future__ import annotations

import asyncio
import secrets
import uuid
from collections import OrderedDict

from payment_service.application.ports import GatewayChargeResult, PaymentGatewayPort


class EmulatorPaymentGateway(PaymentGatewayPort):
    _MAX_CACHE = 10_000
    _RANDOM_RESOLUTION = 10_000

    def __init__(
        self,
        *,
        min_delay: float,
        max_delay: float,
        success_rate: float,
    ) -> None:
        if min_delay < 0 or max_delay < min_delay:
            raise ValueError("invalid gateway delay bounds")
        if not 0.0 <= success_rate <= 1.0:
            raise ValueError("success_rate must be within [0, 1]")
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._success_rate = success_rate
        self._results: OrderedDict[uuid.UUID, GatewayChargeResult] = OrderedDict()
        self._locks: dict[uuid.UUID, asyncio.Lock] = {}

    async def charge(self, payment_id: uuid.UUID) -> GatewayChargeResult:
        lock = self._locks.setdefault(payment_id, asyncio.Lock())
        async with lock:
            cached = self._results.get(payment_id)
            if cached is not None:
                return cached
            await asyncio.sleep(self._next_delay())
            result = GatewayChargeResult(success=self._next_success())
            self._remember(payment_id, result)
            return result

    def _remember(self, payment_id: uuid.UUID, result: GatewayChargeResult) -> None:
        self._results[payment_id] = result
        if len(self._results) > self._MAX_CACHE:
            evicted_id, _ = self._results.popitem(last=False)
            self._locks.pop(evicted_id, None)

    def _next_delay(self) -> float:
        span = self._max_delay - self._min_delay
        fraction = secrets.randbelow(self._RANDOM_RESOLUTION) / self._RANDOM_RESOLUTION
        return self._min_delay + span * fraction

    def _next_success(self) -> bool:
        threshold = int(self._success_rate * self._RANDOM_RESOLUTION)
        return secrets.randbelow(self._RANDOM_RESOLUTION) < threshold
