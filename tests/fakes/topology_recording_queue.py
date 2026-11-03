from __future__ import annotations

from typing import Any


class TopologyRecordingQueue:
    def __init__(self, name: str) -> None:
        self.name = name
        self.bindings: list[tuple[str, str]] = []

    async def bind(self, exchange: Any, *, routing_key: str) -> None:
        self.bindings.append((exchange.name, routing_key))
