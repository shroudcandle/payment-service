from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

from aio_pika.exceptions import AMQPError
from dishka import AsyncContainer
from faststream.rabbit import RabbitBroker
from sqlalchemy.exc import SQLAlchemyError

from payment_service.application.services import OutboxRelayService

logger = logging.getLogger(__name__)


async def run_relay(
    relay: OutboxRelayService,
    *,
    restart_delay: float,
) -> None:
    while True:
        try:
            await relay.run_forever()
        except (SQLAlchemyError, AMQPError, OSError):
            logger.error("Outbox relay crashed; restarting in %ss", restart_delay, exc_info=True)
            await asyncio.sleep(restart_delay)


def install_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for registered_signal in (signal.SIGTERM, signal.SIGINT):
        with suppress(NotImplementedError):
            loop.add_signal_handler(registered_signal, stop_event.set)


class WorkerRuntime:
    def __init__(
        self,
        broker: RabbitBroker,
        relay: OutboxRelayService,
        container: AsyncContainer,
        *,
        restart_delay: float,
    ) -> None:
        self._broker = broker
        self._relay = relay
        self._container = container
        self._restart_delay = restart_delay

    async def run(self, stop_event: asyncio.Event) -> None:
        relay_task = asyncio.create_task(run_relay(self._relay, restart_delay=self._restart_delay))
        stop_task = asyncio.create_task(stop_event.wait())
        try:
            done, _ = await asyncio.wait(
                {relay_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if relay_task in done and not relay_task.cancelled():
                relay_task.result()
        finally:
            for task in (relay_task, stop_task):
                if not task.done():
                    task.cancel()
            for task in (relay_task, stop_task):
                if task.done():
                    continue
                with suppress(asyncio.CancelledError):
                    await task
            await self._broker.stop()
            await self._container.close()
