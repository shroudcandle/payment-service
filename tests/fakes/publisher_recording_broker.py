from __future__ import annotations

from typing import Any


class PublisherRecordingBroker:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[dict[str, Any], dict[str, Any]]] = []

    async def publish(self, message: dict[str, Any], **kwargs: Any) -> None:
        if self.error is not None:
            raise self.error
        self.calls.append((message, kwargs))
