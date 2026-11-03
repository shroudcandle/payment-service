from __future__ import annotations

import logging

from aio_pika.exceptions import AMQPError
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Response, status
from faststream.rabbit import RabbitBroker
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment_service.config import AppSettings
from payment_service.presentation.api.auth import verify_api_key
from payment_service.presentation.api.v1.schemas import (
    ComponentStatus,
    HealthResponse,
    LivenessResponse,
    OverallStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["health"],
    route_class=DishkaRoute,
    dependencies=[Depends(verify_api_key)],
)


@router.get(
    "/health/live",
    response_model=LivenessResponse,
    summary="Живость процесса",
    description="Всегда отвечает 200, пока процесс API способен обрабатывать запросы.",
)
async def live() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Готовность сервиса",
    description="Сообщает о доступности PostgreSQL и RabbitMQ; при сбое возвращает 503.",
)
async def health(
    response: Response,
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
    broker: FromDishka[RabbitBroker],
    settings: FromDishka[AppSettings],
) -> HealthResponse:
    postgres = await _check_postgres(session_factory)
    rabbitmq = await _check_rabbitmq(broker, settings.rabbitmq_health_timeout_seconds)
    overall: OverallStatus = (
        "ok" if postgres == "connected" and rabbitmq == "connected" else "degraded"
    )
    if overall != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status=overall, postgres=postgres, rabbitmq=rabbitmq)


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    include_in_schema=False,
)
async def ready(
    response: Response,
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
    broker: FromDishka[RabbitBroker],
    settings: FromDishka[AppSettings],
) -> HealthResponse:
    return await health(response, session_factory, broker, settings)


async def _check_postgres(
    session_factory: async_sessionmaker[AsyncSession],
) -> ComponentStatus:
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        logger.warning("PostgreSQL health check failed", exc_info=True)
        return "disconnected"
    return "connected"


async def _check_rabbitmq(broker: RabbitBroker, timeout_seconds: float) -> ComponentStatus:
    try:
        connected = await broker.ping(timeout=timeout_seconds)
    except (AMQPError, OSError, RuntimeError):
        logger.warning("RabbitMQ health check failed", exc_info=True)
        return "disconnected"
    return "connected" if connected else "disconnected"
