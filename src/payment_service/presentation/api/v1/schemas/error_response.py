from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str = Field(
        description="Человекочитаемое описание ошибки",
        examples=["Payment not found"],
    )
