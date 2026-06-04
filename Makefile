.DEFAULT_GOAL := help
.PHONY: help install dev run migrate makemigration seed test lint fmt typecheck up down logs reset

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install deps (uv)
	uv sync

dev: ## Run API with reload
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run: ## Run API (prod-ish, local)
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

migrate: ## Apply migrations
	uv run alembic upgrade head

makemigration: ## Autogenerate migration: make makemigration m="msg"
	uv run alembic revision --autogenerate -m "$(m)"

downgrade: ## Roll back one migration
	uv run alembic downgrade -1

seed: ## Seed demo data
	uv run python -m scripts.seed

test: ## Run tests
	uv run pytest

lint: ## Lint
	uv run ruff check .

fmt: ## Format
	uv run ruff format .

typecheck: ## Type-check
	uv run mypy app

up: ## docker compose up
	docker compose up -d --build

down: ## docker compose down
	docker compose down

logs: ## tail api logs
	docker compose logs -f api

reset: ## drop volumes + recreate
	docker compose down -v && docker compose up -d --build
