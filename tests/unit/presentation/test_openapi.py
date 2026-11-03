from __future__ import annotations

from typing import Any


def test_api_key_security_scheme_is_exposed(openapi: dict[str, Any]) -> None:
    schemes = openapi["components"]["securitySchemes"]

    assert schemes["APIKeyHeader"]["type"] == "apiKey"
    assert schemes["APIKeyHeader"]["in"] == "header"
    assert schemes["APIKeyHeader"]["name"] == "X-API-Key"


def test_create_payment_documents_error_responses(openapi: dict[str, Any]) -> None:
    operation = openapi["paths"]["/api/v1/payments"]["post"]

    assert set(operation["responses"]) >= {"202", "400", "401", "409", "500", "503", "422"}
    assert operation["security"] == [{"APIKeyHeader": []}]
    assert operation["description"]


def test_get_payment_documents_error_responses(openapi: dict[str, Any]) -> None:
    operation = openapi["paths"]["/api/v1/payments/{payment_id}"]["get"]

    assert set(operation["responses"]) >= {"200", "401", "404", "500", "503", "422"}
    assert operation["security"] == [{"APIKeyHeader": []}]
    assert operation["description"]
