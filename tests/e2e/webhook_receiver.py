from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WebhookReceiver:
    url: str
    failures_remaining: int = 0
    attempts: int = 0
    received: list[dict[str, Any]] = field(default_factory=list)
    received_headers: list[dict[str, str]] = field(default_factory=list)

    def should_fail(self) -> bool:
        self.attempts += 1
        if self.failures_remaining <= 0:
            return False
        self.failures_remaining -= 1
        return True

    def record(self, body: dict[str, Any], headers: dict[str, str]) -> None:
        self.received.append(body)
        self.received_headers.append(headers)
