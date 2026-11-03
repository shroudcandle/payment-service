from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from payment_service.application.exceptions import (
    DuplicateIdempotencyKeyError,
    PaymentNotFoundError,
)
from payment_service.domain.base import AggregateRoot
from payment_service.domain.outbox import OutboxStatus
from payment_service.domain.payment import IdempotencyKey
from payment_service.infrastructure.persistence.repositories import (
    SqlAlchemyOutboxRepository,
    SqlAlchemyPaymentReader,
    SqlAlchemyPaymentWriter,
)
from payment_service.infrastructure.persistence.tables import PaymentTable
from tests.fakes.repository_fake_session import RepositoryFakeSession
from tests.helpers.payments import NOW, make_payment
from tests.helpers.persistence import make_outbox_table, make_payment_table


async def test_writer_adds_and_tracks_payment() -> None:
    payment = make_payment(now=NOW)
    session = RepositoryFakeSession()
    tracked: list[AggregateRoot[uuid.UUID]] = []

    await SqlAlchemyPaymentWriter(session, tracked.append).add(payment)

    assert isinstance(session.added[0], PaymentTable)
    assert tracked == [payment]


async def test_writer_translates_idempotency_violation() -> None:
    violation = ValueError(
        'duplicate key value violates unique constraint "uq_payments_idempotency_key"'
    )
    session = RepositoryFakeSession(flush_error=IntegrityError("INSERT", {}, violation))
    payment = make_payment(now=NOW)

    with pytest.raises(DuplicateIdempotencyKeyError):
        await SqlAlchemyPaymentWriter(session, lambda _: None).add(payment)


async def test_writer_reraises_unrelated_integrity_error() -> None:
    violation = ValueError('new row violates check constraint "ck_payments_amount_positive"')
    session = RepositoryFakeSession(flush_error=IntegrityError("INSERT", {}, violation))
    payment = make_payment(now=NOW)

    with pytest.raises(IntegrityError):
        await SqlAlchemyPaymentWriter(session, lambda _: None).add(payment)


async def test_writer_updates_existing_row() -> None:
    payment = make_payment(now=NOW)
    row = make_payment_table(payment)
    session = RepositoryFakeSession(row=row)
    payment.complete_success(NOW)

    await SqlAlchemyPaymentWriter(session, lambda _: None).update(payment)

    assert row.status == "succeeded"
    assert row.processed_at == NOW


async def test_writer_rejects_update_of_missing_payment() -> None:
    session = RepositoryFakeSession(row=None)

    with pytest.raises(PaymentNotFoundError):
        await SqlAlchemyPaymentWriter(session, lambda _: None).update(make_payment(now=NOW))


async def test_writer_reads_by_id_and_idempotency_key() -> None:
    payment = make_payment(now=NOW)
    session = RepositoryFakeSession(row=make_payment_table(payment))
    writer = SqlAlchemyPaymentWriter(session, lambda _: None)

    assert (await writer.get_by_id(payment.id)) is not None
    assert (await writer.get_by_idempotency_key(IdempotencyKey("key-1"))) is not None


async def test_writer_returns_none_when_payment_is_missing() -> None:
    writer = SqlAlchemyPaymentWriter(RepositoryFakeSession(row=None), lambda _: None)

    assert await writer.get_by_id(uuid.uuid4()) is None
    assert await writer.get_by_idempotency_key(IdempotencyKey("missing")) is None


async def test_reader_returns_view_or_none() -> None:
    payment = make_payment(now=NOW)
    reader = SqlAlchemyPaymentReader(RepositoryFakeSession(row=make_payment_table(payment)))
    missing_reader = SqlAlchemyPaymentReader(RepositoryFakeSession(row=None))

    view = await reader.get_view_by_id(payment.id)

    assert view is not None
    assert view.id == payment.id
    assert await missing_reader.get_view_by_id(uuid.uuid4()) is None


async def test_outbox_claim_sets_lease_and_returns_events() -> None:
    row = make_outbox_table()
    session = RepositoryFakeSession(rows=[row])
    repository = SqlAlchemyOutboxRepository(session)

    events = await repository.claim_pending(10, NOW, 30.0)

    assert len(events) == 1
    assert row.next_attempt_at == NOW + timedelta(seconds=30)
    assert events[0].status is OutboxStatus.PENDING


async def test_outbox_mark_methods_execute_updates() -> None:
    session = RepositoryFakeSession()
    repository = SqlAlchemyOutboxRepository(session)
    event_id = uuid.uuid4()

    await repository.mark_published(event_id, NOW)
    await repository.mark_retry(event_id, "retry", NOW)
    await repository.mark_failed(event_id, "failed", NOW)

    assert len(session.executed) == 3
