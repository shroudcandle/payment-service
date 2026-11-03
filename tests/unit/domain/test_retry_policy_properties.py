from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from payment_service.domain.outbox import decide_retry

_ATTEMPTS = st.integers(min_value=0, max_value=1_000)
_MAX_ATTEMPTS = st.integers(min_value=1, max_value=100)
_BASES = st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False)
_CAPS = st.floats(min_value=0.01, max_value=120.0, allow_nan=False, allow_infinity=False)


@settings(max_examples=200, deadline=None)
@given(
    attempt=_ATTEMPTS,
    max_attempts=_MAX_ATTEMPTS,
    base=_BASES,
    cap=_CAPS,
)
def test_retry_decision_respects_attempt_limit(
    attempt: int,
    max_attempts: int,
    base: float,
    cap: float,
) -> None:
    decision = decide_retry(attempt, max_attempts, base, cap)

    if attempt < max_attempts:
        assert decision.should_retry
        assert decision.action == "retry"
        assert decision.next_attempt == attempt + 1
        assert 0.0 < decision.delay_seconds <= cap
        assert decision.delay_ms == int(decision.delay_seconds * 1000)
    else:
        assert not decision.should_retry
        assert decision.action == "dlq"
        assert decision.next_attempt == attempt
        assert decision.delay_seconds == 0.0
        assert decision.delay_ms == 0


@settings(max_examples=200, deadline=None)
@given(
    attempt=st.integers(min_value=0, max_value=90),
    max_attempts=st.integers(min_value=2, max_value=100),
    base=_BASES,
    cap=_CAPS,
)
def test_backoff_is_monotonic_until_cap(
    attempt: int,
    max_attempts: int,
    base: float,
    cap: float,
) -> None:
    current = decide_retry(attempt, max_attempts, base, cap)
    following = decide_retry(attempt + 1, max_attempts, base, cap)

    if following.should_retry:
        assert current.delay_seconds <= following.delay_seconds <= cap
