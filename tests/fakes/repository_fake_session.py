from __future__ import annotations

from typing import Any

from tests.fakes.repository_scalars import RepositoryScalars


class RepositoryFakeSession:
    def __init__(
        self,
        *,
        row: Any = None,
        rows: list[Any] | None = None,
        flush_error: Exception | None = None,
    ) -> None:
        self._row = row
        self._rows = rows or []
        self._flush_error = flush_error
        self.added: list[Any] = []
        self.executed: list[Any] = []

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        if self._flush_error is not None:
            raise self._flush_error

    async def get(self, model: Any, identifier: Any) -> Any:
        _ = model, identifier
        return self._row

    async def scalar(self, statement: Any) -> Any:
        _ = statement
        return self._row

    async def scalars(self, statement: Any) -> RepositoryScalars:
        _ = statement
        return RepositoryScalars(self._rows)

    async def execute(self, statement: Any) -> None:
        self.executed.append(statement)
