from __future__ import annotations

from typing import Protocol

from payment_service.application.ports.unit_of_work import UnitOfWorkPort


class UnitOfWorkFactoryPort(Protocol):
    def __call__(self) -> UnitOfWorkPort: ...
