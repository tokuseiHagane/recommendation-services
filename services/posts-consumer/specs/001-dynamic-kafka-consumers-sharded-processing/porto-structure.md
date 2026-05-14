# Porto Structure: Динамические Kafka консьюмеры

**Дата**: 2025-11-02  
**Фаза**: Phase 1 - Porto Design  
**Container**: AppSection.TgPost

## Обзор структуры

```
src/Containers/AppSection/TgPost/
├── Actions/              # Бизнес use cases (4 файла)
├── Tasks/                # Атомарные операции (9 файлов)
├── Models/               # Piccolo ORM (1 файл)
├── Services/             # Сервисы контейнера (2 файла)
├── UI/Workers/           # Kafka workers (2 файла)
├── UI/CLI/               # CLI команды (1 файл)
├── Data/                 # DTOs (2 файла)
├── Exceptions/           # Исключения (3 файла)
├── Config/               # Конфигурация (1 файл)
├── migrations/           # Piccolo миграции
├── Tests/                # Тесты (5 файлов)
├── PiccoloApp.py         # Piccolo app config
├── Providers.py          # Dishka DI providers
└── __init__.py
```

## 1. Actions (Бизнес use cases)

### 1.1 InitializeConsumersAction

**Файл**: `Actions/InitializeConsumersAction.py`

**Ответственность**: Инициализация консьюмеров для всех существующих каналов при старте сервиса

**Workflow**:
```
1. LoadChannelsFromDBTask → Загрузить все каналы из БД
2. SyncCacheTask → Синхронизировать персистентный слой кэша
3. Для каждого канала:
   a. CreateKafkaConsumerTask → Создать консьюмер
   b. RegisterConsumerTask → Зарегистрировать в DynamicConsumerManager
4. Вернуть количество созданных консьюмеров
```

**Сигнатура**:
```python
async def initialize_consumers_action() -> int:
    """
    Action: Инициализировать консьюмеры из БД при старте.
    
    Returns:
        Количество созданных консьюмеров
        
    Raises:
        ConsumerCreationException: Если не удалось создать консьюмеры
    """
```

**Dependencies**:
- LoadChannelsFromDBTask
- UpdateCacheTask (для синхронизации)
- CreateKafkaConsumerTask
- RegisterConsumerTask
- PostObjectsCache (DI)
- DynamicConsumerManager (DI)

**Logfire трассировка**:
```python
with logfire.span(
    "initialize_consumers_action",
    total_channels=len(channels)
):
    # ... workflow
    logfire.info(f"Initialized {count} consumers")
```

---

### 1.2 CreateDynamicConsumerAction

**Файл**: `Actions/CreateDynamicConsumerAction.py`

**Ответственность**: Реактивное создание нового консьюмера при получении события о новом канале

**Workflow**:
```
1. CheckDuplicateTask → Проверить наличие в кэше
   → Если существует: вернуть существующий консьюмер
2. UpdateCacheTask → Добавить канал в оперативный слой кэша
3. CreateKafkaConsumerTask → Создать новый AIOKafkaConsumer
4. RegisterConsumerTask → Зарегистрировать в DynamicConsumerManager
5. Вернуть consumer ID
```

**Сигнатура**:
```python
async def create_dynamic_consumer_action(
    channel_data: Dict[str, Any]
) -> Optional[int]:
    """
    Action: Создать новый консьюмер для канала.
    
    Args:
        channel_data: Данные о канале из tg_channels_diff
            - id: int
            - name: str
            - type: str
    
    Returns:
        Channel ID если консьюмер создан, None если уже существует
        
    Raises:
        ConsumerCreationException: Если не удалось создать консьюмер
        CacheValidationException: Если данные канала невалидны
    """
```

**Dependencies**:
- CheckDuplicateTask
- UpdateCacheTask
- CreateKafkaConsumerTask
- RegisterConsumerTask
- PostObjectsCache (DI)
- DynamicConsumerManager (DI)

**Logfire трассировка**:
```python
with logfire.span(
    "create_dynamic_consumer_action",
    channel_id=channel_data["id"],
    channel_name=channel_data["name"]
):
    # ... workflow
    logfire.info(f"Created consumer for channel {channel_id}")
```

---

### 1.3 BatchProcessPostsAction

**Файл**: `Actions/BatchProcessPostsAction.py`

**Ответственность**: Обработка батча постов из Kafka топика с валидацией и сохранением в БД

**Workflow**:
```
1. ValidatePostsTask → Валидировать структуру всех постов
   → Пропустить невалидные, логировать warning
2. BatchUpsertPostsTask → Batch INSERT ON CONFLICT UPDATE
3. Вернуть количество успешно сохраненных постов
```

**Сигнатура**:
```python
async def batch_process_posts_action(
    raw_posts: List[Dict[str, Any]],
    *,
    channel_id: int,
    metadata_list: List[Dict[str, Any]] | None = None
) -> int:
    """
    Action: Обработать батч постов из Kafka топика.
    
    Args:
        raw_posts: Список raw постов из Kafka
        channel_id: ID канала для логирования
        metadata_list: Опциональные метаданные (topic, partition, offset)
    
    Returns:
        Количество успешно сохраненных постов
        
    Raises:
        BatchUpsertException: Если batch upsert полностью провалился
    """
```

**Dependencies**:
- ValidatePostsTask
- BatchUpsertPostsTask

**Logfire трассировка**:
```python
with logfire.span(
    "batch_process_posts_action",
    channel_id=channel_id,
    batch_size=len(raw_posts)
):
    with logfire.span("validate_posts"):
        validated = await validate_posts_task(raw_posts)
    
    with logfire.span("batch_upsert_posts"):
        inserted = await batch_upsert_posts_task(validated)
    
    logfire.metric(
        "posts_processed",
        value=inserted,
        channel_id=channel_id
    )
```

---

### 1.4 UpdateChannelCacheAction

**Файл**: `Actions/UpdateChannelCacheAction.py`

**Ответственность**: Обновление кэша каналов при получении событий из tg_channels_diff

**Workflow**:
```
1. ValidateChannelDataTask → Валидировать данные канала
2. UpdateCacheTask → Обновить оперативный слой кэша
3. Вернуть success status
```

**Сигнатура**:
```python
async def update_channel_cache_action(
    channel_data: Dict[str, Any]
) -> bool:
    """
    Action: Обновить кэш каналов из события.
    
    Args:
        channel_data: Данные канала из tg_channels_diff
    
    Returns:
        True если кэш обновлен, False если данные невалидны
        
    Raises:
        CacheValidationException: Если данные критически невалидны
    """
```

**Dependencies**:
- ValidateChannelDataTask (новый Task для валидации)
- UpdateCacheTask
- PostObjectsCache (DI)

---

## 2. Tasks (Атомарные операции)

### 2.1 LoadChannelsFromDBTask

**Файл**: `Tasks/LoadChannelsFromDBTask.py`

**Ответственность**: Загрузить все каналы из БД для инициализации

**Сигнатура**:
```python
async def load_channels_from_db_task() -> List[Dict[str, Any]]:
    """
    Task: Загрузить все каналы из БД.
    
    Примечание: Предполагается, что данные о каналах либо:
    1. Хранятся локально в TgPost контейнере (таблица channels)
    2. Или запрашиваются из БД Telegram-Channel-Consumer через shared DB
    
    Returns:
        Список каналов с полями: id, name, type
        
    Raises:
        Exception: Если не удалось загрузить из БД
    """
```

**Реализация** (вариант с локальной таблицей):
```python
# Если есть локальная таблица channels
from src.Containers.AppSection.TgPost.Models.Channel import Channel

async def load_channels_from_db_task() -> List[Dict[str, Any]]:
    channels = await Channel.select(
        Channel.id,
        Channel.name,
        Channel.type
    )
    
    return [
        {
            "id": ch["id"],
            "name": ch["name"],
            "type": ch["type"]
        }
        for ch in channels
    ]
```

**Альтернатива** (вариант с shared DB - доступ к БД Telegram-Channel-Consumer):
```python
# Если доступ к внешней БД через connection string
from src.Containers.AppSection.TgPost.Models.ExternalChannel import ExternalChannel

async def load_channels_from_db_task() -> List[Dict[str, Any]]:
    # Piccolo может подключаться к разным БД
    channels = await ExternalChannel.select()
    return [ch.to_dict() for ch in channels]
```

**Dependencies**: Piccolo ORM, Database connection

---

### 2.2 CreateKafkaConsumerTask

**Файл**: `Tasks/CreateKafkaConsumerTask.py`

**Ответственность**: Создать и запустить AIOKafkaConsumer для топика tg_posts_{id}

**Сигнатура**:
```python
async def create_kafka_consumer_task(
    channel_id: int,
    bootstrap_servers: str,
    group_id_prefix: str = "posts-consumer-group"
) -> AIOKafkaConsumer:
    """
    Task: Создать Kafka consumer для канала.
    
    Args:
        channel_id: ID канала
        bootstrap_servers: Kafka bootstrap servers
        group_id_prefix: Префикс для consumer group ID
    
    Returns:
        Запущенный AIOKafkaConsumer
        
    Raises:
        ConsumerCreationException: Если не удалось создать/запустить
    """
```

**Реализация**:
```python
from aiokafka import AIOKafkaConsumer
from src.Containers.AppSection.TgPost.Exceptions import ConsumerCreationException

async def create_kafka_consumer_task(
    channel_id: int,
    bootstrap_servers: str,
    group_id_prefix: str = "posts-consumer-group"
) -> AIOKafkaConsumer:
    
    topic = f"tg_posts_{channel_id}"
    group_id = f"{group_id_prefix}-{channel_id}"
    
    try:
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=False,  # Manual commit
            auto_offset_reset="earliest",
            consumer_timeout_ms=1000
        )
        
        await consumer.start()
        
        logger.info(f"Created consumer for {topic} with group {group_id}")
        
        return consumer
        
    except Exception as exc:
        raise ConsumerCreationException(
            f"Failed to create consumer for channel {channel_id}: {exc}"
        )
```

**Dependencies**: aiokafka, KafkaConfig

---

### 2.3 BatchUpsertPostsTask

**Файл**: `Tasks/BatchUpsertPostsTask.py`

**Ответственность**: Batch INSERT ON CONFLICT UPDATE постов в БД

**Сигнатура**:
```python
async def batch_upsert_posts_task(
    posts: List[Dict[str, Any]]
) -> int:
    """
    Task: Batch upsert постов с идемпотентностью.
    
    Args:
        posts: Список валидированных постов
    
    Returns:
        Количество upserted постов
        
    Raises:
        BatchUpsertException: Если batch upsert провалился
    """
```

**Реализация**:
```python
from src.Containers.AppSection.TgPost.Models.Post import Post
from src.Containers.AppSection.TgPost.Exceptions import BatchUpsertException

async def batch_upsert_posts_task(
    posts: List[Dict[str, Any]]
) -> int:
    
    if not posts:
        logger.warning("Attempted batch upsert with empty posts list")
        return 0
    
    try:
        # Дедупликация по id
        unique_posts = {}
        for post in posts:
            post_id = post.get("id")
            if post_id:
                unique_posts[post_id] = post
        
        # Создать Post instances
        post_rows = [
            Post(
                id=p["id"],
                content=p.get("content"),
                repost_count=p.get("repost_count", 0),
                view_count=p.get("view_count", 0),
                link=p.get("link"),
                message_timestamp=p.get("message_timestamp"),
                has_reactions=p.get("has_reactions", False),
                id_channels=p.get("id_channels"),
                free_reactions_count=p.get("free_reactions_count", 0),
                paid_reactions_count=p.get("paid_reactions_count", 0),
            )
            for p in unique_posts.values()
        ]
        
        # Batch upsert с ON CONFLICT UPDATE
        await Post.insert(*post_rows).on_conflict(
            action="DO UPDATE",
            target=Post.id,
            values=[
                Post.content,
                Post.repost_count,
                Post.view_count,
                Post.link,
                Post.message_timestamp,
                Post.has_reactions,
                Post.id_channels,
                Post.free_reactions_count,
                Post.paid_reactions_count,
            ]
        )
        
        logger.info(f"Successfully upserted {len(post_rows)} posts")
        
        return len(post_rows)
        
    except Exception as exc:
        logger.exception(f"Failed to batch upsert {len(posts)} posts: {exc}")
        raise BatchUpsertException(f"Batch upsert failed: {exc}")
```

**Dependencies**: Post Model, Piccolo ORM

---

### 2.4 ValidatePostsTask

**Файл**: `Tasks/ValidatePostsTask.py`

**Ответственность**: Валидировать структуру постов через Pydantic

**Сигнатура**:
```python
async def validate_posts_task(
    raw_posts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Task: Валидировать структуру постов.
    
    Args:
        raw_posts: Список raw постов из Kafka
    
    Returns:
        Список валидированных постов (пропускает невалидные)
    """
```

**Реализация**:
```python
from src.Containers.AppSection.TgPost.Data.PostDTO import PostDTO

async def validate_posts_task(
    raw_posts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    
    validated = []
    
    for idx, raw_post in enumerate(raw_posts):
        try:
            # Pydantic валидация
            post_dto = PostDTO(**raw_post)
            validated.append(post_dto.model_dump())
            
        except Exception as exc:
            logger.warning(
                f"Failed to validate post at index {idx}: {exc}. Skipping."
            )
            continue
    
    logger.debug(f"Validated {len(validated)}/{len(raw_posts)} posts")
    
    return validated
```

**Dependencies**: PostDTO (Pydantic model)

---

### 2.5 UpdateCacheTask

**Файл**: `Tasks/UpdateCacheTask.py`

**Ответственность**: Обновить PostObjectsCache с новыми каналами

**Сигнатура**:
```python
async def update_cache_task(
    cache: PostObjectsCache,
    channels: List[Dict[str, Any]]
) -> int:
    """
    Task: Обновить кэш каналов.
    
    Args:
        cache: PostObjectsCache instance (DI)
        channels: Список каналов для добавления в кэш
    
    Returns:
        Количество добавленных каналов
    """
```

**Реализация**:
```python
async def update_cache_task(
    cache: PostObjectsCache,
    channels: List[Dict[str, Any]]
) -> int:
    
    count = await cache.put_channels(channels)
    logger.debug(f"Updated cache with {count} channels")
    return count
```

**Dependencies**: PostObjectsCache (DI)

---

### 2.6 CheckDuplicateTask

**Файл**: `Tasks/CheckDuplicateTask.py`

**Ответственность**: Проверить наличие канала в кэше для исключения дубликатов

**Сигнатура**:
```python
async def check_duplicate_task(
    cache: PostObjectsCache,
    channel_id: int
) -> bool:
    """
    Task: Проверить наличие канала в кэше.
    
    Args:
        cache: PostObjectsCache instance (DI)
        channel_id: ID канала для проверки
    
    Returns:
        True если канал уже существует, False если нет
    """
```

**Реализация**:
```python
async def check_duplicate_task(
    cache: PostObjectsCache,
    channel_id: int
) -> bool:
    
    exists = await cache.has_channel(channel_id)
    
    if exists:
        logger.debug(f"Channel {channel_id} already exists in cache")
    
    return exists
```

**Dependencies**: PostObjectsCache (DI)

---

### 2.7 ConsumePostsBatchTask

**Файл**: `Tasks/ConsumePostsBatchTask.py`

**Ответственность**: Прочитать батч сообщений из Kafka консьюмера

**Сигнатура**:
```python
async def consume_posts_batch_task(
    consumer: AIOKafkaConsumer,
    batch_size: int = 100,
    timeout_ms: int = 10000
) -> List[Dict[str, Any]]:
    """
    Task: Consume батч постов из Kafka.
    
    Args:
        consumer: AIOKafkaConsumer instance
        batch_size: Максимальный размер батча
        timeout_ms: Timeout для getmany
    
    Returns:
        Список сообщений (parsed from JSON)
    """
```

**Реализация**:
```python
import json
from aiokafka import AIOKafkaConsumer

async def consume_posts_batch_task(
    consumer: AIOKafkaConsumer,
    batch_size: int = 100,
    timeout_ms: int = 10000
) -> List[Dict[str, Any]]:
    
    messages = []
    
    # Batch consumption с getmany
    result = await consumer.getmany(timeout_ms=timeout_ms)
    
    for tp, msgs in result.items():
        for msg in msgs:
            try:
                # Parse JSON
                post_data = json.loads(msg.value.decode('utf-8'))
                messages.append(post_data)
                
                if len(messages) >= batch_size:
                    break
                    
            except Exception as exc:
                logger.warning(f"Failed to parse message: {exc}")
                continue
        
        if len(messages) >= batch_size:
            break
    
    logger.debug(f"Consumed {len(messages)} messages from Kafka")
    
    return messages[:batch_size]
```

**Dependencies**: aiokafka

---

### 2.8 RegisterConsumerTask

**Файл**: `Tasks/RegisterConsumerTask.py`

**Ответственность**: Зарегистрировать консьюмер в DynamicConsumerManager

**Сигнатура**:
```python
async def register_consumer_task(
    manager: DynamicConsumerManager,
    channel_id: int,
    consumer: AIOKafkaConsumer
) -> bool:
    """
    Task: Зарегистрировать консьюмер в менеджере.
    
    Args:
        manager: DynamicConsumerManager instance (DI)
        channel_id: ID канала
        consumer: AIOKafkaConsumer instance
    
    Returns:
        True если зарегистрирован, False если уже существует
    """
```

**Реализация**:
```python
async def register_consumer_task(
    manager: DynamicConsumerManager,
    channel_id: int,
    consumer: AIOKafkaConsumer
) -> bool:
    
    success = await manager.add_consumer(channel_id, consumer)
    
    if success:
        logger.info(f"Registered consumer for channel {channel_id}")
    else:
        logger.warning(f"Consumer for channel {channel_id} already exists")
    
    return success
```

**Dependencies**: DynamicConsumerManager (DI)

---

### 2.9 ValidateChannelDataTask

**Файл**: `Tasks/ValidateChannelDataTask.py`

**Ответственность**: Валидировать данные канала из tg_channels_diff

**Сигнатура**:
```python
async def validate_channel_data_task(
    channel_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Task: Валидировать данные канала.
    
    Args:
        channel_data: Raw данные из Kafka
    
    Returns:
        Валидированные данные канала
        
    Raises:
        CacheValidationException: Если данные невалидны
    """
```

**Реализация**:
```python
from src.Containers.AppSection.TgPost.Data.ChannelDTO import ChannelDTO
from src.Containers.AppSection.TgPost.Exceptions import CacheValidationException

async def validate_channel_data_task(
    channel_data: Dict[str, Any]
) -> Dict[str, Any]:
    
    try:
        # Pydantic валидация
        channel_dto = ChannelDTO(**channel_data)
        return channel_dto.model_dump()
        
    except Exception as exc:
        raise CacheValidationException(
            f"Invalid channel data: {exc}"
        )
```

**Dependencies**: ChannelDTO (Pydantic model)

---

## 3. Models (Piccolo ORM)

### 3.1 Post

**Файл**: `Models/Post.py`

**Определение**:
```python
from piccolo.table import Table
from piccolo.columns import (
    Integer, Text, Boolean, Timestamp, JSONB
)

class Post(Table):
    """
    Porto Model: Представляет пост из Telegram канала.
    
    Соответствует SQL схеме из post_model.md.
    """
    
    id = Integer(primary_key=True)
    content = Text(null=True)
    repost_count = Integer(null=True, default=0)
    view_count = Integer(null=True, default=0)
    link = JSONB(null=True)
    message_timestamp = Timestamp(null=True)
    has_reactions = Boolean(null=True, default=False)
    id_channels = Integer(null=True)
    free_reactions_count = Integer(null=True, default=0)
    paid_reactions_count = Integer(null=True, default=0)
```

**Индексы** (создаются в миграции):
- `idx_posts_id_channels` на `id_channels` для быстрого поиска постов канала
- `idx_posts_timestamp` на `message_timestamp` для временных запросов

---

## 4. Services

### 4.1 PostObjectsCache

**Файл**: `Services/PostObjectsCache.py`

**Интерфейс**:
```python
class PostObjectsCache:
    """
    Service: In-memory кэш для данных о каналах.
    
    Двухуровневая система:
    - Персистентный слой: синхронизация с БД при старте
    - Оперативный слой: обновление через события из tg_channels_diff
    
    Паттерн: Singleton (Dishka APP scope)
    """
    
    def __init__(self, ttl_seconds: int = 300):
        self._channels: Dict[int, Dict[str, Any]] = {}
        self._ttl_seconds = ttl_seconds
        self._last_update: Optional[datetime] = None
    
    async def put_channels(self, channels: List[Dict[str, Any]]) -> int:
        """Добавить/обновить каналы в кэше."""
        ...
    
    async def get_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Получить канал по ID."""
        ...
    
    async def has_channel(self, channel_id: int) -> bool:
        """Проверить наличие канала."""
        ...
    
    async def get_all_channels(self) -> List[Dict[str, Any]]:
        """Получить все каналы из кэша."""
        ...
    
    async def clear(self) -> int:
        """Очистить кэш."""
        ...
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша."""
        ...
    
    def _is_expired(self) -> bool:
        """Проверить истечение TTL."""
        ...
```

**Реализация**: Адаптация из `../Telegram-Channel-Consumer/src/Containers/tg_channel/services/channel_objects_cache.py`

---

### 4.2 DynamicConsumerManager

**Файл**: `Services/DynamicConsumerManager.py`

**Интерфейс**:
```python
class DynamicConsumerManager:
    """
    Service: Управление динамическими Kafka консьюмерами.
    
    Ответственность:
    - Создание и регистрация консьюмеров
    - Отслеживание активных консьюмеров
    - Graceful shutdown всех консьюмеров
    
    Паттерн: Singleton (Dishka APP scope)
    """
    
    def __init__(
        self,
        bootstrap_servers: str,
        cache: PostObjectsCache
    ):
        self._consumers: Dict[int, AIOKafkaConsumer] = {}
        self._tasks: Dict[int, asyncio.Task] = {}
        self._bootstrap_servers = bootstrap_servers
        self._cache = cache
        self._lock = asyncio.Lock()
    
    async def add_consumer(
        self,
        channel_id: int,
        consumer: AIOKafkaConsumer
    ) -> bool:
        """
        Добавить новый консьюмер.
        
        Returns:
            True если добавлен, False если уже существует
        """
        ...
    
    async def remove_consumer(self, channel_id: int) -> bool:
        """Остановить и удалить консьюмер."""
        ...
    
    async def get_consumer(
        self,
        channel_id: int
    ) -> Optional[AIOKafkaConsumer]:
        """Получить консьюмер по channel_id."""
        ...
    
    async def get_all_consumers(self) -> Dict[int, AIOKafkaConsumer]:
        """Получить все активные консьюмеры."""
        ...
    
    def get_all_consumer_ids(self) -> List[int]:
        """Получить список всех channel IDs с активными консьюмерами."""
        ...
    
    async def shutdown_all(self):
        """Graceful shutdown всех консьюмеров."""
        ...
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику менеджера."""
        ...
```

**Реализация**:
```python
class DynamicConsumerManager:
    
    async def add_consumer(
        self,
        channel_id: int,
        consumer: AIOKafkaConsumer
    ) -> bool:
        async with self._lock:
            if channel_id in self._consumers:
                logger.warning(
                    f"Consumer for channel {channel_id} already exists"
                )
                return False
            
            self._consumers[channel_id] = consumer
            
            logfire.info(
                "Consumer added",
                channel_id=channel_id,
                total_consumers=len(self._consumers)
            )
            
            logfire.metric(
                "active_consumers_count",
                value=len(self._consumers)
            )
            
            return True
    
    async def shutdown_all(self):
        """Graceful shutdown всех консьюмеров."""
        logger.info(f"Shutting down {len(self._consumers)} consumers")
        
        for channel_id, consumer in self._consumers.items():
            try:
                await consumer.stop()
                logger.info(f"Stopped consumer for channel {channel_id}")
            except Exception as exc:
                logger.error(
                    f"Failed to stop consumer {channel_id}: {exc}"
                )
        
        # Очистить tasks
        for task in self._tasks.values():
            task.cancel()
        
        self._consumers.clear()
        self._tasks.clear()
        
        logger.info("All consumers shut down")
```

---

## 5. UI/Workers

### 5.1 ConsumerWorker

**Файл**: `UI/Workers/ConsumerWorker.py`

**Ответственность**: Обработка постов из топика tg_posts_{id}

**Интерфейс**:
```python
class ConsumerWorker:
    """
    Worker: Обработка постов из Kafka топика tg_posts_{id}.
    
    Workflow:
    1. Consume батч постов (ConsumePostsBatchTask)
    2. Обработать батч (BatchProcessPostsAction)
    3. Manual commit offsets
    4. Повторить
    """
    
    def __init__(
        self,
        manager: DynamicConsumerManager,
        channel_id: int,
        batch_size: int = 100,
        batch_timeout_ms: int = 10000
    ):
        self._manager = manager
        self._channel_id = channel_id
        self._batch_size = batch_size
        self._batch_timeout_ms = batch_timeout_ms
        self._running = False
    
    async def start(self):
        """Запустить worker loop."""
        ...
    
    async def stop(self):
        """Остановить worker gracefully."""
        ...
```

**Реализация**:
```python
async def start(self):
    """Запустить worker loop."""
    self._running = True
    
    consumer = await self._manager.get_consumer(self._channel_id)
    
    if not consumer:
        raise ValueError(f"No consumer for channel {self._channel_id}")
    
    logger.info(f"Starting ConsumerWorker for channel {self._channel_id}")
    
    while self._running:
        try:
            # 1. Consume batch
            messages = await consume_posts_batch_task(
                consumer=consumer,
                batch_size=self._batch_size,
                timeout_ms=self._batch_timeout_ms
            )
            
            if not messages:
                continue
            
            # 2. Process batch
            processed = await batch_process_posts_action(
                raw_posts=messages,
                channel_id=self._channel_id
            )
            
            # 3. Manual commit после успешной обработки
            if processed > 0:
                await consumer.commit()
                
                logger.debug(
                    f"Committed {processed} posts for channel {self._channel_id}"
                )
            
        except Exception as exc:
            logger.exception(
                f"Error in ConsumerWorker for channel {self._channel_id}: {exc}"
            )
            # Продолжить работу после ошибки
            await asyncio.sleep(5)
```

---

### 5.2 ChannelsDiffWorker

**Файл**: `UI/Workers/ChannelsDiffWorker.py`

**Ответственность**: Прослушивание топика tg_channels_diff и создание новых консьюмеров

**Интерфейс**:
```python
class ChannelsDiffWorker:
    """
    Worker: Прослушивание tg_channels_diff для реактивного создания консьюмеров.
    
    Workflow:
    1. Consume события о новых каналах
    2. Создать новый консьюмер (CreateDynamicConsumerAction)
    3. Запустить ConsumerWorker для нового канала
    """
    
    def __init__(
        self,
        kafka_config: KafkaConfig,
        create_consumer_action: CreateDynamicConsumerAction,
        manager: DynamicConsumerManager
    ):
        self._config = kafka_config
        self._create_action = create_consumer_action
        self._manager = manager
        self._running = False
    
    async def start(self):
        """Запустить worker loop."""
        ...
    
    async def stop(self):
        """Остановить worker gracefully."""
        ...
```

**Реализация**:
```python
async def start(self):
    """Запустить worker loop."""
    self._running = True
    
    # Создать consumer для tg_channels_diff
    consumer = AIOKafkaConsumer(
        "tg_channels_diff",
        bootstrap_servers=self._config.bootstrap_servers,
        group_id="channels-diff-consumer",
        auto_offset_reset="earliest"
    )
    
    await consumer.start()
    
    logger.info("ChannelsDiffWorker started, listening to tg_channels_diff")
    
    try:
        while self._running:
            async for msg in consumer:
                try:
                    # Parse channel data
                    channel_data = json.loads(msg.value.decode('utf-8'))
                    
                    # Create dynamic consumer
                    channel_id = await self._create_action(channel_data)
                    
                    if channel_id:
                        # Start ConsumerWorker для нового канала
                        worker = ConsumerWorker(
                            manager=self._manager,
                            channel_id=channel_id
                        )
                        asyncio.create_task(worker.start())
                        
                        logger.info(
                            f"Created and started worker for channel {channel_id}"
                        )
                
                except Exception as exc:
                    logger.exception(
                        f"Error processing channel diff event: {exc}"
                    )
                    continue
    
    finally:
        await consumer.stop()
        logger.info("ChannelsDiffWorker stopped")
```

---

## 6. Data (DTOs)

### 6.1 PostDTO

**Файл**: `Data/PostDTO.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class PostDTO(BaseModel):
    """
    DTO: Pydantic схема для валидации постов.
    """
    id: int = Field(..., description="Post ID (primary key)")
    content: Optional[str] = Field(None, description="Post content")
    repost_count: Optional[int] = Field(0, description="Repost count")
    view_count: Optional[int] = Field(0, description="View count")
    link: Optional[Dict[str, Any]] = Field(None, description="Link structure (JSONB)")
    message_timestamp: Optional[datetime] = Field(None, description="Post timestamp")
    has_reactions: Optional[bool] = Field(False, description="Has reactions flag")
    id_channels: Optional[int] = Field(None, description="Channel ID (FK)")
    free_reactions_count: Optional[int] = Field(0, description="Free reactions count")
    paid_reactions_count: Optional[int] = Field(0, description="Paid reactions count")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "content": "Post content...",
                "repost_count": 10,
                "view_count": 1000,
                "link": {"url": "https://...", "type": "external"},
                "message_timestamp": "2025-11-02T12:00:00Z",
                "has_reactions": True,
                "id_channels": 456,
                "free_reactions_count": 50,
                "paid_reactions_count": 5
            }
        }
```

---

### 6.2 ChannelDTO

**Файл**: `Data/ChannelDTO.py`

```python
from pydantic import BaseModel, Field
from typing import Optional

class ChannelDTO(BaseModel):
    """
    DTO: Pydantic схема для валидации данных о канале.
    """
    id: int = Field(..., description="Channel ID")
    name: str = Field(..., description="Channel name")
    type: str = Field(..., description="Channel type (public/private)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "name": "Tech News",
                "type": "public"
            }
        }
```

---

## 7. Exceptions

### 7.1 BatchUpsertException

**Файл**: `Exceptions/BatchUpsertException.py`

```python
class BatchUpsertException(Exception):
    """
    Exception: Ошибка batch upsert постов в БД.
    
    Использование:
    - Raise в BatchUpsertPostsTask при критической ошибке БД
    - Catch в BatchProcessPostsAction для логирования и возможного retry
    """
    pass
```

---

### 7.2 ConsumerCreationException

**Файл**: `Exceptions/ConsumerCreationException.py`

```python
class ConsumerCreationException(Exception):
    """
    Exception: Ошибка создания Kafka consumer.
    
    Использование:
    - Raise в CreateKafkaConsumerTask при ошибке создания/запуска
    - Catch в CreateDynamicConsumerAction для логирования
    """
    pass
```

---

### 7.3 CacheValidationException

**Файл**: `Exceptions/CacheValidationException.py`

```python
class CacheValidationException(Exception):
    """
    Exception: Ошибка валидации данных для кэша.
    
    Использование:
    - Raise в ValidateChannelDataTask при невалидных данных канала
    - Catch в UpdateChannelCacheAction для логирования
    """
    pass
```

---

## 8. Config

### 8.1 container_settings

**Файл**: `Config/container_settings.py`

```python
from dataclasses import dataclass
from src.Ship.config.settings import settings

@dataclass
class TgPostContainerSettings:
    """
    Конфигурация контейнера TgPost.
    """
    # Kafka settings
    kafka_bootstrap_servers: str = settings.KAFKA_BOOTSTRAP_SERVERS
    kafka_group_id_prefix: str = "posts-consumer-group"
    
    # Batch processing settings
    batch_size: int = 100
    batch_timeout_ms: int = 10000
    
    # Cache settings
    cache_ttl_seconds: int = 300
    
    # Consumer settings
    consumer_timeout_ms: int = 1000
    auto_offset_reset: str = "earliest"

# Singleton instance
container_settings = TgPostContainerSettings()
```

---

## 9. Providers (Dishka DI)

### 9.1 TgPostProvider

**Файл**: `Providers.py`

```python
from dishka import Provider, Scope, provide
from typing import AsyncIterator

from src.Containers.AppSection.TgPost.Services.PostObjectsCache import PostObjectsCache
from src.Containers.AppSection.TgPost.Services.DynamicConsumerManager import DynamicConsumerManager
from src.Containers.AppSection.TgPost.Config.container_settings import container_settings
from src.Ship.config.kafka_config import KafkaConfig

class TgPostProvider(Provider):
    """
    Dishka Provider для TgPost контейнера.
    """
    
    @provide(scope=Scope.APP)
    def post_objects_cache(self) -> PostObjectsCache:
        """Singleton кэш каналов."""
        return PostObjectsCache(
            ttl_seconds=container_settings.cache_ttl_seconds
        )
    
    @provide(scope=Scope.APP)
    def dynamic_consumer_manager(
        self,
        kafka_config: KafkaConfig,
        cache: PostObjectsCache
    ) -> DynamicConsumerManager:
        """Singleton менеджер консьюмеров."""
        return DynamicConsumerManager(
            bootstrap_servers=kafka_config.bootstrap_servers,
            cache=cache
        )
    
    # Actions (Request scope - созданы при вызове)
    @provide(scope=Scope.REQUEST)
    async def initialize_consumers_action(
        self,
        cache: PostObjectsCache,
        manager: DynamicConsumerManager,
        kafka_config: KafkaConfig
    ):
        from src.Containers.AppSection.TgPost.Actions.InitializeConsumersAction import (
            InitializeConsumersAction
        )
        return InitializeConsumersAction(
            cache=cache,
            manager=manager,
            kafka_config=kafka_config
        )
    
    @provide(scope=Scope.REQUEST)
    async def create_dynamic_consumer_action(
        self,
        cache: PostObjectsCache,
        manager: DynamicConsumerManager,
        kafka_config: KafkaConfig
    ):
        from src.Containers.AppSection.TgPost.Actions.CreateDynamicConsumerAction import (
            CreateDynamicConsumerAction
        )
        return CreateDynamicConsumerAction(
            cache=cache,
            manager=manager,
            kafka_config=kafka_config
        )
    
    # ... другие providers
```

---

## 10. PiccoloApp

**Файл**: `PiccoloApp.py`

```python
import os
from piccolo.conf.apps import AppConfig, table_finder

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

APP_CONFIG = AppConfig(
    app_name="TgPost",
    migrations_folder_path=os.path.join(
        CURRENT_DIRECTORY, "migrations"
    ),
    table_classes=table_finder(
        modules=["src.Containers.AppSection.TgPost.Models"],
        exclude_imported=True
    ),
    migration_dependencies=[],
    commands=[]
)
```

---

## Итоговая статистика компонентов

| Категория | Количество файлов | Описание |
|-----------|-------------------|----------|
| Actions | 4 | Бизнес use cases |
| Tasks | 9 | Атомарные операции |
| Models | 1 | Piccolo ORM модели |
| Services | 2 | Singleton сервисы |
| Workers | 2 | Kafka workers |
| DTOs | 2 | Pydantic схемы |
| Exceptions | 3 | Кастомные исключения |
| Config | 1 | Настройки контейнера |
| Providers | 1 | Dishka DI providers |
| PiccoloApp | 1 | Piccolo configuration |
| **Всего** | **26 файлов** | Полная структура TgPost |

---

**Следующий шаг**: Создать data-model.md с детальными Piccolo схемами и миграциями


