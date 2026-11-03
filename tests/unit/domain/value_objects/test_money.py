from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from payment_service.domain.payment import Currency, Money
from payment_service.domain.payment.exceptions import InvalidAmountError

_POSITIVE_AMOUNTS = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("1000000.00"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)
_NON_POSITIVE_AMOUNTS = st.decimals(
    max_value=Decimal("0"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


def test_money_quantizes_to_two_decimal_places() -> None:
    money = Money(Decimal("10.005"), Currency.RUB)
    assert money.amount == Decimal("10.00")
    assert money.currency is Currency.RUB


def test_money_rejects_non_positive_amount() -> None:
    with pytest.raises(InvalidAmountError):
        Money(Decimal("0.00"), Currency.USD)


def test_money_has_structural_equality() -> None:
    assert Money(Decimal("5.00"), Currency.EUR) == Money(Decimal("5.00"), Currency.EUR)
    assert Money(Decimal("5.00"), Currency.EUR) != Money(Decimal("5.01"), Currency.EUR)


def test_money_has_stable_hash() -> None:
    assert hash(Money(Decimal("5.00"), Currency.EUR)) == hash(Money(Decimal("5.00"), Currency.EUR))


def test_money_is_immutable() -> None:
    money = Money(Decimal("5.00"), Currency.EUR)

    with pytest.raises(FrozenInstanceError):
        money.amount = Decimal("6.00")


def test_money_repr_contains_amount_and_currency() -> None:
    assert repr(Money(Decimal("5.00"), Currency.EUR)) == "Money(5.00 EUR)"


@given(_POSITIVE_AMOUNTS)
def test_money_normalises_any_positive_amount_to_two_places(amount: Decimal) -> None:
    money = Money(amount, Currency.RUB)

    assert money.amount == amount.quantize(Decimal("0.01"))
    assert money.amount > Decimal("0.00")


@given(_NON_POSITIVE_AMOUNTS)
def test_money_rejects_any_non_positive_amount(amount: Decimal) -> None:
    with pytest.raises(InvalidAmountError):
        Money(amount, Currency.RUB)


@pytest.mark.parametrize(
    "amount",
    [
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_money_rejects_non_finite_amounts(amount: Decimal) -> None:
    with pytest.raises(InvalidAmountError):
        Money(amount, Currency.RUB)
