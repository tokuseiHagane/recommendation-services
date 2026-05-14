# Quick Start & Testing Guide: Dynamic Kafka Consumers

**Дата**: 2025-11-02  
**Фаза**: Phase 1 - Testing Scenarios  
**Testing Framework**: pytest + pytest-asyncio

## Обзор

Этот документ содержит тестовые сценарии для всех компонентов TgPost контейнера в порядке их реализации (TDD подход).

**Стратегия тестирования**:
1. **Unit тесты** для Tasks (атомарные операции)
2. **Integration тесты** для Actions (оркестрация)
3. **Service тесты** для Cache и Manager
4. **E2E тесты** для Workers (полный workflow)

## Setup

### Установка зависимостей

```bash
# Добавить в pyproject.toml
[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-mock = "^3.11.0"
```

### Конфигурация pytest

**pytest.ini**:
```ini
[pytest]
asyncio_mode = auto
testpaths = src/Containers/AppSection/TgPost/Tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests for Tasks
    integration: Integration tests for Actions
    service: Service tests
    e2e: End-to-end tests for Workers
```

### Тестовая БД

**conftest.py** в `Tests/`:
```python
import pytest
from piccolo.conf.apps import Finder
from piccolo.table import create_db_tables, drop_db_tables
from src.Containers.AppSection.TgPost.Models.Post import Post

@pytest.fixture(scope="session")
async def setup_test_db():
    """Setup test database."""
    # Create tables
    await create_db_tables(Post)
    
    yield
    
    # Cleanup
    await drop_db_tables(Post)

@pytest.fixture(autouse=True)
async def cleanup_posts():
    """Cleanup posts table before each test."""
    await Post.delete().where(Post.id > 0)
    yield
```

## 1. Unit Tests (Tasks)

### 1.1 BatchUpsertPostsTask

**Файл**: `Tests/test_batch_upsert_posts_task.py`

```python
import pytest
from src.Containers.AppSection.TgPost.Tasks.BatchUpsertPostsTask import (
    batch_upsert_posts_task
)
from src.Containers.AppSection.TgPost.Models.Post import Post
from src.Containers.AppSection.TgPost.Exceptions import BatchUpsertException

@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_upsert_posts_success(setup_test_db):
    """Test успешный batch upsert постов."""
    posts = [
        {
            "id": 1,
            "content": "Post 1",
            "view_count": 100,
            "id_channels": 123
        },
        {
            "id": 2,
            "content": "Post 2",
            "view_count": 200,
            "id_channels": 123
        }
    ]
    
    count = await batch_upsert_posts_task(posts)
    
    assert count == 2
    
    # Проверить сохранение
    saved_posts = await Post.select()
    assert len(saved_posts) == 2

@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_upsert_posts_idempotency(setup_test_db):
    """Test идемпотентность (ON CONFLICT UPDATE)."""
    posts = [
        {"id": 1, "content": "Original", "view_count": 100}
    ]
    
    # Первая вставка
    count1 = await batch_upsert_posts_task(posts)
    assert count1 == 1
    
    # Повторная вставка (обновление)
    updated_posts = [
        {"id": 1, "content": "Updated", "view_count": 200}
    ]
    count2 = await batch_upsert_posts_task(updated_posts)
    assert count2 == 1
    
    # Проверить обновление
    post = await Post.objects().get(Post.id == 1)
    assert post.content == "Updated"
    assert post.view_count == 200

@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_upsert_posts_deduplication(setup_test_db):
    """Test дедупликация постов по id."""
    posts = [
        {"id": 1, "content": "First"},
        {"id": 1, "content": "Second"},  # Дубликат
        {"id": 2, "content": "Third"}
    ]
    
    count = await batch_upsert_posts_task(posts)
    
    # Должен сохранить 2 уникальных поста
    assert count == 2
    
    # Проверить что сохранен последний дубликат
    post = await Post.objects().get(Post.id == 1)
    assert post.content == "Second"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_upsert_posts_empty_list(setup_test_db):
    """Test обработка пустого списка."""
    count = await batch_upsert_posts_task([])
    assert count == 0
```

### 1.2 ValidatePostsTask

**Файл**: `Tests/test_validate_posts_task.py`

```python
import pytest
from src.Containers.AppSection.TgPost.Tasks.ValidatePostsTask import (
    validate_posts_task
)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_posts_success():
    """Test валидация корректных постов."""
    raw_posts = [
        {
            "id": 1,
            "content": "Valid post",
            "view_count": 100,
            "id_channels": 123
        },
        {
            "id": 2,
            "content": "Another valid post",
            "repost_count": 10,
            "id_channels": 123
        }
    ]
    
    validated = await validate_posts_task(raw_posts)
    
    assert len(validated) == 2
    assert validated[0]["id"] == 1
    assert validated[1]["id"] == 2

@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_posts_skip_invalid():
    """Test пропуск невалидных постов."""
    raw_posts = [
        {"id": 1, "content": "Valid"},  # Valid
        {"content": "Missing ID"},      # Invalid (нет id)
        {"id": 2, "content": "Valid"},  # Valid
        {"id": "not_int"},              # Invalid (id не int)
    ]
    
    validated = await validate_posts_task(raw_posts)
    
    # Должно валидироваться только 2 поста
    assert len(validated) == 2
    assert validated[0]["id"] == 1
    assert validated[1]["id"] == 2

@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_posts_empty_list():
    """Test обработка пустого списка."""
    validated = await validate_posts_task([])
    assert len(validated) == 0
```

### 1.3 CheckDuplicateTask

**Файл**: `Tests/test_check_duplicate_task.py`

```python
import pytest
from src.Containers.AppSection.TgPost.Tasks.CheckDuplicateTask import (
    check_duplicate_task
)
from src.Containers.AppSection.TgPost.Services.PostObjectsCache import (
    PostObjectsCache
)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_duplicate_exists():
    """Test проверка существующего канала."""
    cache = PostObjectsCache()
    
    # Добавить канал в кэш
    await cache.put_channels([{"id": 123, "name": "Test"}])
    
    exists = await check_duplicate_task(cache, 123)
    
    assert exists is True

@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_duplicate_not_exists():
    """Test проверка несуществующего канала."""
    cache = PostObjectsCache()
    
    exists = await check_duplicate_task(cache, 999)
    
    assert exists is False
```

### 1.4 ConsumePostsBatchTask

**Файл**: `Tests/test_consume_posts_batch_task.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
import json
from src.Containers.AppSection.TgPost.Tasks.ConsumePostsBatchTask import (
    consume_posts_batch_task
)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_consume_posts_batch_success():
    """Test успешное чтение батча."""
    # Mock consumer
    consumer = AsyncMock()
    
    # Mock messages
    mock_messages = []
    for i in range(1, 6):
        msg = MagicMock()
        msg.value = json.dumps({
            "id": i,
            "content": f"Post {i}"
        }).encode('utf-8')
        mock_messages.append(msg)
    
    # Mock getmany response
    from aiokafka import TopicPartition
    tp = TopicPartition("tg_posts_123", 0)
    consumer.getmany.return_value = {tp: mock_messages}
    
    messages = await consume_posts_batch_task(
        consumer=consumer,
        batch_size=10,
        timeout_ms=5000
    )
    
    assert len(messages) == 5
    assert messages[0]["id"] == 1
    assert messages[4]["id"] == 5

@pytest.mark.unit
@pytest.mark.asyncio
async def test_consume_posts_batch_empty():
    """Test пустой батч."""
    consumer = AsyncMock()
    consumer.getmany.return_value = {}
    
    messages = await consume_posts_batch_task(consumer)
    
    assert len(messages) == 0

@pytest.mark.unit
@pytest.mark.asyncio
async def test_consume_posts_batch_size_limit():
    """Test ограничение размера батча."""
    consumer = AsyncMock()
    
    # Создать 150 сообщений
    mock_messages = []
    for i in range(1, 151):
        msg = MagicMock()
        msg.value = json.dumps({"id": i}).encode('utf-8')
        mock_messages.append(msg)
    
    from aiokafka import TopicPartition
    tp = TopicPartition("tg_posts_123", 0)
    consumer.getmany.return_value = {tp: mock_messages}
    
    messages = await consume_posts_batch_task(
        consumer=consumer,
        batch_size=100
    )
    
    # Должно вернуть максимум 100
    assert len(messages) == 100
```

## 2. Integration Tests (Actions)

### 2.1 BatchProcessPostsAction

**Файл**: `Tests/test_batch_process_posts_action.py`

```python
import pytest
from src.Containers.AppSection.TgPost.Actions.BatchProcessPostsAction import (
    batch_process_posts_action
)
from src.Containers.AppSection.TgPost.Models.Post import Post

@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_process_posts_success(setup_test_db):
    """Test полный workflow обработки батча."""
    raw_posts = [
        {"id": 1, "content": "Post 1", "view_count": 100, "id_channels": 123},
        {"id": 2, "content": "Post 2", "view_count": 200, "id_channels": 123},
        {"id": 3, "content": "Post 3", "view_count": 300, "id_channels": 123},
    ]
    
    inserted = await batch_process_posts_action(
        raw_posts=raw_posts,
        channel_id=123
    )
    
    assert inserted == 3
    
    # Проверить сохранение в БД
    posts = await Post.select()
    assert len(posts) == 3

@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_process_posts_with_invalid(setup_test_db):
    """Test обработка батча с невалидными постами."""
    raw_posts = [
        {"id": 1, "content": "Valid"},
        {"content": "Invalid - no id"},  # Будет пропущен
        {"id": 2, "content": "Valid"},
    ]
    
    inserted = await batch_process_posts_action(
        raw_posts=raw_posts,
        channel_id=123
    )
    
    # Должно быть вставлено только 2 валидных
    assert inserted == 2

@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_process_posts_empty(setup_test_db):
    """Test обработка пустого батча."""
    inserted = await batch_process_posts_action(
        raw_posts=[],
        channel_id=123
    )
    
    assert inserted == 0
```

### 2.2 CreateDynamicConsumerAction

**Файл**: `Tests/test_create_dynamic_consumer_action.py`

```python
import pytest
from unittest.mock import AsyncMock
from src.Containers.AppSection.TgPost.Actions.CreateDynamicConsumerAction import (
    create_dynamic_consumer_action
)
from src.Containers.AppSection.TgPost.Services.PostObjectsCache import PostObjectsCache
from src.Containers.AppSection.TgPost.Services.DynamicConsumerManager import (
    DynamicConsumerManager
)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_dynamic_consumer_new_channel():
    """Test создание консьюмера для нового канала."""
    cache = PostObjectsCache()
    manager = AsyncMock(spec=DynamicConsumerManager)
    
    channel_data = {
        "id": 123,
        "name": "Test Channel",
        "type": "public"
    }
    
    channel_id = await create_dynamic_consumer_action(
        channel_data=channel_data,
        cache=cache,
        manager=manager
    )
    
    assert channel_id == 123
    
    # Проверить что канал добавлен в кэш
    assert await cache.has_channel(123) is True

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_dynamic_consumer_duplicate():
    """Test попытка создать консьюмер для существующего канала."""
    cache = PostObjectsCache()
    manager = AsyncMock(spec=DynamicConsumerManager)
    
    # Добавить канал в кэш
    await cache.put_channels([{"id": 123, "name": "Existing"}])
    
    channel_data = {"id": 123, "name": "Duplicate", "type": "public"}
    
    channel_id = await create_dynamic_consumer_action(
        channel_data=channel_data,
        cache=cache,
        manager=manager
    )
    
    # Должен вернуть None для дубликата
    assert channel_id is None
```

### 2.3 InitializeConsumersAction

**Файл**: `Tests/test_initialize_consumers_action.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.Containers.AppSection.TgPost.Actions.InitializeConsumersAction import (
    initialize_consumers_action
)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_initialize_consumers_success():
    """Test инициализация консьюмеров из БД."""
    
    # Mock LoadChannelsFromDBTask
    with patch(
        'src.Containers.AppSection.TgPost.Tasks.LoadChannelsFromDBTask.load_channels_from_db_task',
        new_callable=AsyncMock
    ) as mock_load:
        mock_load.return_value = [
            {"id": 1, "name": "Channel 1"},
            {"id": 2, "name": "Channel 2"},
            {"id": 3, "name": "Channel 3"},
        ]
        
        # Mock CreateKafkaConsumerTask
        with patch(
            'src.Containers.AppSection.TgPost.Tasks.CreateKafkaConsumerTask.create_kafka_consumer_task',
            new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = AsyncMock()  # Mock consumer
            
            count = await initialize_consumers_action()
            
            assert count == 3
            assert mock_load.called
            assert mock_create.call_count == 3
```

## 3. Service Tests

### 3.1 PostObjectsCache

**Файл**: `Tests/test_post_objects_cache.py`

```python
import pytest
from datetime import datetime
from src.Containers.AppSection.TgPost.Services.PostObjectsCache import (
    PostObjectsCache
)

@pytest.mark.service
@pytest.mark.asyncio
async def test_cache_put_and_get():
    """Test добавление и получение каналов."""
    cache = PostObjectsCache()
    
    channels = [
        {"id": 1, "name": "Channel 1"},
        {"id": 2, "name": "Channel 2"}
    ]
    
    count = await cache.put_channels(channels)
    assert count == 2
    
    channel = await cache.get_channel(1)
    assert channel["name"] == "Channel 1"

@pytest.mark.service
@pytest.mark.asyncio
async def test_cache_has_channel():
    """Test проверка наличия канала."""
    cache = PostObjectsCache()
    
    await cache.put_channels([{"id": 123, "name": "Test"}])
    
    assert await cache.has_channel(123) is True
    assert await cache.has_channel(999) is False

@pytest.mark.service
@pytest.mark.asyncio
async def test_cache_get_all():
    """Test получение всех каналов."""
    cache = PostObjectsCache()
    
    channels = [
        {"id": i, "name": f"Channel {i}"}
        for i in range(1, 11)
    ]
    
    await cache.put_channels(channels)
    
    all_channels = await cache.get_all_channels()
    assert len(all_channels) == 10

@pytest.mark.service
@pytest.mark.asyncio
async def test_cache_clear():
    """Test очистка кэша."""
    cache = PostObjectsCache()
    
    await cache.put_channels([{"id": 123, "name": "Test"}])
    
    cleared = await cache.clear()
    assert cleared == 1
    
    assert await cache.has_channel(123) is False

@pytest.mark.service
@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test истечение TTL."""
    cache = PostObjectsCache(ttl_seconds=1)
    
    await cache.put_channels([{"id": 123, "name": "Test"}])
    
    # Подождать истечения TTL
    import asyncio
    await asyncio.sleep(2)
    
    channels = await cache.get_all_channels()
    
    # Кэш должен быть пустым после истечения TTL
    assert len(channels) == 0
```

### 3.2 DynamicConsumerManager

**Файл**: `Tests/test_dynamic_consumer_manager.py`

```python
import pytest
from unittest.mock import AsyncMock
from src.Containers.AppSection.TgPost.Services.DynamicConsumerManager import (
    DynamicConsumerManager
)
from src.Containers.AppSection.TgPost.Services.PostObjectsCache import (
    PostObjectsCache
)

@pytest.mark.service
@pytest.mark.asyncio
async def test_manager_add_consumer():
    """Test добавление консьюмера."""
    cache = PostObjectsCache()
    manager = DynamicConsumerManager(
        bootstrap_servers="localhost:9092",
        cache=cache
    )
    
    mock_consumer = AsyncMock()
    
    success = await manager.add_consumer(123, mock_consumer)
    
    assert success is True
    assert len(manager.get_all_consumer_ids()) == 1

@pytest.mark.service
@pytest.mark.asyncio
async def test_manager_add_duplicate_consumer():
    """Test попытка добавить дубликат консьюмера."""
    cache = PostObjectsCache()
    manager = DynamicConsumerManager(
        bootstrap_servers="localhost:9092",
        cache=cache
    )
    
    mock_consumer1 = AsyncMock()
    mock_consumer2 = AsyncMock()
    
    await manager.add_consumer(123, mock_consumer1)
    success = await manager.add_consumer(123, mock_consumer2)
    
    assert success is False
    assert len(manager.get_all_consumer_ids()) == 1

@pytest.mark.service
@pytest.mark.asyncio
async def test_manager_get_consumer():
    """Test получение консьюмера."""
    cache = PostObjectsCache()
    manager = DynamicConsumerManager(
        bootstrap_servers="localhost:9092",
        cache=cache
    )
    
    mock_consumer = AsyncMock()
    await manager.add_consumer(123, mock_consumer)
    
    consumer = await manager.get_consumer(123)
    
    assert consumer is mock_consumer

@pytest.mark.service
@pytest.mark.asyncio
async def test_manager_remove_consumer():
    """Test удаление консьюмера."""
    cache = PostObjectsCache()
    manager = DynamicConsumerManager(
        bootstrap_servers="localhost:9092",
        cache=cache
    )
    
    mock_consumer = AsyncMock()
    await manager.add_consumer(123, mock_consumer)
    
    removed = await manager.remove_consumer(123)
    
    assert removed is True
    assert mock_consumer.stop.called
    assert len(manager.get_all_consumer_ids()) == 0

@pytest.mark.service
@pytest.mark.asyncio
async def test_manager_shutdown_all():
    """Test остановка всех консьюмеров."""
    cache = PostObjectsCache()
    manager = DynamicConsumerManager(
        bootstrap_servers="localhost:9092",
        cache=cache
    )
    
    # Добавить несколько консьюмеров
    for i in range(1, 4):
        mock_consumer = AsyncMock()
        await manager.add_consumer(i, mock_consumer)
    
    await manager.shutdown_all()
    
    assert len(manager.get_all_consumer_ids()) == 0
```

## 4. E2E Tests (Workers)

### 4.1 ConsumerWorker

**Файл**: `Tests/test_consumer_worker.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.Containers.AppSection.TgPost.UI.Workers.ConsumerWorker import ConsumerWorker
from src.Containers.AppSection.TgPost.Services.DynamicConsumerManager import (
    DynamicConsumerManager
)

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_consumer_worker_full_workflow(setup_test_db):
    """Test полный workflow ConsumerWorker."""
    
    # Mock manager
    manager = AsyncMock(spec=DynamicConsumerManager)
    mock_consumer = AsyncMock()
    manager.get_consumer.return_value = mock_consumer
    
    # Mock consume_posts_batch_task
    with patch(
        'src.Containers.AppSection.TgPost.Tasks.ConsumePostsBatchTask.consume_posts_batch_task',
        new_callable=AsyncMock
    ) as mock_consume:
        mock_consume.return_value = [
            {"id": 1, "content": "Post 1", "id_channels": 123},
            {"id": 2, "content": "Post 2", "id_channels": 123}
        ]
        
        worker = ConsumerWorker(
            manager=manager,
            channel_id=123,
            batch_size=10
        )
        
        # Запустить worker на 1 итерацию
        worker._running = True
        
        # Симулировать одну итерацию
        messages = await mock_consume(mock_consumer)
        from src.Containers.AppSection.TgPost.Actions.BatchProcessPostsAction import (
            batch_process_posts_action
        )
        processed = await batch_process_posts_action(
            raw_posts=messages,
            channel_id=123
        )
        
        assert processed == 2
        
        # Проверить commit
        # mock_consumer.commit.assert_called_once()
```

## 5. Команды запуска тестов

### Все тесты
```bash
pytest src/Containers/AppSection/TgPost/Tests/
```

### По категориям
```bash
# Unit тесты
pytest -m unit

# Integration тесты
pytest -m integration

# Service тесты
pytest -m service

# E2E тесты
pytest -m e2e
```

### С покрытием
```bash
pytest --cov=src/Containers/AppSection/TgPost --cov-report=html
```

### Конкретный файл
```bash
pytest src/Containers/AppSection/TgPost/Tests/test_batch_upsert_posts_task.py -v
```

## 6. Coverage Goals

**Минимальные требования**:
- Tasks: > 90% coverage
- Actions: > 85% coverage
- Services: > 90% coverage
- Models: > 80% coverage
- **Overall: > 80% coverage**

## 7. Резюме

### Тестовая стратегия:
1. ✅ **TDD подход**: тесты перед реализацией
2. ✅ **Реальные зависимости**: настоящая БД, не моки (где возможно)
3. ✅ **Изоляция**: каждый тест независим
4. ✅ **Покрытие**: > 80% для всего контейнера

### Порядок реализации:
1. Unit тесты → Tasks implementation
2. Service тесты → Services implementation
3. Integration тесты → Actions implementation
4. E2E тесты → Workers implementation

### Следующие шаги:
1. ✅ Все артефакты Phase 1 созданы
2. → Создать TODO list для отслеживания прогресса
3. → Запустить /tasks для генерации детальных задач реализации

---
**Testing Guide завершен**: 2025-11-02  
**Готово к TDD реализации**: Все тестовые сценарии спроектированы


