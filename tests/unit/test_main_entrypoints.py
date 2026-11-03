from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from faststream.rabbit import RabbitBroker

import payment_service.main_api as main_api
import payment_service.main_worker as main_worker
from payment_service.application.services import OutboxRelayService
from tests.fakes.stub_broker import StubBroker


async def test_worker_entrypoint_wires_consumer_and_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker = StubBroker()
    relay = object()
    events: list[str] = []

    async def get(dependency: Any) -> Any:
        if dependency is RabbitBroker:
            return broker
        if dependency is OutboxRelayService:
            return relay
        raise AssertionError(f"unexpected dependency: {dependency}")

    async def close() -> None:
        events.append("closed")

    container = SimpleNamespace(get=get, close=close)

    async def declare_topology(declared_broker: object) -> None:
        events.append(f"topology:{declared_broker is broker}")

    async def run(runtime: object, stop_event: object) -> None:
        events.append(f"runtime:{runtime is relay}:{isinstance(stop_event, object)}")

    def runtime_factory(
        declared_broker: object,
        declared_relay: object,
        declared_container: object,
        *,
        restart_delay: float,
    ) -> SimpleNamespace:
        events.append(
            f"factory:{declared_broker is broker}:{declared_relay is relay}:"
            f"{declared_container is container}:{restart_delay}"
        )
        return SimpleNamespace(run=lambda stop_event: run(declared_relay, stop_event))

    def register(broker_to_register: object) -> None:
        events.append(f"register:{broker_to_register is broker}")

    def install(stop_event: object) -> None:
        events.append("signals")

    monkeypatch.setattr(main_worker, "make_container", lambda: container)
    monkeypatch.setattr(main_worker, "register_payment_consumer", register)
    monkeypatch.setattr(main_worker, "setup_dishka", lambda *a, **k: events.append("dishka"))
    monkeypatch.setattr(main_worker, "declare_topology", declare_topology)
    monkeypatch.setattr(main_worker, "install_signal_handlers", install)
    monkeypatch.setattr(main_worker, "WorkerRuntime", runtime_factory)

    await main_worker._run(relay_restart_delay=0.0)

    assert broker.started is True
    assert events == [
        "register:True",
        "dishka",
        "topology:True",
        "signals",
        "factory:True:True:True:0.0",
        "runtime:True:True",
    ]


def test_worker_main_configures_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    configured: list[str] = []
    executed: list[object] = []
    settings = SimpleNamespace(
        app=SimpleNamespace(log_level="INFO"),
        worker=SimpleNamespace(relay_restart_delay_seconds=5.0),
    )

    def fake_run(coroutine: object) -> None:
        executed.append(coroutine)
        coroutine.close()

    monkeypatch.setattr(main_worker, "Settings", lambda: settings)
    monkeypatch.setattr(main_worker, "configure_logging", configured.append)
    monkeypatch.setattr(main_worker.asyncio, "run", fake_run)

    main_worker.main()

    assert configured == ["INFO"]
    assert len(executed) == 1


def test_api_main_runs_uvicorn_with_configured_host(monkeypatch: pytest.MonkeyPatch) -> None:
    configured: list[str] = []
    calls: list[dict[str, object]] = []
    settings = SimpleNamespace(
        app=SimpleNamespace(
            log_level="WARNING",
            api_host="127.0.0.1",
            api_port=9000,
        )
    )

    monkeypatch.setattr(main_api, "Settings", lambda: settings)
    monkeypatch.setattr(main_api, "configure_logging", configured.append)
    monkeypatch.setattr(main_api.uvicorn, "run", lambda *a, **k: calls.append({"args": a, **k}))

    main_api.main()

    assert configured == ["WARNING"]
    assert calls == [
        {
            "args": ("payment_service.presentation.api.app:create_app",),
            "factory": True,
            "host": "127.0.0.1",
            "port": 9000,
            "log_level": "warning",
            "log_config": None,
        }
    ]
