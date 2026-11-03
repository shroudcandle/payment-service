from __future__ import annotations

from tests.fakes.uow_fake_session import UowFakeSession


class UowFakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[UowFakeSession] = []

    def __call__(self) -> UowFakeSession:
        session = UowFakeSession()
        self.sessions.append(session)
        return session
