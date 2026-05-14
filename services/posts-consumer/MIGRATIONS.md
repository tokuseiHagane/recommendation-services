# 📋 Piccolo Migrations Guide

Руководство по работе с Piccolo миграциями в TgPost сервисе.

## 🎯 Автоматическое применение миграций

**TgPost сервис автоматически применяет миграции при старте через Docker!**

### Как это работает

1. **docker-entrypoint.sh** запускается перед стартом приложения
2. Скрипт ждет готовности PostgreSQL
3. Проверяет статус миграций: `piccolo migrations check TgPost`
4. Если есть неприменённые миграции → применяет их: `piccolo migrations forwards TgPost`
5. Запускает приложение: `python -m src.Bootstrap`

```bash
🚀 Starting TgPost service entrypoint...
⏳ Waiting for PostgreSQL to be ready...
✅ PostgreSQL is ready!
📋 Checking Piccolo migrations...
⚙️  Applying Piccolo migrations...
✅ Migrations applied successfully!
✨ Setup complete! Starting application...
```

### Преимущества

- ✅ **Zero-configuration** - не нужно вручную применять миграции
- ✅ **Идемпотентность** - безопасно перезапускать контейнер
- ✅ **Автоматизация** - миграции всегда синхронизированы с кодом
- ✅ **Проверка БД** - автоматическое ожидание готовности PostgreSQL

## 📦 Структура миграций

```
src/Containers/AppSection/TgPost/
├── Models/
│   ├── __init__.py
│   └── Post.py                    # Piccolo Table definition
├── migrations/
│   ├── __init__.py
│   └── 2025-11-02T13-00-00-000000.py  # Migration file
└── PiccoloApp.py                  # Piccolo app config
```

## 🛠️ Работа с миграциями

### Проверить статус миграций

```bash
# Внутри контейнера
docker-compose exec tgpost piccolo migrations check TgPost

# Локально (если установлен Piccolo)
piccolo migrations check TgPost
```

**Вывод**:
```
✅ All migrations have been run
```

### Применить миграции вручную

Обычно **не требуется** (применяются автоматически), но если нужно:

```bash
# Внутри контейнера
docker-compose exec tgpost piccolo migrations forwards TgPost

# С автоподтверждением
docker-compose exec tgpost piccolo migrations forwards TgPost --auto_agree

# Локально
piccolo migrations forwards TgPost
```

### Создать новую миграцию

#### Автоматически (рекомендуется)

```bash
# Внутри контейнера
docker-compose exec tgpost piccolo migrations new TgPost --auto

# Локально
piccolo migrations new TgPost --auto
```

Piccolo автоматически обнаружит изменения в моделях и создаст миграцию.

#### Вручную

Создайте файл в `src/Containers/AppSection/TgPost/migrations/`:

```python
# 2025-11-03T10-00-00-000000.py

from piccolo.apps.migrations.auto.migration_manager import MigrationManager

ID = "2025-11-03T10:00:00:000000"
VERSION = "1.22.0"
DESCRIPTION = "Add new column to posts"

async def forwards():
    manager = MigrationManager(
        migration_id=ID,
        app_name="TgPost",
        description=DESCRIPTION
    )
    
    # Добавить колонку
    manager.add_column(
        table_class_name="Post",
        tablename="posts",
        column_name="new_field",
        db_column_name="new_field",
        column_class_name="Text",
        column_class="Text",
        params={"null": True},
        schema=None
    )
    
    return manager

async def backwards():
    manager = MigrationManager(
        migration_id=ID,
        app_name="TgPost",
        description=DESCRIPTION
    )
    
    # Удалить колонку
    manager.drop_column(
        table_class_name="Post",
        tablename="posts",
        column_name="new_field",
        db_column_name="new_field",
        schema=None
    )
    
    return manager
```

### Откатить миграцию

```bash
# Откатить последнюю миграцию
docker-compose exec tgpost piccolo migrations backwards TgPost

# Откатить до конкретной миграции
docker-compose exec tgpost piccolo migrations backwards TgPost --migration_id=2025-11-02T13:00:00:000000
```

⚠️ **Внимание**: Откат миграций может привести к потере данных!

### Список всех миграций

```bash
docker-compose exec tgpost piccolo migrations list TgPost
```

## 🔍 Как работает Post Model

### Определение модели

```python
# src/Containers/AppSection/TgPost/Models/Post.py

from piccolo.table import Table
from piccolo.columns import Integer, Text, JSONB, Timestamp, Boolean

class Post(Table, tablename="posts"):
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

### Миграция создает

1. **Таблицу posts** со всеми колонками
2. **Индекс** `idx_posts_id_channels` для быстрого поиска по каналам
3. **Индекс** `idx_posts_timestamp` для временных запросов

### SQL эквивалент

```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    content TEXT,
    repost_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    link JSONB,
    message_timestamp TIMESTAMP,
    has_reactions BOOLEAN DEFAULT FALSE,
    id_channels INTEGER,
    free_reactions_count INTEGER DEFAULT 0,
    paid_reactions_count INTEGER DEFAULT 0
);

CREATE INDEX idx_posts_id_channels ON posts(id_channels);
CREATE INDEX idx_posts_timestamp ON posts(message_timestamp);
```

## 🧪 Тестирование миграций

### Проверить миграцию локально

```bash
# 1. Создать тестовую БД
createdb tgpost_test

# 2. Применить миграции
DB_NAME=tgpost_test piccolo migrations forwards TgPost

# 3. Проверить таблицы
psql tgpost_test -c "\dt"
psql tgpost_test -c "\d posts"

# 4. Удалить тестовую БД
dropdb tgpost_test
```

### Проверить откат миграции

```bash
# Применить
piccolo migrations forwards TgPost

# Откатить
piccolo migrations backwards TgPost

# Применить снова
piccolo migrations forwards TgPost
```

## 🐛 Troubleshooting

### Проблема: Миграции не применяются автоматически

**Симптомы**: Таблица posts не существует

**Решение**:
```bash
# Проверить логи entrypoint
docker-compose logs tgpost | grep -A 10 "Starting TgPost service"

# Применить вручную
docker-compose exec tgpost piccolo migrations forwards TgPost

# Проверить подключение к БД
docker-compose exec tgpost python -c "
from src.Ship.utils.db import get_db_engine
import asyncio
asyncio.run(get_db_engine().execute_query('SELECT 1'))
print('DB OK')
"
```

### Проблема: Миграция зависла

**Решение**:
```bash
# Остановить контейнер
docker-compose stop tgpost

# Проверить статус миграций напрямую в БД
docker-compose exec postgres psql -U app_user -d app_db -c "SELECT * FROM piccolo_migrations;"

# Удалить последнюю запись если нужно (ОСТОРОЖНО!)
docker-compose exec postgres psql -U app_user -d app_db -c "DELETE FROM piccolo_migrations WHERE migration_id='2025-11-02T13:00:00:000000';"

# Перезапустить
docker-compose up tgpost
```

### Проблема: Конфликт миграций

**Симптомы**: Ошибка "migration already exists"

**Решение**:
```bash
# Проверить список миграций
docker-compose exec tgpost piccolo migrations list TgPost

# Переименовать файл миграции с новым ID
# migrations/2025-11-03T10-00-00-000000.py (новое время)

# Обновить ID внутри файла
```

### Проблема: Таблица уже существует

**Симптомы**: "relation posts already exists"

**Решение**:
```bash
# Отметить миграцию как выполненную без применения
docker-compose exec postgres psql -U app_user -d app_db -c "
INSERT INTO piccolo_migrations (app_name, migration_id) 
VALUES ('TgPost', '2025-11-02T13:00:00:000000')
ON CONFLICT DO NOTHING;
"
```

## 📚 Полезные команды

```bash
# Все миграции приложения TgPost
piccolo migrations list TgPost

# Статус миграций
piccolo migrations check TgPost

# Применить все
piccolo migrations forwards TgPost --auto_agree

# Откатить одну
piccolo migrations backwards TgPost

# Создать новую (auto)
piccolo migrations new TgPost --auto

# SQL Preview (не применяет, только показывает)
piccolo migrations forwards TgPost --preview
```

## 🔗 Ссылки

- [Piccolo Migrations Docs](https://piccolo-orm.readthedocs.io/en/latest/piccolo/migrations.html)
- [Piccolo ORM Docs](https://piccolo-orm.readthedocs.io/)
- [TgPost Data Model](specs/001-dynamic-kafka-consumers-sharded-processing/data-model.md)

---

**Создано**: 2025-11-02  
**Обновлено**: 2025-11-02  
**Автоматические миграции**: ✅ Включены

