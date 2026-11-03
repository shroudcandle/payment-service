from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aio_pika.exceptions import AMQPError
from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from faststream.rabbit import RabbitBroker

from payment_service import __version__
from payment_service.config import AppSettings, Settings
from payment_service.di import make_container
from payment_service.infrastructure.persistence import run_migrations
from payment_service.presentation.api.exception_handlers import register_exception_handlers
from payment_service.presentation.api.v1.routes import health, payments

logger = logging.getLogger(__name__)

_OPENAPI_TAGS = [
    {
        "name": "payments",
        "description": "Создание и просмотр платежей. Требует заголовок `X-API-Key`.",
    },
    {
        "name": "health",
        "description": "Проверка живости и доступности зависимостей.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: AsyncContainer = app.state.dishka_container
    settings = await container.get(Settings)
    if settings.app.run_migrations:
        logger.info("Applying database migrations")
        await asyncio.to_thread(run_migrations)
    broker = await container.get(RabbitBroker)
    try:
        await broker.start()
    except (AMQPError, OSError) as exc:
        logger.error(
            "RabbitMQ is unavailable at startup; API will serve reads and writes",
            exc_info=exc,
        )
    try:
        yield
    finally:
        await broker.stop()
        await container.close()


def create_app(container: AsyncContainer | None = None) -> FastAPI:
    container = container or make_container()
    app_settings = AppSettings()
    expose_docs = app_settings.app_env != "production"
    app = FastAPI(
        title="payment-service",
        version=__version__,
        openapi_tags=_OPENAPI_TAGS,
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        openapi_url="/openapi.json" if expose_docs else None,
        lifespan=lifespan,
    )
    setup_dishka(container, app)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(payments.router, prefix="/api/v1")
    return app
