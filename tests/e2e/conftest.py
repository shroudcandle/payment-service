from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

import aio_pika
import pytest
import uvicorn
from aio_pika.abc import AbstractIncomingMessage
from dishka import AsyncContainer
from dishka_faststream import setup_dishka
from fastapi import FastAPI, Request, Response
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.rabbitmq import RabbitMqContainer

from payment_service.application.services import OutboxRelayService
from payment_service.di import make_container
from payment_service.infrastructure.messaging import PAYMENTS_DLQ, declare_topology
from payment_service.presentation.api.app import create_app
from payment_service.presentation.consumers import register_payment_consumer
from tests.e2e.constants import API_KEY
from tests.e2e.webhook_receiver import WebhookReceiver
from tests.helpers.network import amqp_url, free_port, wait_for_amqp, wait_for_server


@pytest.fixture
async def infrastructure(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[str]:
    postgres = PostgresContainer("postgres:16-alpine", driver="asyncpg")
    rabbitmq = RabbitMqContainer("rabbitmq:3.13-alpine")
    postgres.start()
    rabbitmq.start()
    try:
        amqp_connection_url = amqp_url(rabbitmq)
        await wait_for_amqp(amqp_connection_url)
        database_url = postgres.get_connection_url()
        monkeypatch.setenv("API_KEY", API_KEY)
        monkeypatch.setenv("DATABASE_URL", database_url)
        monkeypatch.setenv("RABBITMQ_URL", amqp_connection_url)
        monkeypatch.setenv("RUN_MIGRATIONS", "true")
        monkeypatch.setenv("GATEWAY_MIN_DELAY", "0")
        monkeypatch.setenv("GATEWAY_MAX_DELAY", "0")
        monkeypatch.setenv("GATEWAY_SUCCESS_RATE", "1")
        monkeypatch.setenv("OUTBOX_POLL_INTERVAL", "0.05")
        monkeypatch.setenv("WEBHOOK_TIMEOUT_SECONDS", "2")
        monkeypatch.setenv("WEBHOOK_STRICT_SECURITY", "false")
        monkeypatch.setenv("WEBHOOK_ALLOWED_HOSTS", "")
        yield database_url
    finally:
        rabbitmq.stop()
        postgres.stop()


@pytest.fixture
async def api_server(infrastructure: str) -> AsyncIterator[str]:
    _ = infrastructure
    container: AsyncContainer = make_container()
    app = create_app(container)
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    task = asyncio.create_task(server.serve())
    try:
        await wait_for_server(server, task)
    except Exception:
        server.should_exit = True
        with suppress(Exception):
            await task
        raise
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    await task


@pytest.fixture
async def db_session(api_server: str, infrastructure: str) -> AsyncIterator[AsyncSession]:
    _ = api_server, infrastructure
    engine = create_async_engine(infrastructure)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def worker(infrastructure: str) -> AsyncIterator[None]:
    _ = infrastructure
    container = make_container()
    broker = await container.get(RabbitBroker)
    relay: OutboxRelayService = await container.get(OutboxRelayService)
    register_payment_consumer(broker)
    setup_dishka(container, broker=broker, auto_inject=True)
    await broker.start()
    await declare_topology(broker)
    relay_task = asyncio.create_task(relay.run_forever())
    try:
        yield
    finally:
        relay_task.cancel()
        with suppress(asyncio.CancelledError):
            await relay_task
        await broker.stop()
        await container.close()


@pytest.fixture
async def webhook_receiver() -> AsyncIterator[WebhookReceiver]:
    receiver = WebhookReceiver(url="")
    app = FastAPI()

    @app.post("/hook")
    async def hook(request: Request) -> Response:
        if receiver.should_fail():
            return Response(status_code=500)
        receiver.record(await request.json(), dict(request.headers))
        return Response(status_code=200)

    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    task = asyncio.create_task(server.serve())
    await wait_for_server(server, task)
    receiver.url = f"http://127.0.0.1:{port}/hook"
    yield receiver
    server.should_exit = True
    await task


@pytest.fixture
def gateway_failure(infrastructure: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _ = infrastructure
    monkeypatch.setenv("GATEWAY_SUCCESS_RATE", "0")


@pytest.fixture
def fast_webhook_retry(infrastructure: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _ = infrastructure
    monkeypatch.setenv("MAX_DELIVERY_ATTEMPTS", "1")


@pytest.fixture
async def dead_letters(
    infrastructure: str,
    worker: None,
) -> AsyncIterator[list[dict[str, Any]]]:
    _ = infrastructure, worker
    connection = await aio_pika.connect(os.environ["RABBITMQ_URL"])
    channel = await connection.channel()
    queue = await channel.declare_queue(PAYMENTS_DLQ.name, durable=True)
    messages: list[dict[str, Any]] = []

    async def on_message(message: AbstractIncomingMessage) -> None:
        async with message.process():
            messages.append(
                {
                    "body": json.loads(message.body),
                    "headers": dict(message.headers or {}),
                }
            )

    consumer_tag = await queue.consume(on_message)
    try:
        yield messages
    finally:
        await queue.cancel(consumer_tag)
        await connection.close()
