from __future__ import annotations

import uuid
from typing import Any

import pytest

from payment_service.application.exceptions import WebhookDeliveryError
from payment_service.domain.payment import Payment, PaymentStatus
from tests.fakes.consumer_harness import ConsumerHarness
from tests.fakes.fake_webhook_sender import FakeWebhookSender


async def test_consumer_resolves_handler_from_dishka(
    harness: ConsumerHarness,
    seeded_payment: Payment,
    webhook_sender: FakeWebhookSender,
) -> None:
    await harness.publish({"payment_id": str(seeded_payment.id)})

    assert seeded_payment.status is PaymentStatus.SUCCEEDED
    assert len(webhook_sender.calls) == 1


async def test_unknown_payment_is_routed_to_dlq(
    harness: ConsumerHarness,
) -> None:
    await harness.publish({"payment_id": str(uuid.uuid4())})

    assert len(harness.dead) == 1
    assert harness.dead[0].headers["x-failure-reason"] == "payment not found"
    assert harness.retried == []


@pytest.mark.parametrize("body", [{}, {"payment_id": "not-a-uuid"}])
async def test_invalid_payload_is_routed_to_dlq(
    harness: ConsumerHarness,
    body: dict[str, Any],
) -> None:
    await harness.publish(body)

    assert len(harness.dead) == 1
    assert harness.dead[0].body == body
    assert harness.dead[0].headers["x-failure-reason"] == "invalid payload"


async def test_non_numeric_retry_header_falls_back_to_zero(
    harness: ConsumerHarness,
    seeded_payment: Payment,
    webhook_sender: FakeWebhookSender,
) -> None:
    await harness.publish({"payment_id": str(seeded_payment.id)}, headers={"x-retry-count": "bad"})

    assert seeded_payment.status is PaymentStatus.SUCCEEDED
    assert len(webhook_sender.calls) == 1
    assert harness.retried == []


async def test_webhook_delivery_error_schedules_retry(
    harness: ConsumerHarness,
    seeded_payment: Payment,
    webhook_sender: FakeWebhookSender,
) -> None:
    webhook_sender.error = WebhookDeliveryError(str(seeded_payment.webhook_url), "timeout")

    await harness.publish({"payment_id": str(seeded_payment.id)}, headers={"x-retry-count": 0})

    assert seeded_payment.status is PaymentStatus.SUCCEEDED
    assert len(harness.retried) == 1
    assert harness.retried[0].headers["x-retry-count"] == 1
    assert harness.retried[0].expiration == 2.0
    assert harness.dead == []


async def test_exhausted_webhook_attempts_are_routed_to_dlq(
    harness: ConsumerHarness,
    seeded_payment: Payment,
    webhook_sender: FakeWebhookSender,
) -> None:
    webhook_sender.error = WebhookDeliveryError(str(seeded_payment.webhook_url), "timeout")

    await harness.publish({"payment_id": str(seeded_payment.id)}, headers={"x-retry-count": 3})

    assert len(harness.dead) == 1
    assert "timeout" in harness.dead[0].headers["x-failure-reason"]
    assert harness.retried == []
