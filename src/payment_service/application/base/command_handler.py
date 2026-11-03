from __future__ import annotations

from typing import Protocol

from payment_service.application.base.command import Command
from payment_service.application.base.view import View


class CommandHandler[TCommand: Command[View | None], TResult: View | None](Protocol):
    async def handle(self, command: TCommand) -> TResult: ...
