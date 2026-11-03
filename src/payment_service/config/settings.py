from __future__ import annotations

from payment_service.config.app import AppSettings
from payment_service.config.database import DatabaseSettings
from payment_service.config.http_client import HttpClientSettings
from payment_service.config.rabbitmq import RabbitMQSettings
from payment_service.config.security import SecuritySettings
from payment_service.config.worker import WorkerSettings


class Settings:
    def __init__(
        self,
        app: AppSettings | None = None,
        database: DatabaseSettings | None = None,
        http: HttpClientSettings | None = None,
        rabbitmq: RabbitMQSettings | None = None,
        security: SecuritySettings | None = None,
        worker: WorkerSettings | None = None,
    ) -> None:
        self.app = app or AppSettings()
        self.database = database or DatabaseSettings()
        self.http = http or HttpClientSettings()
        self.rabbitmq = rabbitmq or RabbitMQSettings()
        self.security = security or SecuritySettings()
        self.worker = worker or WorkerSettings()
