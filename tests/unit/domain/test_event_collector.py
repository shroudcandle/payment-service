from __future__ import annotations

import uuid
from datetime import UTC, datetime

from payment_service.domain.base import EventCollector
from tests.fakes.sample_event import SampleEvent


def make_event() -> SampleEvent:
    return SampleEvent(payment_id=uuid.uuid4(), happened_at=datetime.now(UTC))


def test_new_collector_is_empty() -> None:
    collector = EventCollector()

    assert collector.peek() == ()
    assert len(collector) == 0
    assert list(collector) == []


def test_record_appends_event_in_order() -> None:
    collector = EventCollector()
    first = make_event()
    second = make_event()

    collector.record(first)
    collector.record(second)

    assert collector.peek() == (first, second)
    assert len(collector) == 2


def test_peek_does_not_drop_events() -> None:
    collector = EventCollector()
    event = make_event()
    collector.record(event)

    assert collector.peek() == (event,)
    assert collector.peek() == (event,)


def test_pull_returns_events_and_clears_collector() -> None:
    collector = EventCollector()
    event = make_event()
    collector.record(event)

    assert collector.pull() == (event,)
    assert collector.peek() == ()
    assert len(collector) == 0


def test_clear_discards_events() -> None:
    collector = EventCollector()
    collector.record(make_event())

    collector.clear()

    assert collector.peek() == ()


def test_iteration_yields_recorded_events() -> None:
    collector = EventCollector()
    first = make_event()
    second = make_event()
    collector.record(first)
    collector.record(second)

    assert list(collector) == [first, second]
