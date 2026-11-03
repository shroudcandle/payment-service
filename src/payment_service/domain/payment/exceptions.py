from __future__ import annotations

from payment_service.domain.base import DomainError


class InvalidAmountError(DomainError):
    pass


class InvalidDescriptionError(DomainError):
    pass


class InvalidIdempotencyKeyError(DomainError):
    pass


class InvalidWebhookUrlError(DomainError):
    pass


class InvalidStateTransitionError(DomainError):
    pass
