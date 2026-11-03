from __future__ import annotations

import pytest
from pydantic import ValidationError

from payment_service.config import HttpClientSettings


def test_http_settings_have_explicit_defaults() -> None:
    settings = HttpClientSettings(_env_file=None)

    assert settings.max_connections == 100
    assert settings.max_keepalive_connections == 20
    assert settings.keepalive_expiry == 10.0
    assert settings.timeout_seconds == 10.0
    assert settings.connect_timeout_seconds == 5.0


def test_http_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_MAX_CONNECTIONS", "42")
    monkeypatch.setenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", "7")
    monkeypatch.setenv("HTTP_KEEPALIVE_EXPIRY", "3.5")
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "8.0")
    monkeypatch.setenv("HTTP_CONNECT_TIMEOUT_SECONDS", "2.0")

    settings = HttpClientSettings(_env_file=None)

    assert settings.max_connections == 42
    assert settings.max_keepalive_connections == 7
    assert settings.keepalive_expiry == 3.5
    assert settings.timeout_seconds == 8.0
    assert settings.connect_timeout_seconds == 2.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_connections": 0},
        {"max_keepalive_connections": -1},
        {"keepalive_expiry": 0},
        {"timeout_seconds": 0},
        {"connect_timeout_seconds": 0},
        {"max_connections": 5, "max_keepalive_connections": 6},
        {"timeout_seconds": 2.0, "connect_timeout_seconds": 3.0},
    ],
)
def test_http_settings_reject_invalid_values(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        HttpClientSettings(_env_file=None, **kwargs)
