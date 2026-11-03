from __future__ import annotations

from payment_service.application.ports import UnitOfWorkFactoryPort
from tests.fakes.commit_race_unit_of_work import CommitRaceUnitOfWork
from tests.fakes.store import InMemoryStore


def make_racing_factory(
    *stores: InMemoryStore,
) -> tuple[UnitOfWorkFactoryPort, list[CommitRaceUnitOfWork]]:
    created: list[CommitRaceUnitOfWork] = []
    remaining = list(stores)

    def build() -> CommitRaceUnitOfWork:
        store = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        uow = CommitRaceUnitOfWork(store)
        created.append(uow)
        return uow

    return build, created
