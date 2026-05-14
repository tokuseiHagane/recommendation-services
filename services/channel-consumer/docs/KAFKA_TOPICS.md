# Kafka Topics Configuration

## Overview

Приложение работает с несколькими Kafka топиками для обработки данных Telegram каналов.

## Topics

### Input Topic: `tg_channels`

**Назначение**: Входящий поток данных о Telegram каналах

**Формат сообщения**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Channel Name",
  "type": "channel"
}
```

**Поля**:
- `id` (UUID, optional) - Уникальный идентификатор канала, генерируется автоматически если не указан
- `name` (string, optional) - Название канала
- `type` (string, optional) - Тип канала (channel, group, supergroup, etc.)

**Обработка**:
- Все сообщения валидируются через Pydantic схему
- Невалидные сообщения логируются и пропускаются
- Валидные сообщения сохраняются в БД с помощью INSERT ON CONFLICT UPDATE

---

### Output Topic: `tg_channels_diff`

**Назначение**: Публикация информации о всех обработанных (upserted) каналах

**Формат сообщения**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Channel Name",
  "type": "channel",
  "validated_at": "2024-12-14T10:00:00",
  "_diff_type": "upserted_channel",
  "_published_at": "2024-12-14T10:00:00"
}
```

**Дополнительные поля**:
- `_diff_type` (string) - Тип события: `"upserted_channel"` (все каналы) или `"new_channel"` (только новые)
- `_published_at` (string) - Время публикации в формате ISO 8601
- `validated_at` (string) - Время валидации сообщения

**Кто публикует**:
- `publish_all_channels_task` - публикует ВСЕ upserted каналы с `_diff_type: "upserted_channel"`
- `publish_channels_diff_task` - публикует только НОВЫЕ каналы с `_diff_type: "new_channel"`

**Use cases**:
- Уведомление других сервисов о всех обработанных каналах
- Аудит и логирование изменений
- Downstream processing (например, обогащение данных)
- Синхронизация с другими системами

---

## Topic Management

### Automatic Topic Creation

Топики создаются автоматически при старте приложения через `ensure_application_topics()`:

```python
from src.Ship.utils.kafka_admin import ensure_application_topics

ensure_application_topics()
```

### Configuration

Kafka настройки задаются через переменные окружения:

```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=tg_channels
KAFKA_GROUP_ID=tg-channel-consumer
```

---

## Publishing Strategy

### Все каналы (ALL channels)

После успешного upsert в базу данных, **ВСЕ** обработанные каналы публикуются в `tg_channels_diff`:

```python
result = await batch_process_channels_action(
    channels,
    publish_diff=True  # По умолчанию
)

# result["all_channels_published"] - количество опубликованных каналов
```

### Только новые каналы (NEW channels only)

Дополнительно, если включен кеш, **новые** каналы публикуются отдельно:

```python
result = await batch_process_channels_action(
    channels,
    use_cache=True,      # Детектирует новые каналы
    publish_diff=True
)

# result["new_channels_published"] - количество новых каналов
```

---

## Message Flow

```
┌─────────────────┐
│  Producer       │
│  (External)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Topic: tg_channels         │
│  (Input)                    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Kafka Consumer             │
│  (batch processing)         │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Validation & Upsert        │
│  (batch_process_action)     │
└────────┬────────────────────┘
         │
         ├─────────────────────┐
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌──────────────────┐
│  Database       │   │  Topic:          │
│  (PostgreSQL)   │   │  tg_channels_diff│
│                 │   │  (Output)        │
└─────────────────┘   └──────────────────┘
```

---

## Error Handling

### Publishing Failures

Ошибки публикации в Kafka **не останавливают** обработку batch:

```python
try:
    published = await publish_all_channels_task(channels)
except Exception as exc:
    logger.error(f"Failed to publish: {exc}")
    # Processing continues, channels already saved to DB
```

### Individual Message Failures

Если не удается отправить отдельное сообщение, публикация продолжается для остальных:

```python
for channel in channels:
    try:
        await producer.send(topic, message)
    except Exception:
        # Log error, continue with next channel
        continue
```

---

## Monitoring

### Metrics

После обработки batch, логируются метрики:

```
{
    "channels_upserted": 100,           # Сохранено в БД
    "all_channels_published": 100,      # Опубликовано в Kafka (все)
    "new_channels_detected": 5,         # Обнаружено новых
    "new_channels_published": 5,        # Опубликовано новых отдельно
    "validation_errors": 2,             # Ошибки валидации
    "total_received": 102               # Всего получено
}
```

### Logs

```
INFO: Published 100/100 upserted channels to 'tg_channels_diff'
INFO: Published 5 new channels separately
```

---

## Testing

### Manual Publishing

Отправка тестового сообщения в `tg_channels`:

```bash
docker compose exec kafka kafka-console-producer \
  --broker-list localhost:9092 \
  --topic tg_channels

# Вставить JSON:
{"id": "550e8400-e29b-41d4-a716-446655440000", "name": "Test", "type": "channel"}
```

### Consuming from `tg_channels_diff`

Чтение сообщений из output топика:

```bash
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tg_channels_diff \
  --from-beginning
```

---

## Best Practices

1. **Мониторинг lag**: Следите за consumer lag в `tg_channels` топике
2. **Ретраи**: Для критичных downstream систем настройте retry mechanism
3. **Dead Letter Queue**: Рассмотрите DLQ для failed publications
4. **Partitioning**: При масштабировании используйте partitioning по `channel_id`
5. **Retention**: Настройте retention policy для `tg_channels_diff` в зависимости от потребностей

