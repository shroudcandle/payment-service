from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from payment_service.infrastructure.http import HttpxWebhookSender
from tests.helpers.webhook import make_webhook_sender


@pytest.fixture
def make_sender() -> Callable[..., HttpxWebhookSender]:
    def build(client: httpx.AsyncClient) -> HttpxWebhookSender:
        return make_webhook_sender(client)

    return build
