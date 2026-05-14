# Recommendation Services

Монорепозиторий прототипа распределённой рекомендательной системы для мультикластерной Kubernetes-инфраструктуры.

## Архитектура

Система развёрнута на трёх кластерах K3s (front, back, control), объединённых WireGuard mesh-сетью с сервисной сеткой Istio Ambient.

### ETL-конвейер (`services/`)

| Сервис | Описание |
|--------|----------|
| `vk-parser` | Парсер данных из API ВКонтакте (Litestar, AIOKafka) |
| `channel-consumer` | Нормализация метаданных каналов/групп из Redpanda → PostgreSQL |
| `posts-consumer` | Загрузка публикаций из Redpanda → PostgreSQL |

### Рекомендательный конвейер

| Сервис | Описание |
|--------|----------|
| `normalizer/` | Нормализация ETL-данных, формирование AdResource + ResourceDocument |
| `indexer/` | Синхронизация ResourceDocument → OpenSearch (Bulk API) |
| `recs_api/` | REST API рекомендаций (BM25-поиск + композитное ранжирование) |

### Общие модули (`shared/`)

- `models/etl.py` — Piccolo ORM модели ETL-слоя (read-only)
- `models/normalized.py` — модели нормализованного слоя
- `models/recommendations.py` — модели рекомендательного слоя
- `db.py` — подключение к PostgreSQL
- `config.py` — конфигурация через pydantic-settings

### Инфраструктура (`deploy/`)

Kubernetes-манифесты для развёртывания в back-кластере:
- `recsys/` — namespace, OpenSearch StatefulSet, Normalizer/Indexer/RecsAPI Deployments
- `postgres/` — PostgreSQL StatefulSet
- `redis/` — Redis StatefulSet
- `redpanda/` — Redpanda StatefulSet
- `parsers/` — Deployments ETL-сервисов

## Стек технологий

- **Python 3.12**, Litestar, Piccolo ORM, opensearch-py, APScheduler
- **PostgreSQL** — реляционное хранилище (ETL + normalized + recommendations)
- **OpenSearch 2.19** — полнотекстовый поисковый индекс
- **Redis** — кэш
- **Redpanda** — Kafka-совместимый брокер сообщений
- **Kubernetes (K3s)**, Istio Ambient, WireGuard, MetalLB

## Быстрый старт (локальная разработка)

```bash
docker compose up -d
uv sync
# Normalizer
litestar --app normalizer.app.main:app run --port 8001
# Indexer
litestar --app indexer.app.main:app run --port 8002
# Recommendation API
litestar --app recs_api.app.main:app run --port 8003
```

## Лицензия

Проект создан в рамках ВКР магистра МИРЭА.
