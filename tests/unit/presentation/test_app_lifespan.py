from __future__ import annotations

import pytest
from aio_pika.exceptions import AMQPError
from fastapi import FastAPI

import payment_service.presentation.api.app as app_module
from payment_service.presentation.api.app import create_app, lifespan
from tests.fakes.stub_broker import StubBroker
from tests.fakes.stub_container import StubContainer
from tests.helpers.settings import make_settings


@pytest.mark.parametrize(("run_migrations", "expected_calls"), [(True, 1), (False, 0)])
async def test_lifespan_conditionally_runs_migrations(
    monkeypatch: pytest.MonkeyPatch,
    run_migrations: bool,
    expected_calls: int,
) -> None:
    calls: list[None] = []

    def fake_run_migrations() -> None:
        calls.append(None)

    monkeypatch.setattr(app_module, "run_migrations", fake_run_migrations)
    broker = StubBroker()
    container = StubContainer(make_settings(run_migrations=run_migrations), broker)
    app = FastAPI()
    app.state.dishka_container = container

    async with lifespan(app):
        assert container.closed is False
        assert broker.started is True
        assert broker.stopped is False

    assert len(calls) == expected_calls
    assert broker.stopped is True
    assert container.closed is True


async def test_lifespan_survives_broker_start_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module, "run_migrations", lambda: None)
    broker = StubBroker(start_error=AMQPError("broker down"))
    container = StubContainer(make_settings(run_migrations=False), broker)
    app = FastAPI()
    app.state.dishka_container = container

    async with lifespan(app):
        assert broker.started is False

    assert broker.stopped is True
    assert container.closed is True


def test_production_disables_docs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    app = create_app(StubContainer(make_settings(), StubBroker()))

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


def test_development_exposes_docs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")

    app = create_app(StubContainer(make_settings(), StubBroker()))

    assert app.docs_url == "/docs"
    assert app.openapi_url == "/openapi.json"
