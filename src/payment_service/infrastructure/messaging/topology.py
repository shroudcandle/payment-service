from __future__ import annotations

from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue
from faststream.rabbit.schemas.queue import ClassicQueueArgs

PAYMENTS_EXCHANGE = RabbitExchange(
    "payments",
    type=ExchangeType.TOPIC,
    durable=True,
)
RETRY_EXCHANGE = RabbitExchange(
    "payments.retry",
    type=ExchangeType.DIRECT,
    durable=True,
)
DLX_EXCHANGE = RabbitExchange(
    "payments.dlx",
    type=ExchangeType.DIRECT,
    durable=True,
)

PAYMENT_CREATED_ROUTING_KEY = "payment.created"
PAYMENTS_DEAD_ROUTING_KEY = "payments.dead"
PAYMENTS_RETRY_ROUTING_KEY = "payments.retry"

PAYMENTS_NEW_QUEUE = RabbitQueue(
    "payments.new",
    routing_key=PAYMENT_CREATED_ROUTING_KEY,
    durable=True,
)

_RETRY_ARGUMENTS: ClassicQueueArgs = {
    "x-dead-letter-exchange": "payments",
    "x-dead-letter-routing-key": PAYMENT_CREATED_ROUTING_KEY,
}

PAYMENTS_RETRY_QUEUE = RabbitQueue(
    "payments.retry",
    routing_key=PAYMENTS_RETRY_ROUTING_KEY,
    durable=True,
    arguments=_RETRY_ARGUMENTS,
)

PAYMENTS_DLQ = RabbitQueue(
    "payments.dlq",
    routing_key=PAYMENTS_DEAD_ROUTING_KEY,
    durable=True,
)
