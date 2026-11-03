from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from payment_service.application import (
    DuplicateIdempotencyKeyError,
    IdempotencyConflictError,
    PaymentNotFoundError,
)
from payment_service.domain.base import DomainError
from payment_service.domain.payment import (
    InvalidAmountError,
    InvalidDescriptionError,
    InvalidIdempotencyKeyError,
    InvalidWebhookUrlError,
)
from payment_service.presentation.api.v1.schemas import ErrorResponse

logger = logging.getLogger(__name__)

_UNPROCESSABLE_DOMAIN_ERRORS: tuple[type[DomainError], ...] = (
    InvalidAmountError,
    InvalidDescriptionError,
    InvalidIdempotencyKeyError,
    InvalidWebhookUrlError,
)

_INTERNAL_ERROR_DETAIL = "Internal server error"
_DATABASE_UNAVAILABLE_DETAIL = "Database service is temporarily unavailable"
_CONFLICT_DETAIL = "Request conflicts with stored data"


def _error_response(status_code: int, detail: str) -> JSONResponse:
    payload = ErrorResponse(detail=detail)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(IdempotencyConflictError)
    async def _idempotency_conflict(
        _request: Request, exc: IdempotencyConflictError
    ) -> JSONResponse:
        return _error_response(status.HTTP_409_CONFLICT, str(exc))

    @app.exception_handler(DuplicateIdempotencyKeyError)
    async def _duplicate_idempotency_key(
        _request: Request, exc: DuplicateIdempotencyKeyError
    ) -> JSONResponse:
        return _error_response(status.HTTP_409_CONFLICT, str(exc))

    @app.exception_handler(PaymentNotFoundError)
    async def _payment_not_found(_request: Request, exc: PaymentNotFoundError) -> JSONResponse:
        return _error_response(status.HTTP_404_NOT_FOUND, str(exc))

    @app.exception_handler(DomainError)
    async def _domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        code = (
            status.HTTP_422_UNPROCESSABLE_CONTENT
            if isinstance(exc, _UNPROCESSABLE_DOMAIN_ERRORS)
            else status.HTTP_400_BAD_REQUEST
        )
        return _error_response(code, str(exc))

    @app.exception_handler(OperationalError)
    async def _database_unavailable(request: Request, exc: OperationalError) -> JSONResponse:
        logger.error(
            "Database error while processing %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            _DATABASE_UNAVAILABLE_DETAIL,
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_conflict(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning(
            "Integrity error while processing %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return _error_response(status.HTTP_409_CONFLICT, _CONFLICT_DETAIL)

    @app.exception_handler(SQLAlchemyError)
    async def _database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error(
            "SQLAlchemy error while processing %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, _INTERNAL_ERROR_DETAIL)

    @app.exception_handler(Exception)
    async def _unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled error while processing %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            _INTERNAL_ERROR_DETAIL,
        )
