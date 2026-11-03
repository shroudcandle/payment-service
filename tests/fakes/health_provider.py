from __future__ import annotations

from typing import cast

from dishka import Provider, Scope, provide
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment_service.config import AppSettings, SecuritySettings


class HealthProvider(Provider):
    scope = Scope.APP

    def __init__(
        self,
        session_factory: object,
        broker: object,
        *,
        health_timeout_seconds: float = 1.0,
    ) -> None:
        super().__init__()
        self._session_factory = session_factory
        self._broker = broker
        self._health_timeout_seconds = health_timeout_seconds

    @provide
    def app_settings(self) -> AppSettings:
        return AppSettings(
            _env_file=None,
            rabbitmq_health_timeout_seconds=self._health_timeout_seconds,
        )

    @provide
    def security_settings(self) -> SecuritySettings:
        return SecuritySettings(api_key="test-api-key")

    @provide
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return cast(async_sessionmaker[AsyncSession], self._session_factory)

    @provide
    def broker(self) -> RabbitBroker:
        return cast(RabbitBroker, self._broker)
