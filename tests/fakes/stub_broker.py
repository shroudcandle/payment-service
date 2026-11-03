from __future__ import annotations


class StubBroker:
    def __init__(self, start_error: Exception | None = None) -> None:
        self.started = False
        self.stopped = False
        self._start_error = start_error

    async def start(self) -> None:
        if self._start_error is not None:
            raise self._start_error
        self.started = True

    async def stop(self) -> None:
        self.stopped = True
