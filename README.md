# Payment Service

Асинхронный сервис процессинга платежей.
Реализует прием платежей, транзакционный outbox, эмуляцию шлюза и доставку статусов через webhook.

## Стек

- Python 3.12, uv
- FastAPI, Uvicorn, Pydantic v2
- PostgreSQL 16, SQLAlchemy 2.0, asyncpg, Alembic
- RabbitMQ 3.13, FastStream
- Dishka
- HTTPX
- Docker

## Архитектура

Структура каталогов:

- domain: чистая бизнес-логика без внешних зависимостей.
- application: CQRS, запросы и порты.
- infrastructure: адаптеры PostgreSQL, RabbitMQ и HTTPX.
- presentation: роуты FastAPI и подписчики RabbitMQ.
- di: сборка зависимостей Dishka.
- config: конфигурация через pydantic-settings.

## Запуск

### Docker

Разработка:

```bash
make up-dev
make down-dev
```

Production-окружение:

```bash
cp .env.example .env
make up
make down
```

### Локально

```bash
make sync
make dev
make worker
```

## API

Все запросы требуют заголовок X-API-Key.

### Создание платежа

Запрос:

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: test-secret-api-key-999" \
  -H "Idempotency-Key: order-123" \
  -H "X-Request-ID: req-123" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "1500.00",
    "currency": "RUB",
    "description": "Order #123",
    "metadata": {"order_id": 123},
    "webhook_url": "https://example.com/webhook"
  }'
```

Ответ 202 Accepted:

```json
{
  "payment_id": "0194eb40-62f9-7157-b08e-ebec66bebe8a",
  "status": "pending",
  "created_at": "2026-04-18T10:15:30.123456Z"
}
```

### Детали платежа

Запрос:

```bash
curl http://localhost:8000/api/v1/payments/0194eb40-62f9-7157-b08e-ebec66bebe8a \
  -H "X-API-Key: test-secret-api-key-999"
```

Ответ 200 OK:

```json
{
  "id": "0194eb40-62f9-7157-b08e-ebec66bebe8a",
  "amount": "1500.00",
  "currency": "RUB",
  "description": "Order #123",
  "metadata": {"order_id": 123},
  "status": "succeeded",
  "idempotency_key": "order-123",
  "webhook_url": "https://example.com/webhook",
  "created_at": "2026-04-18T10:15:30.123456Z",
  "processed_at": "2026-04-18T10:15:33.456789Z"
}
```

### Проверка работоспособности

- GET /health/live: возвращает status ok.
- GET /health/ready: возвращает статус доступности PostgreSQL и RabbitMQ.

### Формат Webhook

Сервис отправляет POST-запрос на webhook_url с заголовком X-Correlation-ID:

```json
{
  "event": "payment.updated",
  "webhook_id": "0194eb40-62f9-7157-b08e-ebec66bebe8a:succeeded",
  "payment_id": "0194eb40-62f9-7157-b08e-ebec66bebe8a",
  "status": "succeeded",
  "amount": "1500.00",
  "currency": "RUB",
  "metadata": {"order_id": 123},
  "processed_at": "2026-04-18T10:15:33.456789Z",
  "correlation_id": "req-123"
}
```

## Конфигурация

| Переменная | Описание | По умолчанию |
|---|---|---|
| APP_ENV | Режим окружения: development или production | production |
| API_KEY | Ключ авторизации API | test-secret-api-key-999 |
| DATABASE_URL | Строка подключения к PostgreSQL | postgresql+asyncpg://... |
| RABBITMQ_URL | Строка подключения к RabbitMQ | amqp://guest:guest@rabbitmq:5672/ |
| OUTBOX_POLL_INTERVAL | Интервал опроса outbox в секундах | 0.5 |
| OUTBOX_BATCH_SIZE | Размер выборки событий outbox | 50 |
| OUTBOX_LEASE_SECONDS | Время удержания события воркером в секундах | 30.0 |
| MAX_DELIVERY_ATTEMPTS | Лимит попыток отправки webhook | 3 |
| RETRY_BASE | Базовая задержка повтора в секундах | 2.0 |
| RETRY_CAP | Максимальная задержка повтора в секундах | 30.0 |
| WEBHOOK_STRICT_SECURITY | Запрет отправки webhook на локальные адреса | true |
| WEBHOOK_ALLOWED_HOSTS | Список разрешенных хостов через запятую | пустая строка |
| GATEWAY_SUCCESS_RATE | Доля успешных операций эмулятора шлюза | 0.9 |

## Тестирование

```bash
make test               # Unit и API тесты in-memory
make test-cov           # Проверка покрытия 100% ветвей
make test-architecture  # Проверка правил структуры кода
make test-integration   # Интеграционные тесты с testcontainers
make test-e2e           # Сквозные тесты
make mutation           # Мутационные тесты mutmut
make check              # Полный цикл проверок
```

## Команды Makefile

- make sync: синхронизация зависимостей uv.
- make lock: обновление uv.lock.
- make audit: аудит уязвимостей.
- make lint: проверка ruff с автоисправлением.
- make format: форматирование кода ruff.
- make typecheck: статическая проверка типов mypy.
- make dev: запуск API в режиме отладки.
- make worker: запуск воркера outbox relay и consumers.
- make build: сборка runtime-образа Docker.
- make migrate: применение миграций Alembic.
- make revision m="name": создание миграции Alembic.
- make clean: удаление кэшей и временных файлов.
