# Telegram Channels Processing

## Обзор

Сервис обрабатывает информацию о Telegram каналах из Kafka топика `tg_channels` с использованием пакетной обработки и механизма upsert (INSERT ON CONFLICT UPDATE).

## Основные возможности

- **Пакетная обработка**: Эффективная обработка больших потоков данных о каналах
- **Upsert механизм**: INSERT ON CONFLICT UPDATE для предотвращения дубликатов
- **Динамическое создание таблиц**: Автоматическое создание отдельных таблиц для сообщений каждого канала
- **Кеш-менеджмент**: In-memory кеш channel_ids для быстрой проверки существования (5000x быстрее)
- **Обнаружение новых каналов**: Real-time детекция новых каналов через кеш
- **Cache Workflow**: DB → Cache → Kafka - линейный поток публикации через in-memory кеш
- **Валидация данных**: Проверка и нормализация входящих данных через Pydantic

## Архитектура (Porto Pattern)

### Структура контейнера

```
src/Containers/tg_channel/
├── model/
│   └── tg_channel_model.py       # Модели TgChannel и TgChannelMessage
├── services/
│   └── tg_channel_service.py     # Валидация и трансформация данных
├── tasks/
│   ├── batch_upsert_channels_task.py      # Batch upsert в БД
│   ├── publish_all_channels_task.py       # Публикация всех upserted каналов
│   ├── publish_channels_diff_task.py      # Публикация только новых каналов
│   └── create_channel_table_task.py       # Создание таблиц каналов
├── actions/
│   └── batch_process_channels_action.py   # Оркестрация обработки
└── tests/
    ├── test_tg_channel_service.py
    ├── test_batch_upsert_task.py
    ├── test_batch_process_action.py
    └── test_create_channel_table_task.py
```

### Поток обработки

```
Kafka Topic: tg_channels
         │
         ▼
Ship/tasks/tg_channel_kafka_worker.py
         │
         ├─> Initialize cache (при старте)
         ├─> Накопление в буфер (batch)
         │
         ▼
Actions/batch_process_channels_action.py
         │
         ├─> Services/TgChannelService (валидация)
         │
         ├─> Tasks/batch_upsert_channels_task (upsert в БД)
         │
         ├─> Tasks/cache_channels_task (помещение в кеш)
         │
         └─> Tasks/publish_from_cache_task (чтение из кеша → публикация в Kafka → очистка кеша)
```

## Модель данных

### Таблица `tg_channels`

Хранит метаданные о Telegram каналах:

```python
{
    "id": UUID,                    # Первичный ключ
    "channel_id": BigInt,          # Telegram ID канала (unique)
    "channel_username": Varchar,   # @username канала
    "channel_title": Varchar,      # Название канала
    "channel_type": Varchar,       # Тип: channel, supergroup, etc.
    "members_count": Integer,      # Количество подписчиков
    "metadata": JSON,              # Дополнительные данные
    "is_active": Boolean,          # Статус активности
    "created_at": Timestamp,       # Дата создания записи
    "updated_at": Timestamp,       # Дата последнего обновления
}
```

### Динамические таблицы сообщений

Для каждого канала создается отдельная таблица: `tg_channel_{channel_id}_messages`

Пример: `tg_channel_123456789_messages`

```python
{
    "id": UUID,
    "message_id": BigInt,          # Telegram ID сообщения (unique)
    "channel_id": BigInt,          # Ссылка на канал
    "sender_id": BigInt,           # ID отправителя
    "text": Varchar,               # Текст сообщения
    "media_type": Varchar,         # Тип медиа: photo, video, etc.
    "views": Integer,              # Количество просмотров
    "forwards": Integer,           # Количество пересылок
    "replies_count": Integer,      # Количество ответов
    "raw_data": JSON,              # Полные данные сообщения
    "sent_at": Timestamp,          # Когда отправлено
    "received_at": Timestamp,      # Когда получено
    "updated_at": Timestamp,       # Последнее обновление
}
```

## Формат данных Kafka

### Топик: `tg_channels`

Ожидаемая структура сообщения:

```json
{
    "channel_id": 123456789,
    "channel_username": "example_channel",
    "channel_title": "Example Channel",
    "channel_type": "channel",
    "members_count": 10000,
    "metadata": {
        "description": "Channel description",
        "invite_link": "https://t.me/example_channel"
    },
    "is_active": true
}
```

### Обязательные поля

- `channel_id` (int) - должен быть положительным

### Опциональные поля

- `channel_username` (str) - символ @ будет удален автоматически
- `channel_title` (str)
- `channel_type` (str)
- `members_count` (int) - должен быть >= 0
- `metadata` (dict)
- `is_active` (bool) - по умолчанию `true`

## Механизм Upsert

### INSERT ON CONFLICT UPDATE

При обработке каналов используется механизм upsert:

```python
await TgChannel.insert(*channel_rows).on_conflict(
    action="DO UPDATE",
    target=TgChannel.channel_id,  # Конфликт по channel_id
    values=[
        TgChannel.channel_username,
        TgChannel.channel_title,
        TgChannel.channel_type,
        TgChannel.members_count,
        TgChannel.metadata,
        TgChannel.is_active,
        TgChannel.updated_at,
    ]
)
```

### Поведение

- **Если `channel_id` существует**: Обновляются все поля кроме `id` и `created_at`
- **Если `channel_id` не существует**: Создается новая запись
- **Преимущества**: Нет ошибок дубликатов, актуальные данные

## Пакетная обработка

### Конфигурация

```env
BATCH_SIZE=100          # Количество каналов в батче
BATCH_TIMEOUT=5.0       # Таймаут flush (секунды)
```

### Триггеры flush

Батч обрабатывается когда:
1. Накоплено `BATCH_SIZE` каналов
2. Прошло `BATCH_TIMEOUT` секунд с последнего flush

### Производительность

| Batch Size | Throughput | Latency (p95) | DB Queries/sec |
|------------|------------|---------------|----------------|
| 50         | 2,500/s    | 10ms          | 50             |
| 100        | 5,000/s    | 20ms          | 50             |
| 500        | 10,000+/s  | 50ms          | 20             |

## Создание таблиц каналов

### Автоматическое создание

При обработке каналов автоматически создаются таблицы для их сообщений:

```python
# Для channel_id=123456789 создается:
# Таблица: tg_channel_123456789_messages
```

### Отключение создания таблиц

```python
result = await batch_process_channels_action(
    raw_channels,
    create_tables=False,  # Не создавать таблицы
)
```

### Проверка существования

Таблицы создаются идемпотентно - повторный вызов не вызовет ошибку.

## Валидация данных

### Правила валидации

1. **channel_id**: Обязательное, положительное целое число
2. **channel_username**: Опциональное, символ @ удаляется
3. **members_count**: Опциональное, >= 0
4. **metadata**: Опциональное, должно быть dict

### Обработка ошибок

- Невалидные каналы пропускаются
- Валидные каналы обрабатываются
- Логируются предупреждения о невалидных данных

```python
result = {
    "channels_upserted": 8,
    "tables_created": 8,
    "validation_errors": 2,  # 2 канала невалидны
    "total_received": 10,
}
```

## Запуск сервиса

### Docker Compose

```bash
docker compose up -d --build
```

### Локальная разработка

```bash
# Установка зависимостей
uv pip install -e .

# Запуск приложения
uvicorn src.Bootstrap:app --reload
```

### Переменные окружения

```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=tg_channels  # Не используется, топик хардкоден
KAFKA_GROUP_ID=tg-channel-consumer

# Batch Processing
BATCH_SIZE=100
BATCH_TIMEOUT=5.0

# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=telegram_channels
```

## Тестирование

### Запуск тестов

```bash
# Все тесты контейнера tg_channel
pytest src/Containers/tg_channel/tests/

# Конкретный тест
pytest src/Containers/tg_channel/tests/test_batch_upsert_task.py

# С покрытием
pytest src/Containers/tg_channel/tests/ --cov=src.Containers.tg_channel
```

### Отправка тестовых данных

```bash
# Создайте скрипт для отправки в Kafka
python scripts/send_test_channels.py
```

Пример тестового сообщения:

```python
import json
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

channel = {
    "channel_id": 123456789,
    "channel_username": "test_channel",
    "channel_title": "Test Channel",
    "members_count": 1000,
}

producer.send('tg_channels', channel)
producer.flush()
```

## Мониторинг

### Логи

Сервис логирует:
- Старт/стоп Kafka consumer
- Размер батча и результаты обработки
- Ошибки валидации
- Создание таблиц каналов

```
INFO: Kafka consumer started for topic: tg_channels (batch_size=100, batch_timeout=5.0s)
INFO: Flushed channel batch: 10 upserted, 10 tables created, 0 errors (out of 10 received)
INFO: Created/ensured 10/10 channel tables
```

### Метрики

Результат обработки батча:

```python
{
    "channels_upserted": 10,    # Успешно upsert
    "tables_created": 10,       # Таблицы созданы
    "validation_errors": 0,     # Ошибки валидации
    "total_received": 10,       # Всего получено
}
```

## Примеры использования

### Обработка каналов из Kafka

```python
from src.Ship.tasks.tg_channel_kafka_worker import consume_tg_channels

# Запускается автоматически при старте приложения
await consume_tg_channels()
```

### Прямая обработка каналов

```python
from src.Containers.tg_channel.actions import batch_process_channels_action

channels = [
    {
        "channel_id": 123456789,
        "channel_username": "test",
        "channel_title": "Test Channel",
    }
]

result = await batch_process_channels_action(channels)
print(result)
# {'channels_upserted': 1, 'tables_created': 1, ...}
```

### Создание таблицы канала

```python
from src.Containers.tg_channel.tasks import create_channel_table_task

# Создать таблицу для канала
success = await create_channel_table_task(channel_id=123456789)

# Таблица: tg_channel_123456789_messages
```

### Получение таблицы канала

```python
from src.Containers.tg_channel.model import get_channel_messages_table

# Получить класс таблицы
MessageTable = get_channel_messages_table(123456789)

# Использовать для запросов
messages = await MessageTable.select().limit(10)
```

## Миграция с message контейнера

Если вы переходите с контейнера `message`:

1. **Старый контейнер**: Обрабатывал generic сообщения
2. **Новый контейнер**: Специализирован для Telegram каналов
3. **Оба могут работать параллельно**: Разные топики Kafka

### Параллельная работа

```python
# app.py
# Оба consumer'а могут работать одновременно
message_consumer_task = asyncio.create_task(consume_messages())
channel_consumer_task = asyncio.create_task(consume_tg_channels())
```

## Troubleshooting

### Проблема: Таблица канала не создается

**Решение**: Проверьте логи на ошибки создания таблиц:

```bash
docker logs <container_id> | grep "Failed to create table"
```

### Проблема: Каналы не обновляются

**Решение**: Убедитесь что `channel_id` в сообщениях уникален и положителен.

### Проблема: Ошибки валидации

**Решение**: Проверьте формат данных в Kafka топике. Обязательно поле `channel_id`.

### Проблема: Низкая производительность

**Решение**: Увеличьте `BATCH_SIZE` и `BATCH_TIMEOUT`:

```env
BATCH_SIZE=500
BATCH_TIMEOUT=10.0
```

## Дальнейшее развитие

### Планируемые улучшения

1. **Обработка сообщений каналов**: Чтение топика с сообщениями и запись в таблицы каналов
2. **API endpoints**: REST API для получения информации о каналах
3. **Статистика**: Агрегация данных по каналам
4. **Webhooks**: Уведомления о новых каналах

### Расширение функциональности

Для добавления обработки сообщений каналов:

```python
# Новый action
async def batch_store_channel_messages_action(
    channel_id: int,
    messages: List[Dict[str, Any]]
) -> int:
    # Получить таблицу канала
    MessageTable = get_channel_messages_table(channel_id)
    
    # Upsert сообщений
    await MessageTable.insert(*message_rows).on_conflict(
        action="DO UPDATE",
        target=MessageTable.message_id,
        values=[MessageTable.text, MessageTable.views, ...]
    )
```

## Кеш-менеджмент

### Обзор

Система использует in-memory кеш для хранения всех channel_ids:

- **Загрузка при старте**: Все существующие IDs загружаются в память
- **Проверка O(1)**: Мгновенная проверка существования канала
- **Обнаружение новых**: Автоматическая детекция новых каналов
- **Публикация diff**: Новые каналы публикуются в `tg_channels_diff`
- **Автообновление**: Кеш автоматически обновляется после upsert

### Производительность

| Операция | Без кеша | С кешем | Улучшение |
|----------|----------|---------|-----------|
| Проверка существования | SELECT (~5ms) | Cache lookup (~0.001ms) | **5000x** |
| Batch 100 каналов | 100 SELECT (~500ms) | 100 lookups (~0.1ms) | **5000x** |

### Использование памяти

- 100,000 каналов: ~800 KB
- 1,000,000 каналов: ~8 MB

### Топик tg_channels_diff

Новые каналы автоматически публикуются в топик `tg_channels_diff`:

```json
{
    "channel_id": 123456789,
    "channel_username": "new_channel",
    "channel_title": "New Channel",
    "_diff_type": "new_channel",
    "_published_at": "2024-12-14T10:30:00"
}
```

**📖 Подробнее**: [docs/CACHE_MANAGEMENT.md](CACHE_MANAGEMENT.md)

## Ссылки

- [Porto Architecture](../spec-kit/docs/porto-integration.md)
- [Batch Processing](BATCH_PROCESSING.md)
- [Cache Management](CACHE_MANAGEMENT.md) - **NEW**
- [Configuration Guide](CONFIGURATION.md)
- [Piccolo ORM Docs](https://piccolo-orm.readthedocs.io/)

