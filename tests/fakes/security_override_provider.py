from __future__ import annotations

from dishka import Provider, Scope, provide

from payment_service.config.security import SecuritySettings
from tests.helpers.constants import TEST_API_KEY


class SecurityOverrideProvider(Provider):
    scope = Scope.APP

    @provide
    def security_settings(self) -> SecuritySettings:
        return SecuritySettings(api_key=TEST_API_KEY)
