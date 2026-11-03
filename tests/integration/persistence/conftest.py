from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from docker.errors import DockerException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.infrastructure.persistence.declarative_base import Base
from payment_service.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    explicit_url = os.getenv("TEST_DATABASE_URL")
    if explicit_url:
        yield explicit_url
        return

    container = PostgresContainer("postgres:16-alpine", driver="asyncpg")
    try:
        container.start()
    except (DockerException, OSError) as exc:
        pytest.skip(f"Docker is not available for testcontainers: {exc}")
    try:
        yield container.get_connection_url()
    finally:
        container.stop()


@pytest.fixture
async def session_factory(
    database_url: str,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    yield factory
    await engine.dispose()


@pytest.fixture
def uow_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> UnitOfWorkFactoryPort:
    def build() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    return build
