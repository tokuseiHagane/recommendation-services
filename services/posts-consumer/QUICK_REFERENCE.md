# 📝 Quick Reference - TgPost Service

Краткая справка по работе с TgPost сервисом.

## 🚀 Быстрый старт

```bash
# 1. Настроить окружение
cp env.example .env

# 2. Запустить
make up

# 3. Проверить логи
make logs-tgpost

# 4. Проверить что работает
make check
```

**Готово!** Таблицы созданы автоматически через Piccolo миграции.

## 🎯 Основные команды

### Docker

```bash
make up              # Запустить все сервисы
make up-dev          # Dev mode с hot reload
make down            # Остановить
make restart         # Перезапустить
make logs-tgpost     # Логи TgPost
make shell           # Bash в контейнере
make clean           # Очистить контейнеры
```

### База данных

```bash
make db-shell        # PostgreSQL shell
make migrate         # Применить миграции (обычно не нужно - автоматически!)
make migrate-check   # Статус миграций
make db-backup       # Создать backup
```

### Тесты

```bash
make test            # Все тесты
make test-cov        # С покрытием
```

## 📋 Миграции (Автоматические!)

**Таблицы создаются автоматически при запуске Docker контейнера!**

### Что происходит при запуске

```
1. docker-compose up
2. docker-entrypoint.sh ожидает PostgreSQL
3. Автоматически применяет Piccolo миграции
4. Создает таблицу posts с индексами
5. Запускает приложение
```

### Если нужно вручную

```bash
# Проверить статус
docker-compose exec tgpost piccolo migrations check TgPost

# Применить (обычно не нужно!)
docker-compose exec tgpost piccolo migrations forwards TgPost

# Создать новую миграцию
docker-compose exec tgpost piccolo migrations new TgPost --auto
```

## 🗄️ Структура БД

### Таблица posts (создается автоматически)

```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,              -- Post ID
    content TEXT,                        -- Content
    repost_count INTEGER DEFAULT 0,      -- Reposts
    view_count INTEGER DEFAULT 0,        -- Views
    link JSONB,                          -- Links (JSON)
    message_timestamp TIMESTAMP,         -- When posted
    has_reactions BOOLEAN DEFAULT FALSE, -- Has reactions?
    id_channels INTEGER,                 -- Channel ID (FK)
    free_reactions_count INTEGER DEFAULT 0,
    paid_reactions_count INTEGER DEFAULT 0
);

-- Indexes (created automatically)
CREATE INDEX idx_posts_id_channels ON posts(id_channels);
CREATE INDEX idx_posts_timestamp ON posts(message_timestamp);
```

## 🔧 Переменные окружения

### Обязательные

```env
KAFKA_BOOTSTRAP_SERVERS=broker:29092    # Kafka адрес
DB_PASSWORD=your_secure_password        # БД пароль
```

### Опциональные

```env
BATCH_SIZE=100                          # Размер батча
BATCH_TIMEOUT_MS=10000                  # Timeout getmany
CACHE_TTL_SECONDS=300                   # TTL кэша (5 мин)
LOG_LEVEL=INFO                          # Уровень логов
```

Полный список: [env.example](env.example)

## 📊 Мониторинг

### Проверить здоровье

```bash
make check           # Полная проверка
make ps              # Статус контейнеров
make stats           # CPU/Memory usage
```

### Логи

```bash
make logs            # Все логи
make logs-tgpost     # Только TgPost
make logs-postgres   # Только PostgreSQL

# Последние 100 строк
docker-compose logs --tail=100 tgpost
```

### Метрики (Logfire)

- `active_consumers_count` - количество активных консьюмеров
- `posts_processed` - количество обработанных постов
- `batch_processing_duration_seconds` - время обработки батча

## 🐛 Troubleshooting

### Контейнер не запускается

```bash
make logs-tgpost     # Проверить логи
make rebuild         # Пересобрать
```

### Таблица не создана

```bash
# Проверить что миграции применились
docker-compose logs tgpost | grep -A 5 "migrations"

# Применить вручную если нужно
make migrate
```

### Не подключается к Kafka

```bash
# Проверить переменные
docker-compose exec tgpost env | grep KAFKA

# Проверить доступность
docker-compose exec tgpost ping broker
```

## 📁 Структура проекта

```
.
├── src/Containers/AppSection/TgPost/    # Porto container
│   ├── Actions/                         # Business use cases
│   ├── Tasks/                           # Atomic operations
│   ├── Models/Post.py                   # Piccolo model ✨
│   ├── migrations/                      # Auto-applied ✨
│   ├── Services/                        # Cache, Manager
│   └── UI/Workers/                      # Kafka workers
├── docker-compose.yml                    # Docker config
├── docker-entrypoint.sh                 # Auto-migrations ✨
├── Dockerfile                           # Image definition
└── piccolo_conf.py                      # Piccolo config
```

✨ = Автоматическое создание таблиц

## 🔗 Полезные ссылки

- [Docker Setup](DOCKER_SETUP.md) - Детальная документация
- [Migrations Guide](MIGRATIONS.md) - Работа с миграциями
- [Getting Started](GETTING_STARTED.md) - Пошаговые сценарии
- [Architecture](architecture.md) - Архитектура сервиса

## 💡 Tips

- ✅ Миграции применяются **автоматически** - не нужно запускать вручную
- ✅ Используйте `make` команды для удобства
- ✅ Dev mode с `make up-dev` для hot reload
- ✅ Логи показывают процесс применения миграций
- ✅ Таблицы создаются через **Piccolo ORM**, не SQL скрипты

---

**Быстрая справка** | TgPost Service | 2025-11-02

