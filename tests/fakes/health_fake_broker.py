from __future__ import annotations


class HealthFakeBroker:
    def __init__(self, *, connected: bool = True, error: Exception | None = None) -> None:
        self._connected = connected
        self._error = error
        self.last_timeout: float | None = None

    async def ping(self, timeout: float) -> bool:
        self.last_timeout = timeout
        if self._error is not None:
            raise self._error
        return self._connected
