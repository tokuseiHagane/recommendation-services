# Data Model: TgPost Container

**Дата**: 2025-11-02  
**Фаза**: Phase 1 - Data Model Design  
**ORM**: Piccolo 1.22+

## Обзор

TgPost контейнер использует одну основную таблицу `posts` для хранения постов из Telegram каналов.

**Схема БД**:
```
posts
├── id (INT, PK)
├── content (TEXT)
├── repost_count (INT)
├── view_count (INT)
├── link (JSONB)
├── message_timestamp (TIMESTAMP)
├── has_reactions (BOOLEAN)
├── id_channels (INT)  -- FK к channels (external microservice)
├── free_reactions_count (INT)
└── paid_reactions_count (INT)

Indexes:
- PRIMARY KEY: id
- idx_posts_id_channels: id_channels
- idx_posts_timestamp: message_timestamp
```

## 1. Piccolo Model: Post

### 1.1 Определение модели

**Файл**: `src/Containers/AppSection/TgPost/Models/Post.py`

```python
"""
Post Model: Представляет пост из Telegram канала.

Схема соответствует SQL определению из post_model.md.
"""

from piccolo.table import Table
from piccolo.columns import (
    Integer,
    Text,
    Boolean,
    Timestamp,
    JSONB
)
from typing import Dict, Any


class Post(Table):
    """
    Porto Model: Telegram post entity.
    
    Attributes:
        id: Unique post identifier (primary key)
        content: Post text content
        repost_count: Number of reposts
        view_count: Number of views
        link: JSONB structure with links
        message_timestamp: Post publication timestamp
        has_reactions: Whether post has reactions
        id_channels: Foreign key to channel (external microservice)
        free_reactions_count: Count of free reactions
        paid_reactions_count: Count of paid reactions
    
    Indexes:
        - PRIMARY KEY on id
        - idx_posts_id_channels on id_channels (for channel post lookups)
        - idx_posts_timestamp on message_timestamp (for time-based queries)
    
    Relationships:
        - id_channels → channels.id (external microservice, soft reference)
    
    ON CONFLICT behavior:
        - ON CONFLICT (id) DO UPDATE SET ... (idempotent upserts)
    """
    
    id = Integer(
        primary_key=True,
        help_text="Unique post identifier"
    )
    
    content = Text(
        null=True,
        help_text="Post text content"
    )
    
    repost_count = Integer(
        null=True,
        default=0,
        help_text="Number of reposts"
    )
    
    view_count = Integer(
        null=True,
        default=0,
        help_text="Number of views"
    )
    
    link = JSONB(
        null=True,
        help_text="Link structure (JSONB): {url: str, type: str, ...}"
    )
    
    message_timestamp = Timestamp(
        null=True,
        help_text="Post publication timestamp"
    )
    
    has_reactions = Boolean(
        null=True,
        default=False,
        help_text="Whether post has reactions"
    )
    
    id_channels = Integer(
        null=True,
        help_text="Foreign key to channel (external microservice)"
    )
    
    free_reactions_count = Integer(
        null=True,
        default=0,
        help_text="Count of free reactions"
    )
    
    paid_reactions_count = Integer(
        null=True,
        default=0,
        help_text="Count of paid reactions"
    )
    
    # Table metadata
    class Meta:
        tablename = "posts"
        help_text = "Telegram posts from channels"
```

### 1.2 Пример использования

**Создание записи**:
```python
post = Post(
    id=123,
    content="Test post content",
    repost_count=10,
    view_count=1000,
    link={"url": "https://t.me/...", "type": "external"},
    message_timestamp=datetime.now(),
    has_reactions=True,
    id_channels=456,
    free_reactions_count=50,
    paid_reactions_count=5
)

await post.save()
```

**Batch insert with ON CONFLICT**:
```python
posts = [
    Post(id=1, content="Post 1", id_channels=100),
    Post(id=2, content="Post 2", id_channels=100),
]

await Post.insert(*posts).on_conflict(
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
```

**Запросы**:
```python
# Получить все посты канала
posts = await Post.select().where(Post.id_channels == 456)

# Получить посты за последний день
from datetime import datetime, timedelta
yesterday = datetime.now() - timedelta(days=1)
recent_posts = await Post.select().where(
    Post.message_timestamp > yesterday
).order_by(Post.message_timestamp, ascending=False)

# Получить популярные посты
popular = await Post.select().where(
    Post.view_count > 1000
).order_by(Post.view_count, ascending=False).limit(10)
```

## 2. Миграции

### 2.1 Создание таблицы posts

**Файл**: `src/Containers/AppSection/TgPost/migrations/2025-11-02T00-00-00-000000.py`

```python
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import (
    Integer, Text, Boolean, Timestamp, JSONB
)

ID = "2025-11-02T00:00:00:000000"
VERSION = "1.22.0"
DESCRIPTION = "Create posts table with indexes"


async def forwards():
    manager = MigrationManager(
        migration_id=ID,
        app_name="TgPost",
        description=DESCRIPTION
    )

    # Создать таблицу posts
    manager.add_table(
        class_name="Post",
        tablename="posts",
        schema=None,
        columns=None
    )
    
    # Добавить колонки
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="id",
        db_column_name="id",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "primary_key": True,
            "null": False,
            "help_text": "Unique post identifier"
        },
        schema=None
    )
    
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="content",
        db_column_name="content",
        column_class_name="Text",
        column_class=Text,
        params={
            "null": True,
            "help_text": "Post text content"
        },
        schema=None
    )
    
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="repost_count",
        db_column_name="repost_count",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "null": True,
            "default": 0,
            "help_text": "Number of reposts"
        },
        schema=None
    )
    
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="view_count",
        db_column_name="view_count",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "null": True,
            "default": 0,
            "help_text": "Number of views"
        },
        schema=None
    )
    
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="link",
        db_column_name="link",
        column_class_name="JSONB",
        column_class=JSONB,
        params={
            "null": True,
            "help_text": "Link structure (JSONB)"
        },
        schema=None
    )
    
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="message_timestamp",
        db_column_name="message_timestamp",
        column_class_name="Timestamp",
        column_class=Timestamp,
        params={
            "null": True,
            "help_text": "Post publication timestamp"
        },
        schema=None
    )
    
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="has_reactions",
        db_column_name="has_reactions",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "null": True,
            "default": False,
            "help_text": "Whether post has reactions"
        },
        schema=None
    )
    
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="id_channels",
        db_column_name="id_channels",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "null": True,
            "help_text": "Foreign key to channel"
        },
        schema=None
    )
    
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="free_reactions_count",
        db_column_name="free_reactions_count",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "null": True,
            "default": 0,
            "help_text": "Count of free reactions"
        },
        schema=None
    )
    
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="paid_reactions_count",
        db_column_name="paid_reactions_count",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "null": True,
            "default": 0,
            "help_text": "Count of paid reactions"
        },
        schema=None
    )
    
    # Создать индексы
    await manager.run_sql(
        "CREATE INDEX idx_posts_id_channels ON posts(id_channels)"
    )
    
    await manager.run_sql(
        "CREATE INDEX idx_posts_timestamp ON posts(message_timestamp)"
    )
    
    return manager


async def backwards():
    manager = MigrationManager(
        migration_id=ID,
        app_name="TgPost",
        description=DESCRIPTION
    )
    
    # Удалить индексы
    await manager.run_sql("DROP INDEX IF EXISTS idx_posts_id_channels")
    await manager.run_sql("DROP INDEX IF EXISTS idx_posts_timestamp")
    
    # Удалить таблицу
    manager.drop_table(
        class_name="Post",
        tablename="posts",
        schema=None
    )
    
    return manager
```

### 2.2 Команды миграций

**Создать миграцию**:
```bash
piccolo migrations new TgPost --auto
```

**Применить миграции**:
```bash
piccolo migrations forwards TgPost
```

**Откатить миграции**:
```bash
piccolo migrations backwards TgPost
```

**Проверить статус**:
```bash
piccolo migrations check TgPost
```

## 3. JSONB структура для link

### 3.1 Примеры структур

**External link**:
```json
{
  "url": "https://example.com/article",
  "type": "external",
  "title": "Article Title",
  "preview_image": "https://example.com/image.jpg"
}
```

**Telegram link**:
```json
{
  "url": "https://t.me/channel/123",
  "type": "telegram",
  "channel": "channel_name",
  "message_id": 123
}
```

**Multiple links**:
```json
{
  "links": [
    {"url": "https://example1.com", "type": "external"},
    {"url": "https://example2.com", "type": "external"}
  ]
}
```

### 3.2 Валидация JSONB в Pydantic

**В PostDTO**:
```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List

class LinkStructure(BaseModel):
    """Структура для link поля."""
    url: str
    type: str = Field(..., pattern="^(external|telegram|other)$")
    title: Optional[str] = None
    preview_image: Optional[str] = None
    channel: Optional[str] = None
    message_id: Optional[int] = None

class PostDTO(BaseModel):
    id: int
    content: Optional[str] = None
    link: Optional[Dict[str, Any]] = None  # JSONB
    # ... другие поля
    
    @field_validator('link')
    @classmethod
    def validate_link(cls, v):
        """Валидировать link структуру."""
        if v is None:
            return v
        
        # Проверить наличие url если link не None
        if isinstance(v, dict) and 'url' in v:
            return v
        
        # Или проверить список ссылок
        if isinstance(v, dict) and 'links' in v:
            if not isinstance(v['links'], list):
                raise ValueError("links must be a list")
            return v
        
        raise ValueError("Invalid link structure")
```

## 4. Индексы и производительность

### 4.1 Созданные индексы

**idx_posts_id_channels**:
```sql
CREATE INDEX idx_posts_id_channels ON posts(id_channels);
```
- **Назначение**: Быстрый поиск всех постов канала
- **Использование**: `WHERE id_channels = ?`
- **Cardinalality**: High (много постов на канал)

**idx_posts_timestamp**:
```sql
CREATE INDEX idx_posts_timestamp ON posts(message_timestamp);
```
- **Назначение**: Временные запросы (последние посты, посты за период)
- **Использование**: `WHERE message_timestamp > ? ORDER BY message_timestamp DESC`
- **Cardinalality**: Medium

### 4.2 Composite index (опционально)

Если часто запрашиваются последние посты канала:
```sql
CREATE INDEX idx_posts_channel_timestamp 
ON posts(id_channels, message_timestamp DESC);
```

**Запрос**:
```python
latest_posts = await Post.select().where(
    Post.id_channels == 456
).order_by(
    Post.message_timestamp, ascending=False
).limit(20)
```

### 4.3 JSONB индексы (опционально)

Для быстрого поиска по JSONB полям:
```sql
-- GIN index на link для поиска по содержимому
CREATE INDEX idx_posts_link_gin ON posts USING GIN (link);

-- Поиск постов с конкретным типом ссылки
SELECT * FROM posts WHERE link @> '{"type": "telegram"}';
```

**В Piccolo** (через raw SQL):
```python
# Поиск постов с telegram ссылками
posts = await Post.raw(
    "SELECT * FROM posts WHERE link @> %s",
    '{"type": "telegram"}'
)
```

## 5. Стратегия данных

### 5.1 ON CONFLICT UPDATE (Idempotency)

**Поведение**:
- При вставке поста с существующим `id`: обновить все поля
- Гарантирует идемпотентность при повторной обработке сообщений Kafka
- Позволяет обновлять данные постов (счетчики views, reposts, reactions)

**Пример**:
```python
# Первая вставка: создает запись
await Post.insert(
    Post(id=123, content="Original", view_count=100)
).on_conflict(...)

# Повторная вставка: обновляет запись
await Post.insert(
    Post(id=123, content="Updated", view_count=200)
).on_conflict(
    action="DO UPDATE",
    target=Post.id,
    values=[Post.content, Post.view_count]
)

# Результат: id=123, content="Updated", view_count=200
```

### 5.2 Null values handling

**Все поля кроме id nullable**:
- Позволяет частичные обновления
- Kafka сообщения могут не содержать всех полей
- Default values для счетчиков (0 для int, False для bool)

**Пример**:
```python
# Минимальная вставка
await Post(id=123, content="Text").save()

# Результат:
# {
#   "id": 123,
#   "content": "Text",
#   "repost_count": 0,  # default
#   "view_count": 0,     # default
#   "has_reactions": False,  # default
#   "link": None,
#   "message_timestamp": None,
#   ...
# }
```

### 5.3 Soft references (id_channels)

**id_channels не является FK constraint**:
- Канал находится в другом микросервисе (Telegram-Channel-Consumer)
- Используется soft reference (INTEGER без FOREIGN KEY)
- Валидация через кэш при обработке

**Преимущества**:
- Независимость микросервисов
- Нет блокировок БД между сервисами
- Гибкость при изменении схемы channels

**Недостатки**:
- Нет каскадного удаления
- Нужна ручная проверка целостности

## 6. Тестирование модели

### 6.1 Unit тесты

**test_post_model.py**:
```python
import pytest
from src.Containers.AppSection.TgPost.Models.Post import Post
from datetime import datetime

@pytest.mark.asyncio
async def test_post_creation():
    """Test creating a post."""
    post = Post(
        id=123,
        content="Test post",
        repost_count=10,
        view_count=100,
        id_channels=456
    )
    
    await post.save()
    
    # Проверить сохранение
    saved_post = await Post.objects().get(Post.id == 123)
    assert saved_post.content == "Test post"
    assert saved_post.repost_count == 10
    assert saved_post.view_count == 100

@pytest.mark.asyncio
async def test_post_upsert():
    """Test ON CONFLICT UPDATE behavior."""
    # Первая вставка
    await Post(id=123, content="Original", view_count=100).save()
    
    # Обновление через upsert
    await Post.insert(
        Post(id=123, content="Updated", view_count=200)
    ).on_conflict(
        action="DO UPDATE",
        target=Post.id,
        values=[Post.content, Post.view_count]
    )
    
    # Проверить обновление
    updated = await Post.objects().get(Post.id == 123)
    assert updated.content == "Updated"
    assert updated.view_count == 200

@pytest.mark.asyncio
async def test_post_jsonb_link():
    """Test JSONB link field."""
    post = Post(
        id=123,
        content="Test",
        link={
            "url": "https://example.com",
            "type": "external",
            "title": "Example"
        }
    )
    
    await post.save()
    
    saved = await Post.objects().get(Post.id == 123)
    assert saved.link["url"] == "https://example.com"
    assert saved.link["type"] == "external"
```

### 6.2 Integration тесты

**test_batch_upsert.py**:
```python
@pytest.mark.asyncio
async def test_batch_upsert_posts():
    """Test batch upsert with multiple posts."""
    posts = [
        Post(id=i, content=f"Post {i}", id_channels=100)
        for i in range(1, 101)
    ]
    
    await Post.insert(*posts).on_conflict(
        action="DO UPDATE",
        target=Post.id,
        values=[Post.content, Post.id_channels]
    )
    
    # Проверить количество
    count = await Post.count()
    assert count == 100
    
    # Проверить данные
    first_post = await Post.objects().get(Post.id == 1)
    assert first_post.content == "Post 1"
    assert first_post.id_channels == 100
```

## 7. Резюме

### Ключевые решения:
1. ✅ **Piccolo Table** с JSONB для гибких структур (link)
2. ✅ **ON CONFLICT UPDATE** для идемпотентности
3. ✅ **Индексы** на id_channels и message_timestamp для производительности
4. ✅ **Null values** для всех полей кроме id (частичные обновления)
5. ✅ **Soft reference** на id_channels (независимость микросервисов)
6. ✅ **Default values** для счетчиков (0 для int, False для bool)

### Производительность:
- Batch upsert: 100-1000 постов за операцию
- Index lookups: O(log n) для channel/timestamp queries
- JSONB storage: Эффективное сжатие в PostgreSQL

### Следующие шаги:
1. ✅ Создать миграцию для posts таблицы
2. → Создать quickstart.md с тестовыми сценариями
3. → Запустить /tasks для генерации задач реализации

---
**Data Model Design завершен**: 2025-11-02  
**Готово к реализации**: Models и миграции спроектированы


