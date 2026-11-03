from __future__ import annotations

from dishka import AsyncContainer, make_async_container

from payment_service.di.providers import (
    ConfigProvider,
    DatabaseProvider,
    GatewayProvider,
    HttpProvider,
    MessagingProvider,
    ServicesProvider,
)


def make_container() -> AsyncContainer:
    return make_async_container(
        ConfigProvider(),
        DatabaseProvider(),
        MessagingProvider(),
        HttpProvider(),
        GatewayProvider(),
        ServicesProvider(),
    )
