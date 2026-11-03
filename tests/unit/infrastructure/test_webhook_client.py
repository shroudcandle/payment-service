from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable

import httpx
import pytest
import respx

from payment_service.application.exceptions import (
    NonRetryableWebhookError,
    WebhookDeliveryError,
)
from payment_service.infrastructure.http import HttpxWebhookSender

URL = "https://example.com/hook"
PAYLOAD = {"event": "payment.updated", "status": "succeeded"}

SenderFactory = Callable[..., HttpxWebhookSender]


async def test_send_delivers_payload(make_sender: SenderFactory) -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock:
            route = respx.post(URL).mock(return_value=httpx.Response(200))

            await make_sender(client).send(URL, PAYLOAD)

    assert route.call_count == 1
    assert json.loads(route.calls[0].request.content) == PAYLOAD


async def test_client_error_is_non_retryable(make_sender: SenderFactory) -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock:
            route = respx.post(URL).mock(return_value=httpx.Response(404))

            with pytest.raises(NonRetryableWebhookError) as exc_info:
                await make_sender(client).send(URL, PAYLOAD)

    assert exc_info.value.status_code == 404
    assert route.call_count == 1


async def test_server_error_is_delivery_failure(make_sender: SenderFactory) -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock:
            route = respx.post(URL).mock(return_value=httpx.Response(503))

            with pytest.raises(WebhookDeliveryError, match="503"):
                await make_sender(client).send(URL, PAYLOAD)

    assert route.call_count == 1


@pytest.mark.parametrize("status_code", [301, 302, 307])
async def test_redirect_is_delivery_failure(
    make_sender: SenderFactory,
    status_code: int,
) -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock:
            respx.post(URL).mock(
                return_value=httpx.Response(status_code, headers={"Location": "https://evil.test"})
            )

            with pytest.raises(WebhookDeliveryError, match=str(status_code)):
                await make_sender(client).send(URL, PAYLOAD)


async def test_transport_error_is_wrapped(make_sender: SenderFactory) -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock:
            respx.post(URL).mock(side_effect=httpx.ConnectError("boom"))

            with pytest.raises(WebhookDeliveryError, match="boom"):
                await make_sender(client).send(URL, PAYLOAD)


async def test_send_propagates_correlation_id_header(make_sender: SenderFactory) -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock:
            route = respx.post(URL).mock(return_value=httpx.Response(202))

            await make_sender(client).send(URL, PAYLOAD, correlation_id="trace-1")

    assert route.calls[0].request.headers["X-Correlation-ID"] == "trace-1"


async def test_send_omits_correlation_header_without_id(make_sender: SenderFactory) -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock:
            route = respx.post(URL).mock(return_value=httpx.Response(200))

            await make_sender(client).send(URL, PAYLOAD)

    assert "X-Correlation-ID" not in route.calls[0].request.headers


@pytest.mark.allow_hosts(["127.0.0.1"])
async def test_hanging_socket_is_aborted_by_timeout() -> None:
    release = asyncio.Event()

    async def hanging_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await release.wait()
        writer.close()

    server = await asyncio.start_server(hanging_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            sender = HttpxWebhookSender(client, timeout_seconds=0.05)
            with pytest.raises(WebhookDeliveryError):
                await sender.send(f"http://127.0.0.1:{port}/hook", PAYLOAD)
    finally:
        release.set()
        server.close()
        await server.wait_closed()

    assert time.perf_counter() - started < 1.0
