from __future__ import annotations

import asyncio
import uuid

import pytest

from payment_service.infrastructure.gateway import EmulatorPaymentGateway


@pytest.mark.parametrize(
    ("min_delay", "max_delay"),
    [(-0.1, 1.0), (2.0, 1.0)],
)
def test_gateway_rejects_invalid_delay_bounds(min_delay: float, max_delay: float) -> None:
    with pytest.raises(ValueError, match="delay bounds"):
        EmulatorPaymentGateway(
            min_delay=min_delay,
            max_delay=max_delay,
            success_rate=0.5,
        )


@pytest.mark.parametrize("success_rate", [-0.1, 1.1])
def test_gateway_rejects_invalid_success_rate(success_rate: float) -> None:
    with pytest.raises(ValueError, match="success_rate"):
        EmulatorPaymentGateway(
            min_delay=0.0,
            max_delay=0.0,
            success_rate=success_rate,
        )


async def test_gateway_always_succeeds_at_full_success_rate() -> None:
    gateway = EmulatorPaymentGateway(min_delay=0.0, max_delay=0.0, success_rate=1.0)

    result = await gateway.charge(uuid.uuid4())

    assert result.success is True


async def test_gateway_always_fails_at_zero_success_rate() -> None:
    gateway = EmulatorPaymentGateway(min_delay=0.0, max_delay=0.0, success_rate=0.0)

    result = await gateway.charge(uuid.uuid4())

    assert result.success is False


@pytest.mark.parametrize(("draw", "expected"), [(0, 1.0), (9_999, 2.9998)])
def test_gateway_delay_stays_within_configured_bounds(
    monkeypatch: pytest.MonkeyPatch,
    draw: int,
    expected: float,
) -> None:
    gateway = EmulatorPaymentGateway(min_delay=1.0, max_delay=3.0, success_rate=1.0)
    monkeypatch.setattr("secrets.randbelow", lambda _: draw)

    assert gateway._next_delay() == pytest.approx(expected)


@pytest.mark.parametrize(("draw", "expected"), [(8_999, True), (9_000, False)])
def test_gateway_success_threshold_matches_success_rate(
    monkeypatch: pytest.MonkeyPatch,
    draw: int,
    expected: bool,
) -> None:
    gateway = EmulatorPaymentGateway(min_delay=0.0, max_delay=0.0, success_rate=0.9)
    monkeypatch.setattr("secrets.randbelow", lambda _: draw)

    assert gateway._next_success() is expected


async def test_repeated_charge_reuses_cached_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = EmulatorPaymentGateway(min_delay=0.0, max_delay=0.0, success_rate=1.0)
    draws: list[bool] = []

    def draw() -> bool:
        draws.append(True)
        return True

    monkeypatch.setattr(gateway, "_next_success", draw)
    payment_id = uuid.uuid4()

    first = await gateway.charge(payment_id)
    second = await gateway.charge(payment_id)

    assert first == second
    assert len(draws) == 1


async def test_concurrent_charges_share_one_draw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = EmulatorPaymentGateway(min_delay=0.0, max_delay=0.0, success_rate=1.0)
    draws: list[bool] = []

    def draw() -> bool:
        draws.append(True)
        return True

    monkeypatch.setattr(gateway, "_next_success", draw)
    payment_id = uuid.uuid4()

    results = await asyncio.gather(*(gateway.charge(payment_id) for _ in range(5)))

    assert all(result.success for result in results)
    assert len(draws) == 1


async def test_cache_evicts_oldest_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = EmulatorPaymentGateway(min_delay=0.0, max_delay=0.0, success_rate=1.0)
    monkeypatch.setattr(EmulatorPaymentGateway, "_MAX_CACHE", 1)
    draws: list[bool] = []

    def draw() -> bool:
        draws.append(True)
        return True

    monkeypatch.setattr(gateway, "_next_success", draw)
    first_id = uuid.uuid4()

    await gateway.charge(first_id)
    await gateway.charge(uuid.uuid4())
    await gateway.charge(first_id)

    assert len(draws) == 3
