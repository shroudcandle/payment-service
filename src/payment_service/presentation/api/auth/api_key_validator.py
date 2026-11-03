from __future__ import annotations

import secrets
from typing import Annotated

from dishka import AsyncContainer
from fastapi import Request, Security, status
from fastapi.exceptions import HTTPException
from fastapi.security import APIKeyHeader

from payment_service.config import SecuritySettings

API_KEY_HEADER = "X-API-Key"

api_key_scheme = APIKeyHeader(
    name=API_KEY_HEADER,
    auto_error=False,
    description="Service API key passed in the X-API-Key header",
)


async def verify_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Security(api_key_scheme)] = None,
) -> None:
    container: AsyncContainer = request.state.dishka_container
    settings = await container.get(SecuritySettings)
    if x_api_key is None or not secrets.compare_digest(
        x_api_key.encode("utf-8"), settings.api_key.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
