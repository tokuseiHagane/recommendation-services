# Исследование: Динамические Kafka консьюмеры с шардированной обработкой

**Дата**: 2025-11-02  
**Фаза**: Phase 0 - Research & Analysis  
**Статус**: Завершено

## Цель исследования

Исследовать технические решения для реализации системы динамических Kafka консьюмеров с:
1. Реактивным созданием консьюмеров при появлении новых каналов
2. Batch processing постов для оптимизации производительности БД
3. Двухуровневым кэшированием для синхронизации данных
4. Соответствием принципам Porto архитектуры

## 1. Анализ существующей Porto структуры

### 1.1 Существующие контейнеры

**Текущий проект (Telegram-Posts-Consumers)**:
```
src/Containers/message/
├── actions/
│   ├── batch_store_messages_action.py  ← Паттерн batch processing
│   └── store_message_action.py
├── tasks/
│   ├── batch_insert_messages_task.py   ← Паттерн batch insert
│   └── consume_messages_task.py        ← Паттерн single consumer
├── model/
│   └── message_model.py
└── services/
    └── message_service.py
```

**Соседний проект (Telegram-Channel-Consumer)**:
```
src/Containers/tg_channel/
├── actions/
│   └── batch_process_channels_action.py  ← Похожий паттерн
├── tasks/
│   ├── batch_upsert_channels_task.py     ← ON CONFLICT UPDATE паттерн
│   ├── cache_channels_task.py
│   └── publish_from_cache_task.py
├── model/
│   └── tg_channel_model.py
└── services/
    ├── channel_objects_cache.py          ← Паттерн кэширования!
    └── tg_channel_service.py
```

**Ключевые находки**:
- ✅ Паттерн batch processing уже используется в `batch_store_messages_action.py`
- ✅ Паттерн ON CONFLICT UPDATE используется в `batch_upsert_channels_task.py`
- ✅ Паттерн in-memory кэширования реализован в `channel_objects_cache.py`
- ✅ Структура Porto последовательна в обоих проектах

**Решение**: Переиспользовать паттерны из обоих проектов для TgPost контейнера

### 1.2 Ship компоненты для переиспользования

**Kafka утилиты** (`Ship/utils/kafka_client.py`):
```python
# Существует KafkaClient для создания consumers/producers
# Может потребоваться расширение для множественных консьюмеров
```

**Конфигурация Kafka** (`Ship/config/kafka_config.py`):
```python
@dataclass
class KafkaConfig:
    bootstrap_servers: str
    topic: str                    # Для одного топика
    group_id: str
    enable_auto_commit: bool
    auto_offset_reset: str
    consumer_timeout_ms: int
```
**Проблема**: Конфигурация для одного топика, нужна для множественных
**Решение**: Расширить для поддержки dynamic topic patterns

**Database утилиты** (`Ship/utils/db.py`):
```python
# Piccolo database connection utilities
# Можно переиспользовать как есть
```

**Logging** (`Ship/config/logging.py`):
```python
# Logfire integration
# Можно переиспользовать как есть
```

### 1.3 Похожие паттерны в кодовой базе

**Batch Insert паттерн** (из `tg_channel/tasks/batch_upsert_channels_task.py`):
```python
await TgChannel.insert(*channel_rows).on_conflict(
    action="DO UPDATE",
    target=TgChannel.id,
    values=[TgChannel.name, TgChannel.type]
)
```
**Применение**: Использовать для BatchUpsertPostsTask

**Cache паттерн** (из `tg_channel/services/channel_objects_cache.py`):
```python
class ChannelObjectsCache:
    def __init__(self, ttl_seconds: int = 300):
        self._channels: Dict[str, Dict[str, Any]] = {}
        self._ttl_seconds = ttl_seconds
        self._last_update: Optional[datetime] = None
    
    async def put_channels(self, channels: List[Dict[str, Any]]) -> int
    async def get_all_channels(self) -> List[Dict[str, Any]]
    async def clear(self) -> int
```
**Применение**: Адаптировать для PostObjectsCache

## 2. AIOKafka для динамических консьюмеров

### 2.1 Множественные консьюмеры в одном процессе

**Исследование**: Как создать и управлять несколькими AIOKafkaConsumer в одном процессе?

**Context7 документация** (aiokafka):

**Паттерн 1: Manual partition assignment**
```python
# Каждый консьюмер для отдельного топика
consumer1 = AIOKafkaConsumer(
    "tg_posts_1",
    bootstrap_servers='localhost:9092',
    group_id="posts-consumer-group"
)

consumer2 = AIOKafkaConsumer(
    "tg_posts_2",
    bootstrap_servers='localhost:9092',
    group_id="posts-consumer-group"
)

await consumer1.start()
await consumer2.start()

# Управление в asyncio tasks
task1 = asyncio.create_task(process_consumer(consumer1))
task2 = asyncio.create_task(process_consumer(consumer2))
```

**Преимущества**:
- Простое управление жизненным циклом
- Независимые consumer groups для каждого топика
- Kafka автоматически балансирует партиции

**Недостатки**:
- Каждый консьюмер = отдельное соединение с Kafka
- Требует управления множественными asyncio tasks

**Решение для TgPost**: Использовать этот паттерн с DynamicConsumerManager

### 2.2 Batch consumption паттерн

**Context7 документация** (aiokafka getmany):

```python
# Batch consumption с getmany()
while True:
    result = await consumer.getmany(timeout_ms=10 * 1000)
    for tp, messages in result.items():
        if messages:
            await process_msg_batch(messages)
            # Commit progress only for this partition
            await consumer.commit({tp: messages[-1].offset + 1})
```

**Преимущества**:
- Эффективный batch processing
- Контроль размера батча через timeout
- Ручной commit после успешной обработки

**Применение для TgPost**:
```python
async def consume_posts_batch_task(
    consumer: AIOKafkaConsumer,
    batch_size: int = 100,
    timeout_ms: int = 10000
) -> List[Dict[str, Any]]:
    """
    Task: Прочитать батч сообщений из Kafka топика.
    
    Args:
        consumer: AIOKafkaConsumer instance
        batch_size: Максимальный размер батча
        timeout_ms: Timeout для getmany
    
    Returns:
        Список сообщений для обработки
    """
    messages = []
    result = await consumer.getmany(timeout_ms=timeout_ms)
    
    for tp, msgs in result.items():
        messages.extend(msgs)
        if len(messages) >= batch_size:
            break
    
    return messages[:batch_size]
```

### 2.3 Manual commit для надежности

**Context7 документация** (aiokafka manual commit):

```python
consumer = AIOKafkaConsumer(
    'topic',
    bootstrap_servers='localhost:9092',
    enable_auto_commit=False,  # Отключить auto-commit
    group_id="consumer-group"
)

# После успешной обработки батча
await process_batch(messages)
await consumer.commit()  # Ручной commit
```

**Преимущества**:
- Гарантия "at-least-once" семантики
- Commit только после успешной записи в БД
- Защита от потери данных при падении

**Применение для TgPost**: Использовать в BatchProcessPostsAction

### 2.4 Consumer Groups для масштабирования

**Context7 документация** (aiokafka consumer groups):

```python
# Несколько процессов с одним group_id
# Kafka автоматически распределит партиции

# Process 1
consumer = AIOKafkaConsumer(
    "my_topic",
    bootstrap_servers='localhost:9092',
    group_id="posts-processing-group"
)

# Process 2 (другой инстанс сервиса)
consumer2 = AIOKafkaConsumer(
    "my_topic",
    bootstrap_servers='localhost:9092',
    group_id="posts-processing-group"  # Тот же group_id!
)
# Kafka сделает rebalancing и распределит партиции
```

**Применение для TgPost**: 
- Использовать для горизонтального масштабирования
- Group ID: `posts-consumer-group-{channel_id}`
- Kafka автоматически распределит партиции между инстансами

## 3. Piccolo ORM для Post модели

### 3.1 Определение модели с JSONB

```python
from piccolo.table import Table
from piccolo.columns import (
    Integer, Text, Boolean, Timestamp, JSONB
)

class Post(Table):
    """
    Porto Model: Представляет пост из Telegram канала.
    
    Атрибуты соответствуют SQL схеме из post_model.md
    """
    id = Integer(primary_key=True)
    content = Text(null=True)
    repost_count = Integer(null=True, default=0)
    view_count = Integer(null=True, default=0)
    link = JSONB(null=True)  # Структура: {"url": "...", "type": "..."}
    message_timestamp = Timestamp(null=True)
    has_reactions = Boolean(null=True, default=False)
    id_channels = Integer(null=True)
    free_reactions_count = Integer(null=True, default=0)
    paid_reactions_count = Integer(null=True, default=0)
```

**Особенности**:
- JSONB для link - гибкая структура для разных типов ссылок
- null=True для всех полей кроме id (первичный ключ)
- default values для счетчиков

### 3.2 ON CONFLICT UPDATE паттерн

```python
async def batch_upsert_posts_task(posts: List[Dict[str, Any]]) -> int:
    """
    Task: Batch upsert постов с ON CONFLICT UPDATE.
    
    Идемпотентность: Если id существует, обновляет данные.
    """
    post_rows = [Post(**post_data) for post_data in posts]
    
    await Post.insert(*post_rows).on_conflict(
        action="DO UPDATE",
        target=Post.id,  # Конфликт по первичному ключу
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
    
    return len(post_rows)
```

**Преимущества**:
- Идемпотентность - можно обрабатывать сообщения повторно
- Обновление данных при изменении постов
- Эффективная batch операция

### 3.3 Индексы для производительности

```python
# В миграции:
class Migration:
    async def forwards(self):
        # Создать таблицу
        await self.create_table(Post)
        
        # Создать индекс на id_channels для быстрого поиска постов канала
        await self.run_sql(
            "CREATE INDEX idx_posts_id_channels ON posts(id_channels)"
        )
        
        # Создать индекс на message_timestamp для временных запросов
        await self.run_sql(
            "CREATE INDEX idx_posts_timestamp ON posts(message_timestamp)"
        )
```

## 4. Dishka DI паттерны

### 4.1 Singleton Services (APP scope)

```python
# TgPost/Providers.py
from dishka import Provider, Scope, provide

class TgPostProvider(Provider):
    
    @provide(scope=Scope.APP)
    def post_objects_cache(self) -> PostObjectsCache:
        """
        Singleton кэш для каналов.
        Живет весь жизненный цикл приложения.
        """
        return PostObjectsCache(ttl_seconds=300)
    
    @provide(scope=Scope.APP)
    def dynamic_consumer_manager(
        self,
        kafka_config: KafkaConfig,
        cache: PostObjectsCache
    ) -> DynamicConsumerManager:
        """
        Singleton менеджер консьюмеров.
        """
        return DynamicConsumerManager(
            bootstrap_servers=kafka_config.bootstrap_servers,
            cache=cache
        )
```

### 4.2 Factory для Kafka Consumers

```python
@provide(scope=Scope.REQUEST)
async def kafka_consumer(
    self,
    config: KafkaConfig,
    topic: str
) -> AsyncIterator[AIOKafkaConsumer]:
    """
    Factory для создания Kafka consumer.
    Автоматический cleanup при завершении.
    """
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=config.bootstrap_servers,
        group_id=f"posts-consumer-group-{topic}",
        enable_auto_commit=False,
        auto_offset_reset="earliest"
    )
    
    await consumer.start()
    
    try:
        yield consumer
    finally:
        await consumer.stop()
```

### 4.3 Dependency Graph

```
Application Start
    ↓
Ship/Providers.py
    ├─→ KafkaConfig (from settings)
    ├─→ Database connection (Piccolo)
    └─→ Logfire
    
TgPost/Providers.py
    ├─→ PostObjectsCache (singleton)
    ├─→ DynamicConsumerManager (singleton)
    │       ├─→ KafkaConfig
    │       └─→ PostObjectsCache
    └─→ Post Model

Workers
    ├─→ ChannelsDiffWorker
    │       ├─→ CreateDynamicConsumerAction
    │       │       ├─→ UpdateCacheTask
    │       │       │       └─→ PostObjectsCache
    │       │       └─→ CreateKafkaConsumerTask
    │       │               └─→ DynamicConsumerManager
    │       └─→ KafkaConsumer (factory)
    │
    └─→ ConsumerWorker (множественные инстансы)
            ├─→ BatchProcessPostsAction
            │       ├─→ ValidatePostsTask
            │       └─→ BatchUpsertPostsTask
            │               └─→ Post Model
            └─→ KafkaConsumer (factory)
```

## 5. Logfire для наблюдаемости

### 5.1 Трассировка Actions

```python
import logfire

async def batch_process_posts_action(
    raw_posts: List[Dict[str, Any]],
    channel_id: int
) -> int:
    """Action: Обработать батч постов."""
    
    with logfire.span(
        "batch_process_posts_action",
        channel_id=channel_id,
        batch_size=len(raw_posts)
    ):
        # Валидация
        with logfire.span("validate_posts"):
            validated = await validate_posts_task(raw_posts)
            logfire.info(f"Validated {len(validated)} posts")
        
        # Batch upsert
        with logfire.span("batch_upsert_posts"):
            inserted = await batch_upsert_posts_task(validated)
            logfire.info(f"Upserted {inserted} posts")
        
        return inserted
```

### 5.2 Мониторинг консьюмеров

```python
class DynamicConsumerManager:
    async def add_consumer(self, channel_id: int, consumer: AIOKafkaConsumer):
        """Добавить новый консьюмер с логированием."""
        
        logfire.info(
            "Adding consumer",
            channel_id=channel_id,
            topic=f"tg_posts_{channel_id}",
            total_consumers=len(self._consumers)
        )
        
        self._consumers[channel_id] = consumer
        
        # Метрика для мониторинга
        logfire.metric(
            "active_consumers_count",
            value=len(self._consumers)
        )
```

### 5.3 Batch metrics

```python
async def consume_posts_batch_task(
    consumer: AIOKafkaConsumer,
    batch_size: int = 100
) -> List[Dict[str, Any]]:
    """Task: Consume batch with metrics."""
    
    start_time = time.time()
    
    messages = await consumer.getmany(timeout_ms=10000)
    
    # Метрика latency
    duration = time.time() - start_time
    logfire.metric(
        "batch_consume_duration_seconds",
        value=duration,
        batch_size=len(messages)
    )
    
    return messages
```

## 6. Архитектурные решения

### 6.1 DynamicConsumerManager

**Ответственность**: Управление жизненным циклом множественных Kafka консьюмеров

**Интерфейс**:
```python
class DynamicConsumerManager:
    """
    Service: Управление динамическими Kafka консьюмерами.
    
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
    
    async def add_consumer(
        self,
        channel_id: int,
        topic: str
    ) -> AIOKafkaConsumer:
        """Создать и запустить новый консьюмер."""
        ...
    
    async def remove_consumer(self, channel_id: int) -> bool:
        """Остановить и удалить консьюмер."""
        ...
    
    async def get_consumer(self, channel_id: int) -> Optional[AIOKafkaConsumer]:
        """Получить консьюмер по channel_id."""
        ...
    
    async def get_all_consumers(self) -> List[AIOKafkaConsumer]:
        """Получить все активные консьюмеры."""
        ...
    
    async def shutdown_all(self):
        """Остановить все консьюмеры при shutdown."""
        ...
```

### 6.2 PostObjectsCache

**Ответственность**: Двухуровневое кэширование данных о каналах

**Уровни**:
1. **Персистентный слой**: Синхронизация с БД при старте (LoadChannelsFromDBTask)
2. **Оперативный слой**: Обновление через события tg_channels_diff (UpdateCacheTask)

**Интерфейс** (адаптирован из ChannelObjectsCache):
```python
class PostObjectsCache:
    """
    Service: In-memory кэш для данных о каналах.
    
    Цель: Быстрая валидация дубликатов при создании консьюмеров.
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
        """Проверить наличие канала (для CheckDuplicateTask)."""
        ...
    
    async def clear(self) -> int:
        """Очистить кэш."""
        ...
    
    async def sync_from_db(self, channels: List[Dict[str, Any]]):
        """Синхронизировать кэш с БД (персистентный слой)."""
        ...
```

### 6.3 Worker Architecture

**ChannelsDiffWorker**: Прослушивает tg_channels_diff
```python
class ChannelsDiffWorker:
    """
    Worker: Прослушивание tg_channels_diff для создания новых консьюмеров.
    
    Workflow:
    1. Consume события о новых каналах
    2. Валидировать через кэш (CheckDuplicateTask)
    3. Создать новый консьюмер (CreateDynamicConsumerAction)
    """
    
    async def start(self):
        consumer = AIOKafkaConsumer(
            "tg_channels_diff",
            bootstrap_servers=self._config.bootstrap_servers,
            group_id="channels-diff-consumer"
        )
        
        await consumer.start()
        
        async for msg in consumer:
            channel_data = json.loads(msg.value)
            
            # Action: Создать динамический консьюмер
            await self._create_consumer_action(channel_data)
```

**ConsumerWorker**: Обрабатывает посты из tg_posts_{id}
```python
class ConsumerWorker:
    """
    Worker: Обработка постов из топика tg_posts_{id}.
    
    Workflow:
    1. Consume батч постов (ConsumePostsBatchTask)
    2. Валидировать посты (ValidatePostsTask)
    3. Batch upsert в БД (BatchUpsertPostsTask)
    4. Commit offsets
    """
    
    async def start(self, channel_id: int):
        consumer = await self._manager.get_consumer(channel_id)
        
        while True:
            # Batch consumption
            messages = await consume_posts_batch_task(consumer)
            
            if not messages:
                continue
            
            # Action: Обработать батч
            await batch_process_posts_action(messages, channel_id)
            
            # Manual commit после успешной обработки
            await consumer.commit()
```

## 7. Решения по интеграции

### 7.1 Интеграция с Telegram-Channel-Consumer

**Топик tg_channels_diff**:
- **Producer**: Telegram-Channel-Consumer (микросервис)
- **Consumer**: TgPostsConsumers (этот сервис) через ChannelsDiffWorker
- **Формат сообщения**:
```json
{
  "id": 123,
  "name": "Channel Name",
  "type": "public",
  "timestamp": "2025-11-02T12:00:00Z"
}
```

**Топики tg_posts_{id}**:
- **Producer**: Telegram-Channel-Consumer
- **Consumer**: TgPostsConsumers через ConsumerWorker (множественные)
- **Формат сообщения**:
```json
{
  "id": 456,
  "content": "Post content...",
  "repost_count": 10,
  "view_count": 1000,
  "link": {"url": "...", "type": "..."},
  "message_timestamp": "2025-11-02T12:00:00Z",
  "has_reactions": true,
  "id_channels": 123,
  "free_reactions_count": 50,
  "paid_reactions_count": 5
}
```

### 7.2 Bootstrap процесс

```python
# src/Bootstrap.py
async def bootstrap_tg_post_service():
    """
    Bootstrap для TgPost сервиса.
    
    Workflow:
    1. Инициализировать DI контейнер (Dishka)
    2. Запустить InitializeConsumersAction (загрузить каналы из БД)
    3. Запустить ChannelsDiffWorker (прослушивать новые каналы)
    4. Создать ConsumerWorkers для всех существующих каналов
    """
    
    # 1. Dishka container
    container = make_async_container(
        TgPostProvider(),
        ShipProvider()
    )
    
    # 2. Initialize consumers from DB
    initialize_action = await container.get(InitializeConsumersAction)
    await initialize_action.execute()
    
    # 3. Start ChannelsDiffWorker
    channels_diff_worker = await container.get(ChannelsDiffWorker)
    asyncio.create_task(channels_diff_worker.start())
    
    # 4. Start ConsumerWorkers for existing channels
    manager = await container.get(DynamicConsumerManager)
    for channel_id in manager.get_all_consumer_ids():
        worker = ConsumerWorker(manager=manager, channel_id=channel_id)
        asyncio.create_task(worker.start())
    
    # Keep running
    await asyncio.Event().wait()
```

## 8. Ключевые решения и компромиссы

### Решение 1: Множественные консьюмеры в одном процессе
**Альтернатива**: Один консьюмер на процесс
**Выбор**: Множественные консьюмеры
**Обоснование**: 
- Упрощает управление
- Снижает overhead на процессы
- Kafka consumer groups обеспечивают изоляцию

### Решение 2: Manual commit после batch upsert
**Альтернатива**: Auto-commit
**Выбор**: Manual commit
**Обоснование**:
- Гарантия "at-least-once" семантики
- Commit только после успешной записи в БД
- Защита от потери данных

### Решение 3: In-memory кэш вместо Redis
**Альтернатива**: Redis для кэша каналов
**Выбор**: In-memory словарь
**Обоснование**:
- Простота реализации
- Низкая latency
- TTL для автоочистки
- Синхронизация с БД при старте

### Решение 4: ON CONFLICT UPDATE для идемпотентности
**Альтернатива**: INSERT only с проверкой существования
**Выбор**: ON CONFLICT UPDATE
**Обоснование**:
- Идемпотентность из коробки
- Обновление измененных постов
- Эффективная batch операция

## 9. Метрики и мониторинг

### Key Performance Indicators

**Throughput**:
- `posts_processed_per_second`: Количество постов в секунду
- `batches_processed_per_minute`: Количество батчей в минуту

**Latency**:
- `batch_processing_duration_seconds`: Время обработки батча
- `db_upsert_duration_seconds`: Время batch upsert в БД

**Consumer Health**:
- `active_consumers_count`: Количество активных консьюмеров
- `consumer_lag_seconds`: Задержка консьюмера относительно последнего сообщения

**Errors**:
- `validation_errors_count`: Количество ошибок валидации
- `upsert_errors_count`: Количество ошибок записи в БД
- `consumer_failures_count`: Количество падений консьюмеров

## Выводы

1. ✅ **AIOKafka** подходит для динамических консьюмеров с batch processing
2. ✅ **Piccolo ON CONFLICT UPDATE** обеспечивает идемпотентность
3. ✅ **In-memory кэш** достаточен для валидации дубликатов
4. ✅ **DynamicConsumerManager** упрощает управление множественными консьюмерами
5. ✅ **Manual commit** гарантирует надежность "at-least-once"
6. ✅ **Logfire** обеспечивает полную наблюдаемость
7. ✅ **Porto архитектура** сохраняется во всех компонентах

## Следующие шаги

1. ✅ Создать porto-structure.md с детальной структурой компонентов
2. ✅ Создать data-model.md с Piccolo схемами
3. ✅ Создать quickstart.md с тестовыми сценариями
4. → Запустить /tasks для генерации детальных задач реализации

---
**Исследование завершено**: 2025-11-02  
**Готово к Phase 1**: Porto Design & Contracts


