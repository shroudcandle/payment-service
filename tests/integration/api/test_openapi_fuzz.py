from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import schemathesis
from fastapi import FastAPI
from hypothesis import HealthCheck, given, settings
from schemathesis import Case, GenerationMode

from tests.helpers.constants import TEST_API_KEY

MAX_EXAMPLES = 40


@pytest.mark.parametrize(
    "mode",
    [GenerationMode.POSITIVE, GenerationMode.NEGATIVE],
)
def test_openapi_fuzzing_never_returns_server_error(
    api_app: FastAPI,
    mode: GenerationMode,
) -> None:
    @asynccontextmanager
    async def no_lifespan(app: FastAPI) -> AsyncIterator[None]:
        _ = app
        yield

    api_app.router.lifespan_context = no_lifespan
    schema = schemathesis.openapi.from_asgi("/openapi.json", api_app).exclude(path="/health")
    strategy = schema.as_strategy(
        generation_mode=mode,
        headers={
            "X-API-Key": TEST_API_KEY,
            "Idempotency-Key": "fuzz-key",
            "X-Request-ID": "fuzz-trace",
        },
    )

    @settings(
        max_examples=MAX_EXAMPLES,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    @given(case=strategy)
    def check(case: Case) -> None:
        response = case.call()
        assert response.status_code < 500, case.as_curl_command()
        if response.status_code >= 400:
            assert "detail" in response.json()

    check()
