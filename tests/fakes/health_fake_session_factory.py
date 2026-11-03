from __future__ import annotations

from tests.fakes.health_fake_session import HealthFakeSession


class HealthFakeSessionFactory:
    def __init__(self, error: Exception | None) -> None:
        self._error = error

    def __call__(self) -> HealthFakeSession:
        return HealthFakeSession(self._error)
