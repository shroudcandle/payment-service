from __future__ import annotations

from httpx import AsyncClient


async def test_unexpected_error_is_masked_as_500(client: AsyncClient) -> None:
    response = await client.get("/unexpected")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


async def test_database_unavailable_returns_503(client: AsyncClient) -> None:
    response = await client.get("/database")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database service is temporarily unavailable"}


async def test_integrity_error_returns_409(client: AsyncClient) -> None:
    response = await client.get("/integrity")

    assert response.status_code == 409
    assert response.json() == {"detail": "Request conflicts with stored data"}


async def test_unexpected_sqlalchemy_error_returns_500(client: AsyncClient) -> None:
    response = await client.get("/sqlalchemy")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


async def test_duplicate_idempotency_key_returns_409(client: AsyncClient) -> None:
    response = await client.get("/duplicate-key")

    assert response.status_code == 409
    assert "key-1" in response.json()["detail"]


async def test_invalid_state_transition_returns_400(client: AsyncClient) -> None:
    response = await client.get("/invalid-state")

    assert response.status_code == 400
    assert response.json()["detail"] == "payment is already processed"


async def test_unprocessable_domain_error_returns_422(client: AsyncClient) -> None:
    response = await client.get("/invalid-amount")

    assert response.status_code == 422
    assert response.json()["detail"] == "amount must be positive"
