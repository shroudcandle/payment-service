from __future__ import annotations

import pytest

from payment_service.application.commands.create_payment.handler import CreatePaymentHandler
from payment_service.application.ports import UnitOfWorkFactoryPort
from payment_service.application.services import WebhookPolicy
from payment_service.domain.payment import InvalidWebhookUrlError, WebhookUrl
from tests.factories import make_create_payment_command


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/hook",
        "http://127.0.0.1/hook",
        "https://example.com/hook",
    ],
)
def test_permissive_policy_accepts_any_http_url(url: str) -> None:
    WebhookPolicy.permissive().validate(WebhookUrl(url))


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/hook",
        "https://user:secret@example.com/hook",
        "https://localhost/hook",
        "https://api.internal/hook",
        "https://service.local/hook",
        "https://127.0.0.1/hook",
        "https://10.0.0.1/hook",
        "https://172.16.0.1/hook",
        "https://192.168.1.10/hook",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/hook",
        "https://0.0.0.0/hook",
        "https://224.0.0.1/hook",
        "https://192.0.2.1/hook",
    ],
)
def test_strict_policy_rejects_unsafe_targets(url: str) -> None:
    with pytest.raises(InvalidWebhookUrlError):
        WebhookPolicy.strict_for().validate(WebhookUrl(url))


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/hook",
        "https://api.example.com/hook",
        "https://8.8.8.8/hook",
    ],
)
def test_strict_policy_accepts_public_https(url: str) -> None:
    WebhookPolicy.strict_for().validate(WebhookUrl(url))


def test_strict_policy_honours_allowlist() -> None:
    policy = WebhookPolicy.strict_for("example.com, api.example.com")

    policy.validate(WebhookUrl("https://api.example.com/hook"))
    with pytest.raises(InvalidWebhookUrlError):
        policy.validate(WebhookUrl("https://other.example.com/hook"))


async def test_handler_rejects_unsafe_webhook_in_strict_mode(
    uow_factory: UnitOfWorkFactoryPort,
) -> None:
    handler = CreatePaymentHandler(uow_factory, WebhookPolicy.strict_for())

    with pytest.raises(InvalidWebhookUrlError):
        await handler.handle(make_create_payment_command(webhook_url="http://localhost/hook"))


async def test_handler_accepts_https_webhook_in_strict_mode(
    uow_factory: UnitOfWorkFactoryPort,
) -> None:
    handler = CreatePaymentHandler(uow_factory, WebhookPolicy.strict_for())

    result = await handler.handle(
        make_create_payment_command(webhook_url="https://example.com/hook")
    )

    assert result.payment_id is not None
