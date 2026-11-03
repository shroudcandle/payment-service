from __future__ import annotations

from typing import Any


class RepositoryScalars:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows
