from __future__ import annotations

from alembic.config import Config

from alembic import command


def run_migrations(config_path: str = "alembic.ini") -> None:
    config = Config(config_path)
    command.upgrade(config, "head")
