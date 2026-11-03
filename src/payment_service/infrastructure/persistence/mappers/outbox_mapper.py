from __future__ import annotations

from payment_service.domain.base import DomainEvent
from payment_service.domain.outbox import OutboxEvent, OutboxStatus
from payment_service.infrastructure.persistence.tables import OutboxTable


class OutboxMapper:
    @staticmethod
    def to_domain(row: OutboxTable) -> OutboxEvent:
        return OutboxEvent(
            id=row.id,
            event_type=row.event_type,
            routing_key=row.routing_key,
            payload=row.payload,
            status=OutboxStatus(row.status),
            retry_count=row.retry_count,
            created_at=row.created_at,
            error_log=row.error_log,
            processed_at=row.processed_at,
            next_attempt_at=row.next_attempt_at,
        )

    @staticmethod
    def to_table(event: DomainEvent) -> OutboxTable:
        outbox_event = OutboxEvent.from_domain_event(
            event_id=event.event_id,
            event_type=event.event_name(),
            routing_key=event.routing_key(),
            payload=event.to_primitives(),
            created_at=event.occurred_on,
        )
        return OutboxTable(
            id=outbox_event.id,
            event_type=outbox_event.event_type,
            routing_key=outbox_event.routing_key,
            payload=outbox_event.payload,
            status=outbox_event.status.value,
            retry_count=outbox_event.retry_count,
            created_at=outbox_event.created_at,
        )
