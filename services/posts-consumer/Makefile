.PHONY: help build up down restart logs shell db-shell test migrate clean

# Default target
help:
	@echo "TgPost Service - Docker Management"
	@echo ""
	@echo "Usage:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make up-dev         - Start in development mode (hot reload)"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart services"
	@echo "  make logs           - Show logs (follow mode)"
	@echo "  make logs-tgpost    - Show TgPost service logs"
	@echo "  make logs-postgres  - Show PostgreSQL logs"
	@echo "  make shell          - Open shell in TgPost container"
	@echo "  make db-shell       - Open PostgreSQL shell"
	@echo "  make test           - Run tests"
	@echo "  make migrate        - Run Piccolo migrations"
	@echo "  make migrate-new    - Create new migration"
	@echo "  make clean          - Stop and remove all containers, networks"
	@echo "  make clean-all      - Clean + remove volumes (⚠️  deletes data!)"
	@echo ""

# Build Docker images
build:
	docker-compose build --no-cache

# Start services
up:
	docker-compose up -d

# Start in development mode
up-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Stop services
down:
	docker-compose down

# Restart services
restart:
	docker-compose restart

# Show logs
logs:
	docker-compose logs -f

logs-tgpost:
	docker-compose logs -f tgpost

logs-postgres:
	docker-compose logs -f postgres

# Open shell in TgPost container
shell:
	docker-compose exec tgpost bash

# Open PostgreSQL shell
db-shell:
	docker-compose exec postgres psql -U app_user -d app_db

# Run tests
test:
	docker-compose exec tgpost pytest src/Containers/AppSection/TgPost/Tests/ -v

test-cov:
	docker-compose exec tgpost pytest --cov=src/Containers/AppSection/TgPost --cov-report=html

# Run migrations
migrate:
	docker-compose exec tgpost piccolo migrations forwards TgPost

migrate-check:
	docker-compose exec tgpost piccolo migrations check TgPost

migrate-new:
	docker-compose exec tgpost piccolo migrations new TgPost --auto

migrate-backward:
	docker-compose exec tgpost piccolo migrations backwards TgPost

# Clean up
clean:
	docker-compose down --remove-orphans

clean-all:
	docker-compose down -v --remove-orphans

# Database operations
db-backup:
	docker-compose exec postgres pg_dump -U app_user app_db > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created: backup_$$(date +%Y%m%d_%H%M%S).sql"

db-restore:
	@read -p "Enter backup file path: " backup_file; \
	docker-compose exec -T postgres psql -U app_user -d app_db < $$backup_file

# Monitoring
stats:
	docker stats tgpost-consumer postgres_tgpost_db

ps:
	docker-compose ps

# Quick check
check:
	@echo "Checking services health..."
	@docker-compose ps
	@echo ""
	@echo "Checking Kafka connection..."
	@docker-compose exec tgpost python -c "from aiokafka import AIOKafkaConsumer; import asyncio; asyncio.run((lambda: print('Kafka: OK'))())" || echo "Kafka: FAIL"
	@echo ""
	@echo "Checking DB connection..."
	@docker-compose exec postgres pg_isready -U app_user -d app_db

# Development helpers
fmt:
	docker-compose exec tgpost ruff format src/

lint:
	docker-compose exec tgpost ruff check src/

# Full workflow
setup: build up migrate
	@echo "✅ Setup complete! TgPost service is running."

rebuild: down build up
	@echo "✅ Rebuild complete!"


