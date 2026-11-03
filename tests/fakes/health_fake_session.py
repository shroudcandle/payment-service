from __future__ import annotations


class HealthFakeSession:
    def __init__(self, error: Exception | None) -> None:
        self._error = error

    async def __aenter__(self) -> HealthFakeSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def execute(self, statement: object) -> None:
        _ = statement
        if self._error is not None:
            raise self._error
