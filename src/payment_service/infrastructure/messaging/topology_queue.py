from __future__ import annotations

from typing import Any, Protocol


class TopologyQueue(Protocol):
    async def bind(self, exchange: Any, *, routing_key: str) -> object: ...
