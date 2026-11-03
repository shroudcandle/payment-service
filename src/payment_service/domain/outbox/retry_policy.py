from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DEFAULT_RETRY_BASE = 2.0
DEFAULT_RETRY_CAP = 30.0
_MS_PER_SECOND = 1000

RetryAction = Literal["retry", "dlq"]


@dataclass(frozen=True, slots=True)
class RetryDecision:
    action: RetryAction
    next_attempt: int
    delay_seconds: float

    @property
    def delay_ms(self) -> int:
        return int(self.delay_seconds * _MS_PER_SECOND)

    @property
    def should_retry(self) -> bool:
        return self.action == "retry"


def decide_retry(attempt: int, max_attempts: int, base: float, cap: float) -> RetryDecision:
    if attempt < max_attempts:
        next_attempt = attempt + 1
        try:
            delay = base**next_attempt
        except OverflowError:
            delay = cap
        return RetryDecision("retry", next_attempt, min(cap, delay))
    return RetryDecision("dlq", attempt, 0.0)
