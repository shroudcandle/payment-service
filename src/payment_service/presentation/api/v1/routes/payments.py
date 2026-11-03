from __future__ import annotations

import logging
import uuid
from typing import Annotated, Final

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Header, Path, Response, status

from payment_service.application.commands import (
    CreatePaymentCommand,
    CreatePaymentHandler,
)
from payment_service.application.queries import GetPaymentHandler, GetPaymentQuery
from payment_service.presentation.api.auth import verify_api_key
from payment_service.presentation.api.v1.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    ErrorResponse,
    PaymentDetailResponse,
)

_IDEMPOTENCY_KEY_MAX_LENGTH: Final = 255
_CORRELATION_ID_MAX_LENGTH: Final = 128

_UNAUTHORIZED_RESPONSE = {
    "model": ErrorResponse,
    "description": "Неверный или отсутствующий заголовок X-API-Key",
}
_INTERNAL_ERROR_RESPONSE = {
    "model": ErrorResponse,
    "description": "Непредвиденная внутренняя ошибка",
}
_DATABASE_UNAVAILABLE_RESPONSE = {
    "model": ErrorResponse,
    "description": "База данных временно недоступна",
}

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    dependencies=[Depends(verify_api_key)],
    route_class=DishkaRoute,
)


@router.post(
    "",
    response_model=CreatePaymentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Создать платёж",
    description=(
        "Принимает платёж в асинхронную обработку. Запрос идемпотентен: повтор с тем же "
        "Idempotency-Key и идентичным телом возвращает уже созданный платёж, а другое тело "
        "с тем же ключом отклоняется."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Некорректные данные платежа"},
        401: _UNAUTHORIZED_RESPONSE,
        409: {
            "model": ErrorResponse,
            "description": "Idempotency-Key повторно использован с другими данными платежа",
        },
        500: _INTERNAL_ERROR_RESPONSE,
        503: _DATABASE_UNAVAILABLE_RESPONSE,
    },
)
async def create_payment(
    body: CreatePaymentRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=_IDEMPOTENCY_KEY_MAX_LENGTH,
            description="Ключ клиента для дедупликации создания платежа",
            examples=["order-123"],
        ),
    ],
    response: Response,
    handler: FromDishka[CreatePaymentHandler],
    x_request_id: Annotated[
        str | None,
        Header(
            alias="X-Request-ID",
            min_length=1,
            max_length=_CORRELATION_ID_MAX_LENGTH,
            pattern=r"^[\x21-\x7E]+$",
            description="Необязательный идентификатор корреляции для worker и webhook",
        ),
    ] = None,
) -> CreatePaymentResponse:
    correlation_id = x_request_id or str(uuid.uuid4())
    result = await handler.handle(
        CreatePaymentCommand(
            amount=body.amount,
            currency=body.currency,
            description=body.description,
            metadata=body.metadata,
            idempotency_key=idempotency_key,
            webhook_url=str(body.webhook_url),
            correlation_id=correlation_id,
        )
    )
    response.headers["X-Request-ID"] = correlation_id
    logger.info(
        "Payment %s accepted for processing",
        result.payment_id,
        extra={"correlation_id": correlation_id, "payment_id": str(result.payment_id)},
    )
    return CreatePaymentResponse(
        payment_id=result.payment_id,
        status=result.status,
        created_at=result.created_at,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailResponse,
    summary="Получить детали платежа",
    description="Возвращает текущее состояние платежа по его идентификатору.",
    responses={
        401: _UNAUTHORIZED_RESPONSE,
        404: {"model": ErrorResponse, "description": "Платёж не найден"},
        500: _INTERNAL_ERROR_RESPONSE,
        503: _DATABASE_UNAVAILABLE_RESPONSE,
    },
)
async def get_payment(
    payment_id: Annotated[uuid.UUID, Path(description="Идентификатор платежа")],
    handler: FromDishka[GetPaymentHandler],
) -> PaymentDetailResponse:
    view = await handler.handle(GetPaymentQuery(payment_id=payment_id))
    return PaymentDetailResponse(
        id=view.id,
        amount=view.amount,
        currency=view.currency,
        description=view.description,
        metadata=view.metadata,
        status=view.status,
        idempotency_key=view.idempotency_key,
        webhook_url=view.webhook_url,
        created_at=view.created_at,
        processed_at=view.processed_at,
    )
