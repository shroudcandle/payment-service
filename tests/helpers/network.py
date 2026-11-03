from __future__ import annotations

import asyncio
import socket
from collections.abc import Awaitable, Callable

import aio_pika
import uvicorn
from aio_pika.exceptions import AMQPError
from testcontainers.community.rabbitmq import RabbitMqContainer


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def amqp_url(container: RabbitMqContainer) -> str:
    params = container.get_connection_params()
    vhost = "" if params.virtual_host in (None, "/") else params.virtual_host
    return (
        f"amqp://{params.credentials.username}:{params.credentials.password}"
        f"@{params.host}:{params.port}/{vhost}"
    )


async def wait_for_amqp(url: str, *, timeout: float = 60.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            connection = await aio_pika.connect(url, timeout=2)
        except (AMQPError, OSError, TimeoutError):
            await asyncio.sleep(0.5)
            continue
        await connection.close()
        return
    raise AssertionError("RabbitMQ did not become ready in time")


async def wait_for(
    predicate: Callable[[], Awaitable[bool]],
    *,
    timeout: float,
    message: str,
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if await predicate():
            return
        await asyncio.sleep(0.1)
    raise AssertionError(message)


async def wait_for_server(server: uvicorn.Server, task: asyncio.Task[None]) -> None:
    async def started() -> bool:
        if task.done():
            task.result()
        return server.started

    await wait_for(started, timeout=60.0, message="API server failed to start")
