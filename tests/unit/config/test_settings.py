from __future__ import annotations

import pytest
from pydantic import ValidationError

from payment_service.config import (
    AppSettings,
    DatabaseSettings,
    HttpClientSettings,
    RabbitMQSettings,
    SecuritySettings,
    Settings,
    WorkerSettings,
)


def test_settings_build_all_sections_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "test-api-key")

    settings = Settings()

    assert isinstance(settings.app, AppSettings)
    assert isinstance(settings.database, DatabaseSettings)
    assert isinstance(settings.http, HttpClientSettings)
    assert isinstance(settings.rabbitmq, RabbitMQSettings)
    assert isinstance(settings.security, SecuritySettings)
    assert isinstance(settings.worker, WorkerSettings)
    assert settings.security.api_key == "test-api-key"


def test_settings_default_to_docker_service_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "DATABASE_URL",
        "RABBITMQ_USER",
        "RABBITMQ_PASSWORD",
        "RABBITMQ_HOST",
        "RABBITMQ_PORT",
        "RABBITMQ_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    database = DatabaseSettings(_env_file=None)
    rabbitmq = RabbitMQSettings(_env_file=None)

    assert database.host == "postgres"
    assert database.url == "postgresql+asyncpg://postgres:postgres@postgres:5432/payments_db"
    assert rabbitmq.host == "rabbitmq"
    assert rabbitmq.url == "amqp://guest:guest@rabbitmq:5672/"


def test_settings_build_urls_from_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RABBITMQ_URL", raising=False)

    database = DatabaseSettings(
        _env_file=None,
        user="app",
        password="p@ss word",
        database="payments",
        host="db.internal",
        port=6543,
    )
    rabbitmq = RabbitMQSettings(
        _env_file=None,
        user="app",
        password="secret",
        host="broker.internal",
        port=5673,
    )

    assert database.url == "postgresql+asyncpg://app:p%40ss+word@db.internal:6543/payments"
    assert rabbitmq.url == "amqp://app:secret@broker.internal:5673/"


def test_explicit_urls_override_parts() -> None:
    database = DatabaseSettings(
        _env_file=None,
        host="ignored",
        url="postgresql+asyncpg://u:p@explicit:5432/db",
    )
    rabbitmq = RabbitMQSettings(
        _env_file=None,
        host="ignored",
        url="amqp://u:p@explicit:5672/",
    )

    assert database.url == "postgresql+asyncpg://u:p@explicit:5432/db"
    assert rabbitmq.url == "amqp://u:p@explicit:5672/"


def test_settings_keep_injected_sections() -> None:
    app = AppSettings(run_migrations=False)
    database = DatabaseSettings(host="db.internal")
    http = HttpClientSettings(max_connections=7, max_keepalive_connections=5)
    rabbitmq = RabbitMQSettings(host="broker.internal")
    security = SecuritySettings(api_key="injected-key")
    worker = WorkerSettings(outbox_batch_size=7)

    settings = Settings(
        app=app,
        database=database,
        http=http,
        rabbitmq=rabbitmq,
        security=security,
        worker=worker,
    )

    assert settings.app is app
    assert settings.database is database
    assert settings.http is http
    assert settings.rabbitmq is rabbitmq
    assert settings.security is security
    assert settings.worker is worker


@pytest.mark.parametrize(
    "kwargs",
    [
        {"outbox_poll_interval": 0},
        {"outbox_batch_size": 0},
        {"outbox_lease_seconds": 0},
        {"relay_restart_delay_seconds": 0},
        {"webhook_timeout_seconds": 0},
        {"gateway_min_delay": -1},
        {"gateway_max_delay": -1},
        {"gateway_success_rate": 1.5},
        {"max_delivery_attempts": 0},
        {"retry_base": 0},
        {"retry_cap": 0},
        {"gateway_min_delay": 5.0, "gateway_max_delay": 1.0},
        {"retry_base": 10.0, "retry_cap": 1.0},
    ],
)
def test_worker_settings_reject_invalid_values(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        WorkerSettings(_env_file=None, **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"log_level": "LOUD"},
        {"api_port": 0},
        {"api_port": 70_000},
        {"rabbitmq_health_timeout_seconds": 0},
    ],
)
def test_app_settings_reject_invalid_values(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AppSettings(_env_file=None, **kwargs)


def test_security_settings_reject_empty_api_key() -> None:
    with pytest.raises(ValidationError):
        SecuritySettings(_env_file=None, api_key="")
