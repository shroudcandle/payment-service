from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from payment_service.infrastructure.persistence.declarative_base import Base

_MONEY_PRECISION: Final = 12
_MONEY_SCALE: Final = 2
_CURRENCY_CODE_LENGTH: Final = 3
_DESCRIPTION_MAX_LENGTH: Final = 1024
_STATUS_MAX_LENGTH: Final = 16
_IDEMPOTENCY_KEY_MAX_LENGTH: Final = 255
_WEBHOOK_URL_MAX_LENGTH: Final = 2048


class PaymentTable(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(_MONEY_PRECISION, _MONEY_SCALE), nullable=False)
    currency: Mapped[str] = mapped_column(String(_CURRENCY_CODE_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(String(_DESCRIPTION_MAX_LENGTH), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(_STATUS_MAX_LENGTH), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(_IDEMPOTENCY_KEY_MAX_LENGTH), nullable=False
    )
    webhook_url: Mapped[str] = mapped_column(String(_WEBHOOK_URL_MAX_LENGTH), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
