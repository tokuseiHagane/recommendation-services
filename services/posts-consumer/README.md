# Social Posts Consumer - Telegram & VK

**Распределённый монолит для динамической обработки постов из Telegram каналов и VK групп**

Высокопроизводительная система, построенная на **Porto архитектуре** с **Litestar**, **Piccolo ORM**, **AIOKafka** и **Dishka DI**. Состоит из двух независимых сервисов, обрабатывающих посты из разных социальных сетей.

## ✨ Ключевые возможности

- 🔄 **Динамическое создание консьюмеров** - автоматическое создание Kafka consumers при появлении новых каналов/групп
- 📊 **Шардированная обработка** - каждый канал/группа имеет свой топик для изоляции и масштабируемости
  - Telegram: `tg_posts_{channel_id}`
  - VK: `vk_posts_{group_id}`
- ⚡ **Batch processing** - эффективные bulk inserts (до 10,000+ постов/мин на консьюмер)
- 🗄️ **Multi-Database** - раздельные PostgreSQL базы для Telegram и VK данных
- 💾 **Двухуровневый кэш** - персистентный (БД синхронизация) + оперативный (Kafka события)
- 🔍 **Logfire observability** - полная трассировка Actions, Tasks и метрики
- 🏗️ **Porto Architecture** - чистая архитектура с разделением Actions/Tasks/Models/Services
- 🐳 **Docker ready** - полная Docker конфигурация с health checks и авто-миграциями
- 🧩 **Distributed Monolith** - независимые сервисы с общим кодом (Ship layer)

## 🚀 Quick Start

### 🐳 Docker Compose (рекомендуется)

```bash
# 1. Создать .env файл
cp env.example .env

# 2. Создать Docker сети (если не существуют)
docker network create tg-post-network 2>/dev/null || true
docker network create vk-post-network 2>/dev/null || true
docker network create kafka-network 2>/dev/null || true

# 3. Запустить оба сервиса
docker-compose up -d

# 4. Проверить логи (миграции применяются автоматически!)
# Telegram сервис
docker logs -f tg-post-consumer

# VK сервис
docker logs -f vk-post-consumer
```

**Запуск отдельных сервисов:**

```bash
# Только Telegram сервис
docker-compose up -d tg-service

# Только VK сервис
docker-compose up -d vk-service
```

**Development mode** (с hot reload):
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 💻 Локальная разработка

#### Telegram сервис

```bash
# 1. Установить зависимости
uv pip install -e .

# 2. Настроить переменные окружения
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_NAME=telegram
# ... другие переменные (см. env.example)

# 3. Применить миграции
piccolo migrations forwards TgPost

# 4. Запустить сервис
python -m src.BootstrapTg
```

#### VK сервис

```bash
# 1. Настроить переменные окружения для VK БД
export VK_DB_HOST=localhost
export VK_DB_PORT=5432
export VK_DB_USER=postgres
export VK_DB_PASSWORD=postgres
export VK_DB_NAME=vk
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# 2. Применить миграции (используя VK конфигурацию)
PICCOLO_CONF=piccolo_conf_vk piccolo migrations forwards VkPost

# 3. Запустить сервис
python -m src.BootstrapVk
```

### 📋 Автоматическое создание таблиц

**Таблицы создаются автоматически через Piccolo миграции!**

- 🐳 **В Docker**: миграции применяются автоматически при старте через `docker-entrypoint.sh`
- 💻 **Локально**: 
  - TgPost: `piccolo migrations forwards TgPost`
  - VkPost: `PICCOLO_CONF=piccolo_conf_vk piccolo migrations forwards VkPost`
- ✅ **Идемпотентно**: безопасно запускать повторно

Подробнее: [MIGRATIONS.md](MIGRATIONS.md)

## 🏗️ Архитектура сервисов

### Distributed Monolith

Проект реализован как **распределённый монолит** с двумя независимыми сервисами:

```
┌─────────────────────────────────────────────────────────────┐
│                     Shared Layer (Ship)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Kafka     │  │  Database   │  │     Settings        │  │
│  │   Client    │  │   Utils     │  │     Config          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│   TgPost Service        │    │   VkPost Service        │
│   (BootstrapTg.py)      │    │   (BootstrapVk.py)      │
├─────────────────────────┤    ├─────────────────────────┤
│ • tg_channels_diff      │    │ • vk_groups_diff        │
│ • tg_posts_{channel_id} │    │ • vk_posts_{group_id}   │
│ • PostgreSQL: telegram  │    │ • PostgreSQL: vk        │
└─────────────────────────┘    └─────────────────────────┘
```

### 🎯 Реализованные компоненты

**TgPost Container** (Telegram):
- ✅ **Models**: Post (Piccolo ORM)
- ✅ **Services**: PostObjectsCache, DynamicConsumerManager
- ✅ **Tasks**: 9 атомарных операций
- ✅ **Actions**: 4 бизнес use cases
- ✅ **Workers**: ConsumerWorker, ChannelsDiffWorker

**VkPost Container** (VK):
- ✅ **Models**: VkPost, VkGroup (Piccolo ORM)
- ✅ **Services**: VkGroupsCache, VkDynamicConsumerManager
- ✅ **Tasks**: 10 атомарных операций
- ✅ **Actions**: 4 бизнес use cases
- ✅ **Workers**: VkConsumerWorker, VkGroupsDiffWorker

**Ship Layer** (общий код):
- ✅ **Config**: Settings, Kafka config, Logging
- ✅ **Utils**: Multi-database support, Kafka client, Helpers

## ⚙️ Конфигурация

Сервисы настраиваются через переменные окружения. Полный список в [env.example](env.example).

### 🗄️ Telegram Database (PostgreSQL)
| Переменная | Описание | Default |
|------------|----------|---------|
| `DB_HOST` | PostgreSQL host | localhost |
| `DB_PORT` | PostgreSQL port | 5432 |
| `DB_USER` | PostgreSQL username | postgres |
| `DB_PASSWORD` | PostgreSQL password | postgres |
| `DB_NAME` | Database name | telegram |

### 🗄️ VK Database (PostgreSQL)
| Переменная | Описание | Default |
|------------|----------|---------|
| `VK_DB_HOST` | PostgreSQL host для VK | localhost |
| `VK_DB_PORT` | PostgreSQL port | 5432 |
| `VK_DB_USER` | PostgreSQL username | postgres |
| `VK_DB_PASSWORD` | PostgreSQL password | postgres |
| `VK_DB_NAME` | Database name | vk |

### 📡 Kafka (общие)
| Переменная | Описание | Default |
|------------|----------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka bootstrap servers | localhost:9092 |

### 📡 Kafka (Telegram)
| Переменная | Описание | Default |
|------------|----------|---------|
| `KAFKA_GROUP_ID_PREFIX` | Префикс для consumer groups | posts-consumer-group |
| `KAFKA_CHANNELS_DIFF_TOPIC` | Топик для событий о каналах | tg_channels_diff |
| `KAFKA_POSTS_TOPIC_PREFIX` | Префикс для топиков постов | tg_posts_ |

### 📡 Kafka (VK)
| Переменная | Описание | Default |
|------------|----------|---------|
| `KAFKA_GROUP_ID_PREFIX` | Префикс для consumer groups | vk-posts-consumer-group |
| `KAFKA_GROUPS_DIFF_TOPIC` | Топик для событий о группах | vk_groups_diff |
| `KAFKA_POSTS_TOPIC_PREFIX` | Префикс для топиков постов | vk_posts_ |

### ⚡ Processing Settings
| Переменная | Описание | Default |
|------------|----------|---------|
| `BATCH_SIZE` | Размер батча для обработки | 100 |
| `BATCH_TIMEOUT_MS` | Timeout для getmany (мс) | 10000 |
| `CACHE_TTL_SECONDS` | TTL для кэша | 300 |
| `CONSUMER_TIMEOUT_MS` | Timeout для Kafka consumer | 1000 |
| `AUTO_OFFSET_RESET` | Offset reset strategy | earliest |

## 🏗️ Porto Architecture

Оба контейнера следуют **Porto (Software Architectural Pattern)**:

```
src/Containers/AppSection/
├── TgPost/                    # Telegram container
│   ├── Actions/               # Бизнес use cases (оркестрация)
│   ├── Tasks/                 # Атомарные операции
│   ├── Models/                # Piccolo ORM модели
│   ├── Services/              # Singleton сервисы (Cache, Manager)
│   ├── UI/Workers/            # Kafka workers
│   ├── Data/                  # Pydantic DTOs
│   ├── Exceptions/            # Кастомные исключения
│   ├── Config/                # Конфигурация контейнера
│   └── migrations/            # Piccolo миграции
│
└── VkPost/                    # VK container (аналогичная структура)
    ├── Actions/
    ├── Tasks/
    ├── Models/
    ├── Services/
    ├── UI/Workers/
    ├── Data/
    ├── Exceptions/
    ├── Config/
    └── migrations/
```

### Workflow (Telegram)

1. **ChannelsDiffWorker** прослушивает топик `tg_channels_diff`
2. При получении события о новом канале → **CreateDynamicConsumerAction**
3. Action создает новый **AIOKafkaConsumer** для топика `tg_posts_{channel_id}`
4. **ConsumerWorker** потребляет посты батчами → **BatchProcessPostsAction**
5. Action валидирует и сохраняет посты через **BatchUpsertPostsTask** (ON CONFLICT UPDATE)
6. Manual commit после успешного сохранения (at-least-once семантика)

### Workflow (VK)

1. **VkGroupsDiffWorker** прослушивает топик `vk_groups_diff`
2. При получении события о новой группе → **CreateVkDynamicConsumerAction**
3. Action создает новый **AIOKafkaConsumer** для топика `vk_posts_{group_id}`
4. **VkConsumerWorker** потребляет посты батчами → **BatchProcessVkPostsAction**
5. Action валидирует и сохраняет посты через **BatchUpsertVkPostsTask** (ON CONFLICT UPDATE)
6. Manual commit после успешного сохранения (at-least-once семантика)

## 🛠️ Docker Commands

```bash
# Запустить все сервисы
docker-compose up -d

# Запустить только Telegram сервис
docker-compose up -d tg-service

# Запустить только VK сервис
docker-compose up -d vk-service

# Логи Telegram сервиса
docker logs -f tg-post-consumer

# Логи VK сервиса
docker logs -f vk-post-consumer

# Остановить все сервисы
docker-compose down

# Shell в Telegram контейнере
docker exec -it tg-post-consumer /bin/bash

# Shell в VK контейнере
docker exec -it vk-post-consumer /bin/bash

# Применить миграции вручную (Telegram)
docker exec tg-post-consumer piccolo migrations forwards TgPost

# Применить миграции вручную (VK)
docker exec vk-post-consumer piccolo migrations forwards VkPost

# Пересобрать образы
docker-compose build --no-cache
```

## 🧪 Тестирование

### Интеграционное тестирование

Для тестирования используется проект **Test-Producers**, который отправляет тестовые сообщения в Kafka:

```bash
# Полный интеграционный тест (Telegram + VK)
python full_integration_test.py

# Только Telegram
python full_integration_test.py --telegram-only

# Только VK
python full_integration_test.py --vk-only

# С кастомными параметрами
python full_integration_test.py \
  --tg-channels 3 \
  --tg-posts 50 \
  --vk-groups 3 \
  --vk-posts 50
```

### Unit/Integration тесты

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src

# Тесты TgPost контейнера
pytest src/Containers/AppSection/TgPost/Tests/

# Тесты VkPost контейнера
pytest src/Containers/AppSection/VkPost/Tests/
```

## 📊 Мониторинг

Сервисы используют **Logfire** для observability:
- Трассировка всех Actions и Tasks
- Метрики: `active_consumers_count`, `posts_processed`, `batch_processing_duration_seconds`
- Логирование всех критических операций

## 📚 Документация

- [🐳 Docker Setup](DOCKER_SETUP.md) - Детальное руководство по Docker
- [📋 Migrations Guide](MIGRATIONS.md) - Работа с Piccolo миграциями
- [🚀 Getting Started](GETTING_STARTED.md) - Пошаговые сценарии запуска
- [🏗️ Architecture](architecture.md) - Описание архитектуры сервиса
- [📊 Data Model](post_model.md) - Схема БД для постов
- [📊 Batch Processing](docs/BATCH_PROCESSING.md) - Конфигурация batch обработки
- [📋 Specifications](specs/001-dynamic-kafka-consumers-sharded-processing/) - Porto Spec Kit документация

## 🤝 Интеграция с внешними сервисами

### Telegram

TgPost работает в паре с микросервисом **Telegram-Channel-Consumer**:

- **Telegram-Channel-Consumer** публикует события о новых каналах в `tg_channels_diff`
- **TgPost** подписывается на `tg_channels_diff` и создает консьюмеры динамически
- **Telegram-Channel-Consumer** публикует посты в шардированные топики `tg_posts_{id}`
- **TgPost** потребляет и сохраняет посты в PostgreSQL

### VK

VkPost работает аналогично с сервисом сбора данных VK:

- Внешний сервис публикует события о новых группах в `vk_groups_diff`
- **VkPost** подписывается на `vk_groups_diff` и создает консьюмеры динамически
- Внешний сервис публикует посты в шардированные топики `vk_posts_{group_id}`
- **VkPost** потребляет и сохраняет посты в PostgreSQL

## 📥 Форматы входящих сообщений из Kafka

### Telegram сервис (TgPost)

#### Топик: `tg_channels_diff` (события о каналах)

Сообщения о новых/обновлённых Telegram каналах для динамического создания консьюмеров.

**Формат JSON:**
```json
{
  "id": 123,
  "name": "Tech News Channel",
  "type": "channel"
}
```

**Поля:**
| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `id` | `int` | ✅ | Уникальный ID канала |
| `name` | `str` | ✅ | Название канала |
| `type` | `str` | ✅ | Тип канала (channel, supergroup, broadcast, etc.) |

**Валидация:** `ChannelDTO` (Pydantic)

---

#### Топики: `tg_posts_{channel_id}` (посты канала)

Сообщения с постами из конкретного Telegram канала.

**Формат JSON:**
```json
{
  "id": 123456,
  "content": "Post content text...",
  "repost_count": 10,
  "view_count": 1000,
  "link": {
    "url": "https://t.me/channel/123456",
    "type": "telegram"
  },
  "message_timestamp": "2026-02-01T12:00:00Z",
  "has_reactions": true,
  "id_channels": 123,
  "free_reactions_count": 50,
  "paid_reactions_count": 5
}
```

**Поля:**
| Поле | Тип | Обязательно | Описание | Default |
|------|-----|-------------|----------|---------|
| `id` | `int` | ✅ | Уникальный ID поста | - |
| `content` | `str` | ❌ | Текст поста | `null` |
| `repost_count` | `int` | ❌ | Количество репостов | `0` |
| `view_count` | `int` | ❌ | Количество просмотров | `0` |
| `link` | `object` | ❌ | Ссылка (JSONB структура) | `null` |
| `message_timestamp` | `datetime` | ❌ | Время публикации (ISO 8601) | `null` |
| `has_reactions` | `bool` | ❌ | Флаг наличия реакций | `false` |
| `id_channels` | `int` | ❌ | ID канала (FK) | `null` |
| `free_reactions_count` | `int` | ❌ | Бесплатные реакции | `0` |
| `paid_reactions_count` | `int` | ❌ | Платные реакции | `0` |

**Валидация:** `PostDTO` (Pydantic)  
**Идемпотентность:** ON CONFLICT UPDATE по `id`

---

### VK сервис (VkPost)

#### Топик: `vk_groups_diff` (события о группах)

Сообщения о новых/обновлённых VK группах для динамического создания консьюмеров.

**Формат JSON:**
```json
{
  "id": 123456789,
  "name": "Программирование | Python",
  "screen_name": "python_community",
  "members_count": 50000
}
```

**Поля:**
| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `id` | `int` | ✅ | Уникальный ID группы VK |
| `name` | `str` | ❌ | Название группы | `null` |
| `screen_name` | `str` | ❌ | URL slug группы | `null` |
| `members_count` | `int` | ❌ | Количество участников | `null` |

**Валидация:** `GroupDTO` (Pydantic)

---

#### Топики: `vk_posts_{group_id}` (посты группы)

Сообщения с постами из конкретной VK группы.

**Формат JSON:**
```json
{
  "id": 789012,
  "len_message": 150,
  "repost_count": 25,
  "view_count": 5000,
  "comments_count": 100,
  "message_timestamp": "2026-02-01T12:00:00Z",
  "edit_date": "2026-02-01T13:00:00Z",
  "reactions_count": 300,
  "id_groups": 123456789
}
```

**Поля:**
| Поле | Тип | Обязательно | Описание | Default |
|------|-----|-------------|----------|---------|
| `id` | `int` | ✅ | Уникальный ID поста | - |
| `len_message` | `int` | ❌ | Длина текста поста | `null` |
| `repost_count` | `int` | ❌ | Количество репостов | `0` |
| `view_count` | `int` | ❌ | Количество просмотров | `0` |
| `comments_count` | `int` | ❌ | Количество комментариев | `0` |
| `message_timestamp` | `datetime` | ❌ | Время публикации (ISO 8601) | `null` |
| `edit_date` | `datetime` | ❌ | Время редактирования (ISO 8601) | `null` |
| `reactions_count` | `int` | ❌ | Общее количество реакций | `0` |
| `id_groups` | `int` | ❌ | ID VK группы (FK) | `null` |

**Валидация:** `VkPostDTO` (Pydantic)  
**Идемпотентность:** ON CONFLICT UPDATE по `id`

---

### 📝 Важные примечания

1. **Формат дат:** ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`)
2. **Кодировка:** UTF-8
3. **Сериализация:** JSON (Kafka value serializer)
4. **Валидация:** Pydantic DTOs с автоматическим отклонением невалидных сообщений
5. **Commit strategy:** Manual commit после успешного batch upsert (at-least-once)
6. **Error handling:** Невалидные сообщения логируются и пропускаются, обработка продолжается

## 📊 Performance

| Batch Size | Throughput | Latency (p95) | DB Queries/sec |
|------------|------------|---------------|----------------|
| 50         | 2,500/s    | 10ms          | 50             |
| 100        | 5,000/s    | 20ms          | 50             |
| 500        | 10,000+/s  | 50ms          | 20             |

### Quick Configuration

```env
# High throughput
BATCH_SIZE=500
BATCH_TIMEOUT=10.0

# Low latency
BATCH_SIZE=50
BATCH_TIMEOUT=1.0

# Balanced (default)
BATCH_SIZE=100
BATCH_TIMEOUT=5.0
```

## 🤝 Contributing

This project follows Porto Spec Kit methodology:

1. Create specification: `/specify [feature description]`
2. Generate plan: `/plan [technical details]`
3. Create tasks: `/tasks`
4. Implement with TDD (tests first!)

See [spec-kit/docs/manual-usage.md](spec-kit/docs/manual-usage.md) for details.

## 📄 License

MIT
