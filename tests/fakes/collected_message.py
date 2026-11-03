from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CollectedMessage:
    body: dict[str, Any]
    headers: dict[str, Any]
    expiration: float | None = None
