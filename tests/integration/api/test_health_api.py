from __future__ import annotations

from aio_pika.exceptions import AMQPError

from tests.fakes.health_fake_broker import HealthFakeBroker
from tests.fakes.health_fake_session_factory import HealthFakeSessionFactory
from tests.helpers.health import HEADERS, get_health


async def test_health_returns_ok_when_dependencies_are_connected() -> None:
    status, body = await get_health(
        session_factory=HealthFakeSessionFactory(None),
        broker=HealthFakeBroker(connected=True),
    )

    assert status == 200
    assert body == {"status": "ok", "postgres": "connected", "rabbitmq": "connected"}


async def test_health_returns_503_when_postgres_is_down() -> None:
    status, body = await get_health(
        session_factory=HealthFakeSessionFactory(OSError("db down")),
        broker=HealthFakeBroker(connected=True),
    )

    assert status == 503
    assert body["status"] == "degraded"
    assert body["postgres"] == "disconnected"
    assert body["rabbitmq"] == "connected"


async def test_health_returns_503_when_rabbitmq_is_not_connected() -> None:
    status, body = await get_health(
        session_factory=HealthFakeSessionFactory(None),
        broker=HealthFakeBroker(connected=False),
    )

    assert status == 503
    assert body["status"] == "degraded"
    assert body["rabbitmq"] == "disconnected"


async def test_health_returns_503_when_rabbitmq_ping_fails() -> None:
    status, body = await get_health(
        session_factory=HealthFakeSessionFactory(None),
        broker=HealthFakeBroker(error=AMQPError("broker down")),
    )

    assert status == 503
    assert body["status"] == "degraded"
    assert body["rabbitmq"] == "disconnected"


async def test_ready_alias_reports_same_status() -> None:
    status, body = await get_health(
        session_factory=HealthFakeSessionFactory(None),
        broker=HealthFakeBroker(connected=True),
        path="/health/ready",
    )

    assert status == 200
    assert body["status"] == "ok"


async def test_liveness_is_ok_without_dependencies() -> None:
    status, body = await get_health(
        session_factory=HealthFakeSessionFactory(OSError("db down")),
        broker=HealthFakeBroker(connected=False),
        path="/health/live",
    )

    assert status == 200
    assert body == {"status": "ok"}


async def test_health_uses_configured_rabbitmq_timeout() -> None:
    broker = HealthFakeBroker(connected=True)

    status, _ = await get_health(
        session_factory=HealthFakeSessionFactory(None),
        broker=broker,
        health_timeout_seconds=2.5,
    )

    assert status == 200
    assert broker.last_timeout == 2.5


async def test_health_requires_api_key() -> None:
    status, body = await get_health(
        session_factory=HealthFakeSessionFactory(None),
        broker=HealthFakeBroker(connected=True),
        headers={},
    )

    assert status == 401
    assert body["detail"] == "Invalid or missing API key"


async def test_health_rejects_non_ascii_api_key() -> None:
    status, body = await get_health(
        session_factory=HealthFakeSessionFactory(None),
        broker=HealthFakeBroker(connected=True),
        headers={**HEADERS, "X-API-Key": b"\xff"},
    )

    assert status == 401
    assert body["detail"] == "Invalid or missing API key"
