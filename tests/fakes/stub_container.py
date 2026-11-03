from __future__ import annotations

from typing import Any

from faststream.rabbit import RabbitBroker

from payment_service.config import Settings
from tests.fakes.stub_broker import StubBroker


class StubContainer:
    def __init__(self, settings: Settings, broker: StubBroker) -> None:
        self._settings = settings
        self._broker = broker
        self.closed = False

    async def get(self, dependency_type: Any) -> Any:
        if dependency_type is Settings:
            return self._settings
        if dependency_type is RabbitBroker:
            return self._broker
        raise AssertionError(f"unexpected dependency: {dependency_type}")

    async def close(self) -> None:
        self.closed = True
