from __future__ import annotations

import asyncio

from dishka_faststream import setup_dishka
from faststream.rabbit import RabbitBroker

from payment_service.application.services import OutboxRelayService
from payment_service.config import Settings, configure_logging
from payment_service.di import make_container
from payment_service.infrastructure.messaging import declare_topology
from payment_service.presentation.consumers import register_payment_consumer
from payment_service.presentation.workers import WorkerRuntime, install_signal_handlers


async def _run(*, relay_restart_delay: float) -> None:
    container = make_container()
    broker = await container.get(RabbitBroker)
    relay = await container.get(OutboxRelayService)

    register_payment_consumer(broker)
    setup_dishka(container, broker=broker, auto_inject=True)
    await broker.start()
    await declare_topology(broker)

    stop_event = asyncio.Event()
    install_signal_handlers(stop_event)
    await WorkerRuntime(
        broker,
        relay,
        container,
        restart_delay=relay_restart_delay,
    ).run(stop_event)


def main() -> None:
    settings = Settings()
    configure_logging(settings.app.log_level)
    asyncio.run(_run(relay_restart_delay=settings.worker.relay_restart_delay_seconds))


if __name__ == "__main__":
    main()
