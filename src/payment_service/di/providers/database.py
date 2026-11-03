from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.config import DatabaseSettings
from payment_service.infrastructure.persistence import (
    SqlAlchemyUnitOfWork,
    create_engine,
    create_session_factory,
)


class DatabaseProvider(Provider):
    scope = Scope.APP

    @provide
    async def engine(self, settings: DatabaseSettings) -> AsyncIterator[AsyncEngine]:
        engine = create_engine(settings)
        try:
            yield engine
        finally:
            await engine.dispose()

    @provide
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return create_session_factory(engine)

    @provide
    def uow_factory(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> UnitOfWorkFactoryPort:
        def build() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(session_factory)

        return build
