.DEFAULT_GOAL := help

.PHONY: help sync lock audit lint format format-check typecheck test test-unit \
	test-integration test-e2e test-architecture test-compose test-cov test-domain mutation check \
	clean dev worker build build-test up up-dev down down-dev logs ps migrate revision

help:
	@printf "%-22s %s\n" "make sync" "синхронизировать зависимости"
	@printf "%-22s %s\n" "make lock" "обновить uv.lock до актуальных версий"
	@printf "%-22s %s\n" "make audit" "уязвимости зависимостей"
	@printf "%-22s %s\n" "make lint" "ruff check с автофиксом"
	@printf "%-22s %s\n" "make format" "ruff format"
	@printf "%-22s %s\n" "make format-check" "проверить форматирование"
	@printf "%-22s %s\n" "make typecheck" "mypy --strict"
	@printf "%-22s %s\n" "make test" "быстрые тесты"
	@printf "%-22s %s\n" "make test-unit" "unit-тесты"
	@printf "%-22s %s\n" "make test-integration" "интеграционные тесты"
	@printf "%-22s %s\n" "make test-e2e" "сквозной e2e"
	@printf "%-22s %s\n" "make test-compose" "прогон тестов в docker compose"
	@printf "%-22s %s\n" "make test-architecture" "архитектурные тесты"
	@printf "%-22s %s\n" "make test-cov" "покрытие cov"
	@printf "%-22s %s\n" "make test-domain" "покрытие домена"
	@printf "%-22s %s\n" "make mutation" "мутационное тестирование"
	@printf "%-22s %s\n" "make check" "полный цикл верификации"
	@printf "%-22s %s\n" "make clean" "удалить кэши и артефакты тестов"
	@printf "%-22s %s\n" "make dev" "API с reload"
	@printf "%-22s %s\n" "make worker" "worker"
	@printf "%-22s %s\n" "make build" "собрать runtime-образ"
	@printf "%-22s %s\n" "make build-test" "собрать test-образ"
	@printf "%-22s %s\n" "make up" "prod-like compose"
	@printf "%-22s %s\n" "make up-dev" "dev compose"
	@printf "%-22s %s\n" "make down" "остановить prod-like compose"
	@printf "%-22s %s\n" "make down-dev" "остановить dev compose"
	@printf "%-22s %s\n" "make logs" "логи compose"
	@printf "%-22s %s\n" "make migrate" "применить миграции"
	@printf "%-22s %s\n" "make revision m=msg" "новая миграция"

sync:
	uv sync

lock:
	uv lock --upgrade

audit:
	uv audit --preview-features audit-command

lint:
	uv run ruff check src/ tests/ --fix

format:
	uv run ruff format src/ tests/

format-check:
	uv run ruff format --check src/ tests/

typecheck:
	uv run mypy src/

test:
	uv run pytest --disable-socket --allow-unix-socket

test-unit:
	uv run pytest -m unit --disable-socket --allow-unix-socket

test-integration:
	uv run pytest -m integration

test-e2e:
	uv run pytest -m e2e

test-architecture:
	uv run pytest -m architecture --disable-socket --allow-unix-socket

test-cov:
	uv run pytest -m "not integration and not e2e" --cov=payment_service --cov-branch \
		--cov-report=term-missing --cov-fail-under=100 --disable-socket --allow-unix-socket

test-domain:
	uv run pytest tests/unit/domain -m unit --cov=payment_service.domain \
		--cov-branch --cov-report=term-missing --cov-fail-under=100 --disable-socket --allow-unix-socket

mutation:
	uv run mutmut run --max-children 4
	uv run mutmut export-cicd-stats
	uv run python -c "import json; s=json.load(open('mutants/mutmut-cicd-stats.json')); total=s['killed']+s['survived']; score=100*s['killed']/total; print(f'Mutation score: {score:.1f}% ({s[\"killed\"]}/{total})'); raise SystemExit(0 if score >= 90 else 1)"

test-compose:
	docker compose --project-directory . -f docker/docker-compose.test.yml up --build \
		--abort-on-container-exit --exit-code-from tests ; \
	status=$$? ; docker compose --project-directory . -f docker/docker-compose.test.yml down -v ; \
	exit $$status

check: lint format-check typecheck audit test-cov test-domain test-architecture mutation

clean:
	rm -rf .coverage htmlcov .pytest_cache .mypy_cache .ruff_cache .hypothesis mutants .schemathesis

dev:
	uv run uvicorn payment_service.presentation.api.app:create_app --factory --reload --host 0.0.0.0 --port 8000

worker:
	uv run python -m payment_service.main_worker

build:
	docker build --target runtime -t payment-service:local .

build-test:
	docker build --target test -t payment-service:test .

up:
	docker compose up -d --build

up-dev:
	docker compose --project-directory . -f docker-compose.yml -f docker/docker-compose.dev.yml \
		--env-file .env.example up --build

down:
	docker compose down

down-dev:
	docker compose --project-directory . -f docker-compose.yml -f docker/docker-compose.dev.yml \
		--env-file .env.example down

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

migrate:
	uv run alembic upgrade head

revision:
	uv run alembic revision --autogenerate -m "$(m)"
