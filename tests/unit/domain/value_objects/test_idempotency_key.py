from __future__ import annotations

import pytest

from payment_service.domain.payment.exceptions import InvalidIdempotencyKeyError
from payment_service.domain.payment.value_objects.idempotency_key import IdempotencyKey


@pytest.mark.parametrize("value", ["key-1", "a", "x" * IdempotencyKey.MAX_LENGTH])
def test_idempotency_key_accepts_valid_values(value: str) -> None:
    key = IdempotencyKey(value)

    assert key.value == value
    assert str(key) == value


@pytest.mark.parametrize("value", ["", " ", "\t\n"])
def test_idempotency_key_rejects_blank_values(value: str) -> None:
    with pytest.raises(InvalidIdempotencyKeyError):
        IdempotencyKey(value)


def test_idempotency_key_rejects_values_longer_than_max_length() -> None:
    with pytest.raises(InvalidIdempotencyKeyError):
        IdempotencyKey("x" * (IdempotencyKey.MAX_LENGTH + 1))


def test_idempotency_key_is_immutable() -> None:
    key = IdempotencyKey("key-1")

    with pytest.raises(AttributeError):
        key.value = "other"


def test_idempotency_key_has_structural_equality_and_hash() -> None:
    assert IdempotencyKey("key-1") == IdempotencyKey("key-1")
    assert IdempotencyKey("key-1") != IdempotencyKey("key-2")
    assert len({IdempotencyKey("key-1"), IdempotencyKey("key-1")}) == 1
