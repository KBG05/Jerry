.PHONY: help install dev prod clean migrate test

help:
	@echo "BlankPoint Backend - Available Commands"
	@echo "========================================"
	@echo "install     - Install dependencies with UV"
	@echo "dev         - Start development server with hot reload"
	@echo "prod        - Start production server"
	@echo "docker-dev  - Start all services with Docker Compose (dev mode)"
	@echo "docker-prod - Start all services with Docker Compose (production)"
	@echo "docker-down - Stop all Docker services"
	@echo "migrate     - Run database migrations"
	@echo "migrate-create - Create a new migration (use MSG='description')"
	@echo "test        - Run tests"
	@echo "lint        - Run code linting with ruff"
	@echo "format      - Format code with ruff"
	@echo "clean       - Remove cache and temporary files"

install:
	uv pip install -e .

dev:
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

prod:
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

docker-dev:
	docker-compose -f ../docker-compose.dev.yml up --build

docker-prod:
	docker-compose -f ../docker-compose.yml up --build -d

docker-down:
	docker-compose -f ../docker-compose.yml down
	docker-compose -f ../docker-compose.dev.yml down

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(MSG)"

migrate-down:
	alembic downgrade -1

test:
	pytest

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage
