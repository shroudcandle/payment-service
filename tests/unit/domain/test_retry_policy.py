from __future__ import annotations

from payment_service.domain.outbox import decide_retry


def test_decide_retry_returns_exponential_backoff() -> None:
    decision = decide_retry(attempt=0, max_attempts=3, base=2.0, cap=30.0)
    assert decision.should_retry
    assert decision.next_attempt == 1
    assert decision.delay_seconds == 2.0
    assert decision.delay_ms == 2000


def test_decide_retry_caps_delay() -> None:
    decision = decide_retry(attempt=5, max_attempts=10, base=2.0, cap=30.0)
    assert decision.delay_seconds == 30.0


def test_decide_retry_moves_to_dlq_after_limit() -> None:
    decision = decide_retry(attempt=3, max_attempts=3, base=2.0, cap=30.0)
    assert not decision.should_retry
    assert decision.action == "dlq"
    assert decision.delay_ms == 0


def test_decide_retry_saturates_instead_of_overflowing() -> None:
    decision = decide_retry(attempt=10_000, max_attempts=10_001, base=10.0, cap=30.0)

    assert decision.should_retry
    assert decision.delay_seconds == 30.0
