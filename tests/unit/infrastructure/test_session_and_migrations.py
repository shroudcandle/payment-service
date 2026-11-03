from __future__ import annotations

from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import payment_service.infrastructure.persistence.migrations as migrations_module
from payment_service.config import DatabaseSettings
from payment_service.infrastructure.persistence.session import (
    create_engine,
    create_session_factory,
)


def test_create_engine_uses_database_settings() -> None:
    settings = DatabaseSettings(
        url="postgresql+asyncpg://user:pass@db:5432/payments",
        echo=True,
    )
    engine = create_engine(settings)

    assert engine.url.render_as_string(hide_password=False) == settings.url
    assert engine.echo is True


async def test_create_session_factory_disables_expire_and_autoflush() -> None:
    engine = create_engine(DatabaseSettings())

    session_factory = create_session_factory(engine)

    assert isinstance(session_factory, async_sessionmaker)
    assert isinstance(session_factory(), AsyncSession)
    assert session_factory.kw["expire_on_commit"] is False
    assert session_factory.kw["autoflush"] is False
    await engine.dispose()


def test_run_migrations_upgrades_to_head(monkeypatch) -> None:
    calls: list[tuple[Config, str]] = []

    def fake_upgrade(config: Config, revision: str) -> None:
        calls.append((config, revision))

    monkeypatch.setattr(migrations_module.command, "upgrade", fake_upgrade)

    migrations_module.run_migrations("alembic.ini")

    assert len(calls) == 1
    config, revision = calls[0]
    assert isinstance(config, Config)
    assert revision == "head"
