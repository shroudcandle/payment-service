from __future__ import annotations

import pytest

from payment_service.domain.payment.exceptions import InvalidWebhookUrlError
from payment_service.domain.payment.value_objects.webhook_url import WebhookUrl


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/hook",
        "http://example.com",
        "https://example.com:8443/path?query=1",
    ],
)
def test_webhook_url_accepts_http_and_https(value: str) -> None:
    url = WebhookUrl(value)

    assert url.value == value
    assert str(url) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-a-url",
        "example.com/hook",
        "ftp://example.com/hook",
        "javascript:alert(1)",
        "https://",
        "//example.com/hook",
    ],
)
def test_webhook_url_rejects_invalid_urls(value: str) -> None:
    with pytest.raises(InvalidWebhookUrlError):
        WebhookUrl(value)


def test_webhook_url_is_immutable() -> None:
    url = WebhookUrl("https://example.com/hook")

    with pytest.raises(AttributeError):
        url.value = "https://other.example"


def test_webhook_url_has_structural_equality_and_hash() -> None:
    assert WebhookUrl("https://example.com/hook") == WebhookUrl("https://example.com/hook")
    assert WebhookUrl("https://example.com/hook") != WebhookUrl("https://example.com/other")
    assert (
        len({WebhookUrl("https://example.com/hook"), WebhookUrl("https://example.com/hook")}) == 1
    )
