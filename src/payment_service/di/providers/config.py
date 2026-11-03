from __future__ import annotations

from dishka import Provider, Scope, provide

from payment_service.config import (
    AppSettings,
    DatabaseSettings,
    HttpClientSettings,
    RabbitMQSettings,
    SecuritySettings,
    Settings,
    WorkerSettings,
)


class ConfigProvider(Provider):
    scope = Scope.APP

    @provide
    def settings(self) -> Settings:
        return Settings()

    @provide
    def app_settings(self, settings: Settings) -> AppSettings:
        return settings.app

    @provide
    def database_settings(self, settings: Settings) -> DatabaseSettings:
        return settings.database

    @provide
    def http_settings(self, settings: Settings) -> HttpClientSettings:
        return settings.http

    @provide
    def rabbitmq_settings(self, settings: Settings) -> RabbitMQSettings:
        return settings.rabbitmq

    @provide
    def security_settings(self, settings: Settings) -> SecuritySettings:
        return settings.security

    @provide
    def worker_settings(self, settings: Settings) -> WorkerSettings:
        return settings.worker
