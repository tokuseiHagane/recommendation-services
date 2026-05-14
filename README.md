# recommendation-services

Монорепа микросервисов рекомендательной системы FatData.

## Сервисы

| Сервис | Описание |
|--------|----------|
| **normalizer** | ETL-пайплайн: извлечение и нормализация данных по расписанию (APScheduler) |
| **indexer** | Индексация нормализованных данных в OpenSearch |
| **recs_api** | HTTP API рекомендаций (Litestar) |

## Стек

- **Framework**: Litestar (ASGI)
- **ORM**: Piccolo
- **Search**: OpenSearch 2.19
- **Queue**: Redpanda (Kafka-compatible)
- **Cache**: Redis 7.2
- **DB**: PostgreSQL 18
- **DI**: Dishka
- **Observability**: Logfire

## Быстрый старт

```bash
# Поднять инфраструктуру
docker compose up -d

# Установить зависимости
uv sync

# Запустить линтер
uv run ruff check .

# Запустить тесты
uv run pytest
```

## Структура

```
recommendation-services/
├── normalizer/          # ETL-сервис
├── indexer/             # Индексатор OpenSearch
├── recs_api/            # API рекомендаций
├── shared/              # Общий код (модели, конфиг, БД)
├── migrations/          # Миграции Piccolo
├── docker-compose.yml   # Локальная инфраструктура
└── pyproject.toml       # uv workspace
```
