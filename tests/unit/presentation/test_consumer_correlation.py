from __future__ import annotations

import logging
from typing import Any

import pytest

from payment_service.application.exceptions import WebhookDeliveryError
from payment_service.domain.payment import Payment
from tests.fakes.consumer_harness import ConsumerHarness
from tests.fakes.fake_webhook_sender import FakeWebhookSender


async def test_retry_preserves_correlation_id_from_header(
    harness: ConsumerHarness,
    seeded_payment: Payment,
    webhook_sender: FakeWebhookSender,
    caplog: pytest.LogCaptureFixture,
) -> None:
    webhook_sender.error = WebhookDeliveryError(str(seeded_payment.webhook_url), "timeout")

    await harness.publish(
        {"payment_id": str(seeded_payment.id)},
        headers={"x-retry-count": 0, "x-correlation-id": "trace-header"},
    )

    assert harness.retried[0].headers["x-correlation-id"] == "trace-header"
    assert webhook_sender.correlation_ids == ["trace-header"]
    with caplog.at_level(logging.WARNING):
        assert any(
            getattr(record, "correlation_id", None) == "trace-header" for record in caplog.records
        )


async def test_retry_falls_back_to_correlation_id_from_body(
    harness: ConsumerHarness,
    seeded_payment: Payment,
    webhook_sender: FakeWebhookSender,
) -> None:
    webhook_sender.error = WebhookDeliveryError(str(seeded_payment.webhook_url), "timeout")

    await harness.publish(
        {"payment_id": str(seeded_payment.id), "correlation_id": "trace-body"},
        headers={"x-retry-count": 0},
    )

    assert harness.retried[0].headers["x-correlation-id"] == "trace-body"
    assert webhook_sender.correlation_ids == ["trace-body"]


@pytest.mark.parametrize("header", [123, "", None])
async def test_non_string_header_uses_body_correlation_id(
    harness: ConsumerHarness,
    seeded_payment: Payment,
    webhook_sender: FakeWebhookSender,
    header: Any,
) -> None:
    webhook_sender.error = WebhookDeliveryError(str(seeded_payment.webhook_url), "timeout")

    await harness.publish(
        {"payment_id": str(seeded_payment.id), "correlation_id": "trace-body"},
        headers={"x-retry-count": 0, "x-correlation-id": header},
    )

    assert harness.retried[0].headers["x-correlation-id"] == "trace-body"


async def test_invalid_payload_dlq_preserves_correlation_id(
    harness: ConsumerHarness,
) -> None:
    await harness.publish(
        {"payment_id": "not-a-uuid", "correlation_id": "trace-invalid"},
        headers={"x-correlation-id": "trace-header"},
    )

    assert harness.dead[0].headers["x-correlation-id"] == "trace-header"


async def test_exhausted_retry_dlq_preserves_correlation_id(
    harness: ConsumerHarness,
    seeded_payment: Payment,
    webhook_sender: FakeWebhookSender,
) -> None:
    webhook_sender.error = WebhookDeliveryError(str(seeded_payment.webhook_url), "timeout")

    await harness.publish(
        {"payment_id": str(seeded_payment.id)},
        headers={"x-retry-count": 3, "x-correlation-id": "trace-dlq"},
    )

    assert harness.dead[0].headers["x-correlation-id"] == "trace-dlq"


async def test_missing_correlation_id_adds_no_header(
    harness: ConsumerHarness,
) -> None:
    await harness.publish({})

    assert len(harness.dead) == 1
    assert "x-correlation-id" not in harness.dead[0].headers
