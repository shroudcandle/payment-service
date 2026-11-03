from __future__ import annotations

from dishka import Provider, Scope, provide

from payment_service.config.worker import WorkerSettings


class WorkerSettingsOverrideProvider(Provider):
    scope = Scope.APP

    @provide
    def worker_settings(self) -> WorkerSettings:
        return WorkerSettings()
