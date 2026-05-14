# Social Channel Consumer

Kafka consumer application for processing **Telegram channels** and **VK groups** data, built with Litestar, Piccolo ORM, and Porto architecture pattern.

> **Distributed Monolith**: Модульная архитектура позволяет включать/выключать модули независимо друг от друга. Каждый модуль использует отдельную базу данных.

## Features

### Multi-Platform Support
- **Telegram Channels** - consume and process channel metadata from Kafka (`tg_channels` topic)
- **VK Groups** - consume and process VK social network groups (`vk_groups` topic)

### Core Features
- **Distributed Monolith** - independent modules with separate databases
- **Auto Table Creation** - automatic database schema creation at startup
- **In-Memory Cache** - fast in-memory cache for instant lookups
- **Cache Workflow** - DB → Cache → Kafka for consistent publishing
- **Upsert Mechanism** - INSERT ON CONFLICT UPDATE for duplicate-free storage
- **Batch processing** - efficient bulk inserts (up to 10,000+ msg/sec)
- **PostgreSQL 17** with Piccolo ORM
- **Litestar web framework** for REST API
- **Dishka dependency injection**
- **Logfire observability**
- **Porto architecture compliance**

## Quick Start

### Docker Compose (Full Stack)

```bash
# Start all services (databases + app)
docker compose up -d --build

# Or start only databases for local development
docker compose -f docker-compose.db.yml up -d
```

The application will be available at http://localhost:8000

### Local Development

```bash
# 1. Start databases
docker compose -f docker-compose.db.yml up -d

# 2. Create .env file
cp .env.example .env
# Edit .env with your settings

# 3. Install dependencies and run
uv sync
uv run uvicorn app:app --reload

# Or without Kafka consumers (dev mode)
uv run uvicorn src.Bootstrap:app --reload
```

### Module Selection

Run only specific modules:

```bash
# Only Telegram module
ENABLE_TG_MODULE=true ENABLE_VK_MODULE=false uv run uvicorn app:app

# Only VK module
ENABLE_TG_MODULE=false ENABLE_VK_MODULE=true uv run uvicorn app:app

# Both modules (default)
uv run uvicorn app:app
```

## Environment Variables

### Module Toggles
- `ENABLE_TG_MODULE` - Enable Telegram module (default: true)
- `ENABLE_VK_MODULE` - Enable VK module (default: true)

### Telegram Database
- `TG_DB_HOST` - PostgreSQL host (default: localhost)
- `TG_DB_PORT` - PostgreSQL port (default: 5432)
- `TG_DB_USER` - PostgreSQL username
- `TG_DB_PASSWORD` - PostgreSQL password
- `TG_DB_NAME` - Database name (default: telegram)

> Legacy aliases `DB_HOST`, `DB_PORT`, etc. still work for backward compatibility.

### VK Database (Separate!)
- `VK_DB_HOST` - PostgreSQL host (default: localhost)
- `VK_DB_PORT` - PostgreSQL port (default: 5432)
- `VK_DB_USER` - PostgreSQL username
- `VK_DB_PASSWORD` - PostgreSQL password
- `VK_DB_NAME` - Database name (default: vk)

### Kafka
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka bootstrap servers
- `TG_KAFKA_TOPIC` - Telegram topic (default: tg_channels)
- `TG_KAFKA_GROUP_ID` - Telegram consumer group (default: tg-channel-consumer)
- `VK_KAFKA_TOPIC` - VK topic (default: vk_groups)
- `VK_KAFKA_GROUP_ID` - VK consumer group (default: vk-group-consumer)

### Batch Processing
- `BATCH_SIZE` - Number of messages to accumulate before batch insert (default: 100)
- `BATCH_TIMEOUT` - Max seconds to wait before flushing incomplete batch (default: 5.0)

### Application
- `LOG_LEVEL` - Logging level (default: INFO)
- `ENV` - Environment (default: development)
- `DEBUG` - Debug mode (default: false)

**📚 See [.env.example](.env.example) for complete configuration reference.**

## Kafka Topics & Message Schemas

### Topics Overview

| Module | Input Topic | Output Topic | Partitions |
|--------|-------------|--------------|------------|
| Telegram | `tg_channels` | `tg_channels_diff` | 3 |
| VK | `vk_groups` | `vk_groups_diff` | 3 |

Topics are created automatically at startup if they don't exist.

### Telegram Channel Schema (`tg_channels`)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Telegram Channel",
  "type": "channel"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID/string | ❌ Optional | Channel UUID (auto-generated if not provided) |
| `name` | string | ❌ Optional | Channel display name |
| `type` | string | ❌ Optional | Channel type (e.g., "channel", "group") |

**Notes:**
- If `id` is not provided, a UUID4 will be auto-generated
- `id` can be sent as string or UUID format (validated automatically)
- All fields are optional, but recommended for meaningful data

**Example without ID** (auto-generated):
```json
{
  "name": "Tech News",
  "type": "channel"
}
```

### VK Group Schema (`vk_groups`)

```json
{
  "id": 12345678,
  "name": "My VK Community",
  "screen_name": "my_community",
  "members_count": 5000
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer/string | ✅ **Required** | VK group ID (can be string, converted to int) |
| `name` | string | ❌ Optional | Group display name |
| `screen_name` | string | ❌ Optional | Group URL slug (e.g., `vk.com/screen_name`) |
| `members_count` | integer | ❌ Optional | Number of group members (must be ≥ 0) |

**Notes:**
- `id` is **required** and must be a valid VK group ID
- `id` can be sent as string or integer (converted automatically)
- `members_count` is validated to be non-negative
- Empty or invalid `members_count` values are set to `null`

**Minimal example**:
```json
{
  "id": 123456
}
```

## Architecture

This project follows the **Porto architecture** pattern with **Distributed Monolith** approach:

```
src/
├── Containers/                    # Business logic containers
│   ├── tg_channel/               # Telegram channels module
│   │   ├── actions/              # Business use cases
│   │   ├── tasks/                # Atomic operations
│   │   ├── model/                # Piccolo ORM models
│   │   └── services/             # Domain services
│   │
│   └── vk_group/                 # VK groups module (NEW!)
│       ├── actions/              # Business use cases
│       ├── tasks/                # Atomic operations
│       ├── model/                # Piccolo ORM models
│       └── services/             # Domain services
│
└── Ship/                         # Infrastructure layer
    ├── config/                   # Settings, Kafka config
    ├── utils/                    # DB engines, Kafka client
    ├── tasks/                    # Kafka workers
    └── Providers.py              # Dishka DI
```

### Telegram Container (`tg_channel`)

| Component | Description |
|-----------|-------------|
| **Kafka Topic** | `tg_channels` → `tg_channels_diff` |
| **Database** | PostgreSQL `telegram.channels` |
| **Primary Key** | UUID (auto-generated) |
| **Fields** | id, name, type |

### VK Container (`vk_group`) - NEW!

| Component | Description |
|-----------|-------------|
| **Kafka Topic** | `vk_groups` → `vk_groups_diff` |
| **Database** | PostgreSQL `vk.groups` |
| **Primary Key** | Integer (VK group ID) |
| **Fields** | id, name, screen_name, members_count |

**📖 Telegram documentation**: [docs/TG_CHANNELS.md](docs/TG_CHANNELS.md)

## Message Processing

### Batch Processing 🚀 (Kafka Worker - Active)

The Kafka worker implements efficient batch processing for high-throughput streams:

### How it works

1. **Buffer accumulation**: Messages are collected in memory buffer
2. **Smart flushing**: Batch is inserted when either:
   - Buffer reaches `BATCH_SIZE` (default: 100 messages)
   - `BATCH_TIMEOUT` seconds elapsed (default: 5s)
3. **Bulk insert**: Single SQL INSERT with multiple VALUES for optimal performance
4. **Graceful shutdown**: Remaining messages are flushed before worker stops

### Performance

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

**📖 Full documentation**: [docs/BATCH_PROCESSING.md](docs/BATCH_PROCESSING.md)


## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run Telegram tests
pytest src/Containers/tg_channel/tests/

# Run VK tests
pytest src/Containers/vk_group/tests/

# Integration test (requires running Kafka and DBs)
python test_integration.py   # Send test messages to Kafka
python test_consumer.py      # Consume and verify in DB
```

### Load Testing

```bash
# From Test-Producers directory
cd ../Test-SetUp/Test-Producers

# Test Telegram only
docker compose -f docker-compose.test.yaml up --build

# Test VK only
docker compose -f docker-compose.vk.yaml up --build

# Test both simultaneously
docker compose -f docker-compose.all.yaml up --build
```

## Documentation

### Modules
- **[TG_CHANNELS.md](docs/TG_CHANNELS.md)** - Telegram channels guide
- **[CACHE_MANAGEMENT.md](docs/CACHE_MANAGEMENT.md)** - Cache management
- **[QUICK_START_TG_CHANNELS.md](docs/QUICK_START_TG_CHANNELS.md)** - Quick start

### Configuration
- **[BATCH_PROCESSING.md](docs/BATCH_PROCESSING.md)** - Batch processing guide
- **[CONFIGURATION.md](docs/CONFIGURATION.md)** - Configuration and tuning
- **[.env.example](.env.example)** - Environment variables reference

### Architecture
- **[Porto Spec Kit](spec-kit/)** - Porto architecture methodology
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

## Contributing

This project follows Porto Spec Kit methodology:

1. Create specification: `/specify [feature description]`
2. Generate plan: `/plan [technical details]`
3. Create tasks: `/tasks`
4. Implement with TDD (tests first!)

See [spec-kit/docs/manual-usage.md](spec-kit/docs/manual-usage.md) for details.

## License

MIT