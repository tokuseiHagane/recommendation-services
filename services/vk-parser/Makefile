.PHONY: help install dev run test lint format \
       docker-up docker-down docker-build docker-logs \
       docker-test-up docker-test-down docker-prod-up docker-prod-down \
       migrate clean

help:
	@echo "VK Parser Service - Available commands:"
	@echo ""
	@echo "  install            Install dependencies with uv"
	@echo "  dev                Run development server with hot reload"
	@echo "  run                Run production server"
	@echo "  test               Run tests"
	@echo "  lint               Run linting"
	@echo "  format             Format code"
	@echo ""
	@echo "  docker-up          Start dev containers"
	@echo "  docker-down        Stop dev containers"
	@echo "  docker-build       Build dev containers"
	@echo "  docker-logs        Follow dev app logs"
	@echo ""
	@echo "  docker-test-up     Start test containers"
	@echo "  docker-test-down   Stop test containers"
	@echo "  docker-prod-up     Start prod containers"
	@echo "  docker-prod-down   Stop prod containers"
	@echo ""
	@echo "  migrate            Run Piccolo migrations locally"
	@echo "  clean              Clean cache files"

install:
	uv pip install -e ".[dev]"

dev:
	python run.py

run:
	python -m src.Bootstrap

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# --- Dev ---
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-build:
	docker compose build

docker-logs:
	docker compose logs -f app

# --- Test ---
docker-test-up:
	docker compose -f docker-compose.test.yml up -d --build

docker-test-down:
	docker compose -f docker-compose.test.yml down -v

# --- Prod ---
docker-prod-up:
	docker compose -f docker-compose.prod.yml up -d --build

docker-prod-down:
	docker compose -f docker-compose.prod.yml down

# --- Migrations ---
migrate:
	python scripts/migrate.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

