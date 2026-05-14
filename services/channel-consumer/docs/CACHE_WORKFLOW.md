# Cache Workflow - Channel Objects

## Обзор

Новая архитектура использует **in-memory cache** для хранения полных объектов каналов как промежуточное хранилище между базой данных и Kafka.

## Workflow

```
┌─────────────────────────┐
│   Kafka: tg_channels    │
│   (Input)               │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Validation            │
│   (TgChannelService)    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Database Upsert       │
│   (PostgreSQL)          │
│   INSERT ON CONFLICT    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   🗄️ IN-MEMORY CACHE   │
│   Put full objects      │
│   (ChannelObjectsCache) │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   📖 Read from Cache    │
│   Get all channels      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   📢 Publish to Kafka   │
│   tg_channels_diff      │
│   (Output)              │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   🧹 Clear Cache        │
│   After successful      │
│   publish               │
└─────────────────────────┘
```

## Архитектура

### Компоненты

#### 1. ChannelObjectsCache (Service)

**Файл**: `src/Containers/tg_channel/services/channel_objects_cache.py`

**Назначение**: In-memory хранилище полных объектов каналов

**Особенности**:
- Хранит полные объекты (Dict), не только ID
- TTL для автоматической очистки (default: 300 секунд)
- Singleton pattern для общего доступа
- In-memory (Dict[str, Dict[str, Any]])

**API**:
```python
cache = get_channel_objects_cache()

# Put channels
await cache.put_channels([{...}, {...}])

# Get all channels
channels = await cache.get_all_channels()

# Get single channel
channel = await cache.get_channel("uuid")

# Clear cache
await cache.clear()

# Get stats
stats = await cache.get_stats()
```

---

#### 2. cache_channels_task (Task)

**Файл**: `src/Containers/tg_channel/tasks/cache_channels_task.py`

**Назначение**: Атомарная операция помещения объектов в кеш

**Использование**:
```python
from src.Containers.tg_channel.tasks.cache_channels_task import cache_channels_task

channels = [
    {"id": "uuid1", "name": "Channel 1"},
    {"id": "uuid2", "name": "Channel 2"}
]

cached_count = await cache_channels_task(channels)
```

**Возвращает**: Количество закешированных каналов

---

#### 3. publish_from_cache_task (Task)

**Файл**: `src/Containers/tg_channel/tasks/publish_from_cache_task.py`

**Назначение**: Чтение из кеша и публикация в Kafka

**Workflow**:
1. Читает все объекты из кеша
2. Публикует каждый в Kafka
3. Очищает кеш после успешной публикации

**Использование**:
```python
from src.Containers.tg_channel.tasks.publish_from_cache_task import publish_from_cache_task

result = await publish_from_cache_task(topic="tg_channels_diff")

# result:
# {
#     "channels_read_from_cache": 100,
#     "channels_published": 98,
#     "publish_errors": 2,
#     "cache_cleared": True
# }
```

---

#### 4. batch_process_channels_action (Action)

**Файл**: `src/Containers/tg_channel/actions/batch_process_channels_action.py`

**Новая логика**:
```python
async def batch_process_channels_action(
    raw_channels,
    use_cache=True,      # Enable cache workflow
    publish_diff=True    # Enable publishing
):
    # 1. Validate
    normalized = validate(raw_channels)
    
    # 2. Upsert to DB
    await batch_upsert_channels_task(normalized)
    
    # 3. Put into cache
    await cache_channels_task(normalized)
    
    # 4. Publish from cache
    result = await publish_from_cache_task()
    
    # Cache is automatically cleared after publish
```

---

## Формат данных

### Объекты в кеше

```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Channel Name",
    "type": "channel",
    "validated_at": "2024-12-14T10:00:00",
    # ... все другие поля
}
```

### Сообщения в Kafka

При публикации из кеша добавляются метаданные:

```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Channel Name",
    "type": "channel",
    "validated_at": "2024-12-14T10:00:00",
    "_diff_type": "upserted_channel",
    "_published_at": "2024-12-14T10:00:00",
    "_published_from": "cache"
}
```

---

## Конфигурация

### TTL кеша

По умолчанию: 300 секунд (5 минут)

```python
# Изменить TTL
cache = ChannelObjectsCache(ttl_seconds=600)  # 10 минут
```

### Включение/отключение

```python
# Включить кеш workflow (по умолчанию)
result = await batch_process_channels_action(
    channels,
    use_cache=True,
    publish_diff=True
)

# Отключить кеш workflow
result = await batch_process_channels_action(
    channels,
    use_cache=False,
    publish_diff=True
)
```

---

## Error Handling

### Ошибка кеширования

Если не удалось поместить в кеш:
- ✅ Каналы уже сохранены в БД
- ⚠️ Кеширование пропускается
- 📝 Ошибка логируется
- 🔄 Обработка продолжается

```python
try:
    cached = await cache_channels_task(channels)
except Exception as exc:
    logger.error(f"Failed to cache: {exc}")
    cached = 0
    # Continue processing
```

### Ошибка публикации из кеша

Если Kafka недоступен:
- ✅ Каналы уже в БД и кеше
- ⚠️ Публикация не удалась
- 📝 Ошибка логируется
- 🗑️ Кеш НЕ очищается (для retry)

```python
try:
    result = await publish_from_cache_task()
except Exception as exc:
    logger.error(f"Failed to publish: {exc}")
    # Cache remains for potential retry
```

### Очистка кеша

Кеш очищается автоматически:
- ✅ После успешной публикации
- ✅ При истечении TTL
- ✅ При вызове `clear()`

---

## Преимущества новой архитектуры

### 1. Согласованность

```
Database → Cache → Kafka
```

Все опубликованные в Kafka данные гарантированно сохранены в БД.

### 2. Простота

Линейный поток без сложной логики детекции новых каналов.

### 3. Надежность

- Ошибки кеширования не блокируют сохранение в БД
- Ошибки Kafka не блокируют upsert
- TTL предотвращает переполнение памяти

### 4. Тестируемость

Каждый компонент легко тестировать изолированно с mock.

---

## Миграция со старой архитектуры

### Старая логика

```python
# 1. Detect new channels (cache check)
new_channels = await detect_new_channels_task(channels)

# 2. Upsert
await batch_upsert_channels_task(channels)

# 3. Publish only new
await publish_channels_diff_task(new_channels)

# 4. Update cache with IDs
await update_cache_task(new_channel_ids)
```

### Новая логика

```python
# 1. Upsert
await batch_upsert_channels_task(channels)

# 2. Cache full objects
await cache_channels_task(channels)

# 3. Publish ALL from cache
await publish_from_cache_task()

# Cache автоматически очищается
```

### Ключевые отличия

| Аспект | Старая | Новая |
|--------|--------|-------|
| Кеш хранит | Только ID (Set[int]) | Полные объекты (Dict) |
| Публикация | Только новые каналы | ВСЕ upserted каналы |
| Детекция | Проверка кеша до upsert | Не требуется |
| Очистка | Ручное обновление ID | Автоматическая после publish |
| TTL | Нет | Есть (300s default) |

---

## Метрики

### Результат обработки

```python
{
    "channels_upserted": 100,
    "channels_cached": 100,
    "channels_published_from_cache": 98,
    "publish_errors": 2,
    "cache_cleared": True,
    "validation_errors": 0,
    "total_received": 100
}
```

### Cache stats

```python
stats = await cache.get_stats()

# {
#     "total_channels": 100,
#     "last_update": datetime(...),
#     "ttl_seconds": 300,
#     "is_expired": False,
#     "backend": "in-memory-objects"
# }
```

---

## Monitoring

### Логи

```
INFO: Batch upserted 100 channels
INFO: Cached 100 channels after upsert
INFO: Read 100 channels from cache for publishing
INFO: Published 98/100 channels from cache to 'tg_channels_diff' (2 errors)
INFO: Cleared 100 channels from cache after publishing
```

### Мониторинг кеша

```python
# Periodic check
stats = await cache.get_stats()
if stats["is_expired"]:
    logger.warning("Cache expired, clearing...")
```

---

## Troubleshooting

### Кеш не очищается

**Проблема**: Кеш растет и не очищается

**Решение**:
1. Проверить TTL: `cache.get_stats()["ttl_seconds"]`
2. Проверить логи публикации - очистка происходит только после успешного publish
3. Вручную очистить: `await cache.clear()`

### Каналы не публикуются

**Проблема**: Channels upserted но не published

**Проверить**:
1. `use_cache=True` и `publish_diff=True`?
2. Kafka доступен?
3. Логи показывают ошибки publish?

**Решение**:
```python
# Проверить кеш
stats = await cache.get_stats()
if stats["total_channels"] > 0:
    # Попробовать опубликовать вручную
    result = await publish_from_cache_task()
```

---

## Best Practices

1. **Всегда включай кеш**: `use_cache=True` для консистентности
2. **Мониторь размер кеша**: Периодически проверяй `get_stats()`
3. **Настрой TTL**: В зависимости от частоты обработки batch
4. **Обрабатывай ошибки**: Логируй, но не останавливай обработку
5. **Тестируй с mock**: Используй mock для Kafka в тестах

---

## Дальнейшее развитие

### Потенциальные улучшения

- [ ] Redis вместо in-memory для distributed setup
- [ ] Retry mechanism для failed publish
- [ ] Dead Letter Queue для permanent failures
- [ ] Metrics/Prometheus для cache statistics
- [ ] Configurable cache backend (in-memory/Redis)
- [ ] Partial cache clearing (по ID)
- [ ] Batch size limits для кеша

---

## FAQ

**Q: Зачем нужен кеш, если данные уже в БД?**

A: Кеш служит промежуточным хранилищем между DB и Kafka, обеспечивая:
- Единый источник данных для публикации
- Возможность retry без повторного запроса к БД
- Линейный flow без сложной логики

**Q: Что если кеш переполнится?**

A: TTL автоматически очищает устаревшие данные. Также кеш очищается после каждой успешной публикации.

**Q: Можно ли использовать Redis?**

A: Да, можно заменить реализацию `ChannelObjectsCache` на Redis-backed, сохранив тот же API.

**Q: Что если publish failed?**

A: Кеш остается не очищенным, можно повторить публикацию вручную или дождаться TTL expiration.

---

## Ссылки

- [TG_CHANNELS.md](TG_CHANNELS.md) - Общая документация
- [KAFKA_TOPICS.md](KAFKA_TOPICS.md) - Kafka топики
- [README.md](../README.md) - Главная страница

