from __future__ import annotations

from dishka import Provider, Scope, provide
from faststream.rabbit import RabbitBroker

from payment_service.application.ports import EventPublisherPort
from payment_service.config import RabbitMQSettings
from payment_service.infrastructure.messaging import RabbitEventPublisher


class MessagingProvider(Provider):
    scope = Scope.APP

    @provide
    def broker(self, settings: RabbitMQSettings) -> RabbitBroker:
        return RabbitBroker(settings.url)

    @provide
    def event_publisher(self, broker: RabbitBroker) -> EventPublisherPort:
        return RabbitEventPublisher(broker)
