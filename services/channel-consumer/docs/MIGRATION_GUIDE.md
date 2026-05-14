# Migration Guide: Single → Batch Processing

## Обзор

В проекте остался старый код для одиночной вставки сообщений. Этот документ описывает варианты работы с ним.

## Текущее состояние

### Kafka Worker
**Использует**: Batch processing (новый)
```python
# src/Ship/tasks/kafka_worker.py
await batch_store_messages_action(messages, metadata_list)
```

### Старые компоненты (НЕ используются в Kafka)
```
src/Containers/message/
├── actions/
│   └── store_message_action.py          ← Одиночная вставка
├── tasks/
│   └── consume_messages_task.py         ← process_incoming_message
└── ports/events/
    └── kafka_port.py                    ← Использует старый Task
```

## Опции миграции

### Опция 1: Оставить для совместимости (Рекомендуется)

**Когда использовать старый код:**

1. **HTTP API** - вставка одного сообщения через REST
   ```python
   # src/Containers/message/ports/http/message_controller.py
   from src.Containers.message.actions.store_message_action import store_message_action
   
   @post("/messages")
   async def create_single_message(self, data: MessageDTO) -> dict:
       """Insert a single message via HTTP API."""
       return await store_message_action(
           payload=data.payload,
           message_id=data.message_id,
           topic="manual",
       )
   ```

2. **Приоритетные сообщения** - bypass batch для критичных данных
   ```python
   if message.priority == "critical":
       await store_message_action(message.payload)
   else:
       batch_buffer.append(message)
   ```

3. **Тестирование** - простые unit тесты
   ```python
   async def test_single_message():
       result = await store_message_action(payload={"test": True})
       assert result["id"] is not None
   ```

**Преимущества:**
- ✅ Backward compatibility
- ✅ Гибкость для edge cases
- ✅ HTTP API поддержка
- ✅ Существующие тесты работают

**Недостатки:**
- ⚠️ Дублирование кода
- ⚠️ Нужно поддерживать оба варианта

### Опция 2: Удалить старый код

**Шаги:**
1. Удалить файлы
2. Обновить тесты
3. Создать wrapper для одиночной вставки

```bash
# 1. Удалить старые файлы
rm src/Containers/message/actions/store_message_action.py
rm src/Containers/message/tasks/consume_messages_task.py
rm src/Containers/message/ports/events/kafka_port.py

# 2. Удалить старые тесты
rm src/Containers/message/tests/test_message_action.py
rm src/Containers/message/tests/test_integration.py
```

**Создать wrapper:**
```python
# src/Containers/message/actions/store_single_message_action.py
from src.Containers.message.actions.batch_store_messages_action import batch_store_messages_action

async def store_single_message_action(
    payload: dict,
    *,
    message_id: str | None = None,
    topic: str | None = None,
    partition: int | None = None,
    offset: int | None = None,
) -> dict:
    """
    Store a single message by using batch insert with size=1.
    
    This is a wrapper around batch_store_messages_action for
    backward compatibility and HTTP API support.
    """
    raw_messages = [{"payload": payload}]
    metadata_list = [{
        "topic": topic,
        "partition": partition,
        "offset": offset,
    }]
    
    count = await batch_store_messages_action(raw_messages, metadata_list=metadata_list)
    
    if count == 0:
        raise ValueError("Failed to insert message")
    
    # Return the last inserted message (we only inserted one)
    from src.Containers.message.model.message_model import Message
    result = await Message.select().order_by(Message.id, ascending=False).first()
    return result.to_dict()
```

**Преимущества:**
- ✅ Единая кодовая база
- ✅ Меньше кода для поддержки
- ✅ Всё через batch API

**Недостатки:**
- ⚠️ Оверхед для одиночной вставки
- ⚠️ Нужно переписать тесты

### Опция 3: Гибридный подход (Best of both worlds)

Оставить старый код, но добавить переключатель:

```python
# src/Ship/config/settings.py
class Settings(BaseSettings):
    # ...
    USE_BATCH_PROCESSING: bool = Field(default=True)
    SINGLE_MESSAGE_BYPASS_BATCH: bool = Field(default=False)

# src/Ship/tasks/kafka_worker.py
if settings.USE_BATCH_PROCESSING:
    # Текущая реализация с батчингом
    await flush_batch(batch_messages, batch_metadata)
else:
    # Fallback на старую реализацию
    for msg, meta in zip(messages, metadata):
        await handle_kafka_message({"value": msg, "metadata": meta})
```

## Рекомендация

### Для Production: Опция 1 (Оставить старый код)

**Почему:**
1. **Стабильность** - не ломаем существующий функционал
2. **Гибкость** - поддержка разных сценариев
3. **HTTP API** - удобно для ручных операций
4. **Минимальный риск** - изменения только в Kafka worker

**Что делать:**
```bash
# 1. Документировать использование
# 2. Добавить комментарии в старые файлы
# 3. Обновить тесты (опционально)
```

### Пример документирования:

```python
# src/Containers/message/actions/store_message_action.py
"""
Single message insert action.

⚠️  NOTE: This action is NOT used by Kafka worker (uses batch processing).

Use cases:
- HTTP API for manual message insertion
- Priority/critical messages that bypass batch
- Testing and development
- Backward compatibility

For high-throughput Kafka processing, use batch_store_messages_action instead.

See: docs/BATCH_PROCESSING.md for details on batch processing.
"""
```

## HTTP API Example

Добавьте endpoint для одиночной вставки:

```python
# src/Containers/message/ports/http/message_controller.py
from litestar import get, post, Controller
from src.Containers.message.model.message_model import Message
from src.Containers.message.actions.store_message_action import store_message_action
from pydantic import BaseModel

class CreateMessageDTO(BaseModel):
    payload: dict
    message_id: str | None = None
    topic: str | None = None

class MessageController(Controller):
    path = "/messages"

    @get("/")
    async def list_messages(self) -> list[dict]:
        """Return recent messages (limit 20)."""
        rows = await Message.select().order_by("-received_at").limit(20)
        return [row.to_dict() for row in rows]
    
    @post("/")
    async def create_message(self, data: CreateMessageDTO) -> dict:
        """
        Insert a single message via HTTP API.
        
        This uses single-message insert, not batch processing.
        For high-throughput, use Kafka producer instead.
        """
        return await store_message_action(
            payload=data.payload,
            message_id=data.message_id,
            topic=data.topic or "http-api",
        )
    
    @get("/stats")
    async def get_stats(self) -> dict:
        """Get message statistics."""
        total = await Message.count()
        recent = await Message.count().where(
            Message.received_at >= "NOW() - INTERVAL '1 hour'"
        )
        return {
            "total_messages": total,
            "last_hour": recent,
        }
```

## Тестирование обоих подходов

```python
# tests/test_both_approaches.py
import pytest
from src.Containers.message.actions.store_message_action import store_message_action
from src.Containers.message.actions.batch_store_messages_action import batch_store_messages_action
from src.Containers.message.model.message_model import Message

@pytest.mark.asyncio
async def test_single_vs_batch():
    """Compare single and batch insert performance."""
    await Message.delete(force=True)
    
    # Single insert
    import time
    start = time.time()
    for i in range(100):
        await store_message_action(payload={"index": i})
    single_duration = time.time() - start
    
    await Message.delete(force=True)
    
    # Batch insert
    start = time.time()
    messages = [{"payload": {"index": i}} for i in range(100)]
    await batch_store_messages_action(messages)
    batch_duration = time.time() - start
    
    print(f"Single: {single_duration:.2f}s")
    print(f"Batch: {batch_duration:.2f}s")
    print(f"Speedup: {single_duration / batch_duration:.1f}x")
    
    assert batch_duration < single_duration
```

## Итоговая рекомендация

✅ **ОСТАВИТЬ СТАРЫЙ КОД** для:
- HTTP API
- Специальных случаев
- Backward compatibility

✅ **Документировать** использование каждого подхода

✅ **Kafka worker использует батчинг** (уже реализовано)

---

**См. также:**
- [BATCH_PROCESSING.md](./BATCH_PROCESSING.md) - Документация по батчингу
- [QUICK_START.md](./QUICK_START.md) - Быстрый старт

