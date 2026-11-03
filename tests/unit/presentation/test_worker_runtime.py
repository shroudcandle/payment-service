from __future__ import annotations

import asyncio
import os
import signal
from unittest.mock import AsyncMock

import pytest
from aio_pika.exceptions import AMQPError
from sqlalchemy.exc import SQLAlchemyError

from payment_service.presentation.workers import (
    WorkerRuntime,
    install_signal_handlers,
    run_relay,
)


async def test_runtime_cancels_relay_and_closes_resources_on_stop() -> None:
    broker = AsyncMock()
    container = AsyncMock()
    relay = AsyncMock()
    relay.run_forever = AsyncMock(side_effect=_block_forever)
    stop_event = asyncio.Event()
    runtime = WorkerRuntime(broker, relay, container, restart_delay=0.0)

    task = asyncio.create_task(runtime.run(stop_event))
    await asyncio.sleep(0)
    stop_event.set()
    await asyncio.wait_for(task, timeout=1.0)

    broker.stop.assert_awaited_once()
    container.close.assert_awaited_once()
    assert relay.run_forever.await_count == 1


async def test_runtime_fails_fast_when_relay_crashes() -> None:
    broker = AsyncMock()
    container = AsyncMock()
    relay = AsyncMock()
    relay.run_forever = AsyncMock(side_effect=ValueError("relay bug"))
    stop_event = asyncio.Event()
    runtime = WorkerRuntime(broker, relay, container, restart_delay=0.0)

    with pytest.raises(ValueError, match="relay bug"):
        await asyncio.wait_for(runtime.run(stop_event), timeout=1.0)

    broker.stop.assert_awaited_once()
    container.close.assert_awaited_once()


@pytest.mark.parametrize(
    "error",
    [SQLAlchemyError("db down"), AMQPError("broker down"), OSError("socket reset")],
)
async def test_relay_restarts_after_infrastructure_failure(error: Exception) -> None:
    calls: list[int] = []
    recovered = asyncio.Event()

    async def run_forever() -> None:
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            raise error
        recovered.set()
        await _block_forever()

    relay = AsyncMock()
    relay.run_forever = run_forever
    task = asyncio.create_task(run_relay(relay, restart_delay=0.0))
    try:
        await asyncio.wait_for(recovered.wait(), timeout=1.0)
        assert len(calls) == 2
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_sigterm_sets_stop_event() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    install_signal_handlers(stop_event)
    try:
        os.kill(os.getpid(), signal.SIGTERM)
        await asyncio.wait_for(stop_event.wait(), timeout=1.0)
    finally:
        loop.remove_signal_handler(signal.SIGTERM)
        loop.remove_signal_handler(signal.SIGINT)


async def _block_forever() -> None:
    await asyncio.Event().wait()
