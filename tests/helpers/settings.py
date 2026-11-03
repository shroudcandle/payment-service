from __future__ import annotations

from payment_service.config import AppSettings, SecuritySettings, Settings
from tests.helpers.constants import TEST_API_KEY


def make_settings(*, run_migrations: bool = False) -> Settings:
    return Settings(
        app=AppSettings(run_migrations=run_migrations),
        security=SecuritySettings(api_key=TEST_API_KEY),
    )
