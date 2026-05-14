# ✅ Инструкция по проверке настройки

Быстрая проверка что автоматическое создание таблиц через Piccolo работает.

## 🧪 Тест 1: Первый запуск (чистая установка)

### Шаг 1: Очистить всё

```bash
# Остановить и удалить всё (включая volumes)
docker-compose down -v
```

### Шаг 2: Запустить заново

```bash
# Запустить сервисы
docker-compose up -d
```

### Шаг 3: Проверить логи

```bash
# Смотрим логи TgPost
docker-compose logs tgpost | grep -A 20 "entrypoint"
```

**Ожидаемый вывод**:
```
🚀 Starting TgPost service entrypoint...
================================================
  TgPost Service - Piccolo Auto-Migration
================================================

⏳ Waiting for PostgreSQL to be ready...
✅ PostgreSQL is ready!
📋 Checking Piccolo migrations...
⚙️  Applying Piccolo migrations...
✅ Migrations applied successfully!

✨ Setup complete! Starting application...
================================================
```

### Шаг 4: Проверить таблицу

```bash
# Подключиться к БД и проверить таблицу posts
docker-compose exec postgres psql -U app_user -d app_db -c "\d posts"
```

**Ожидаемый вывод** (структура таблицы):
```
                        Table "public.posts"
         Column          |            Type             | Nullable | Default
-------------------------+-----------------------------+----------+---------
 id                      | integer                     | not null |
 content                 | text                        |          |
 repost_count            | integer                     |          | 0
 view_count              | integer                     |          | 0
 link                    | jsonb                       |          |
 message_timestamp       | timestamp without time zone |          |
 has_reactions           | boolean                     |          | false
 id_channels             | integer                     |          |
 free_reactions_count    | integer                     |          | 0
 paid_reactions_count    | integer                     |          | 0
Indexes:
    "posts_pkey" PRIMARY KEY, btree (id)
    "idx_posts_id_channels" btree (id_channels)
    "idx_posts_timestamp" btree (message_timestamp)
```

### Шаг 5: Проверить миграции

```bash
# Проверить статус миграций
docker-compose exec tgpost piccolo migrations check TgPost
```

**Ожидаемый вывод**:
```
✅ All migrations have been run
```

### Шаг 6: Проверить таблицу миграций

```bash
# Посмотреть записи в piccolo_migrations
docker-compose exec postgres psql -U app_user -d app_db -c "SELECT * FROM piccolo_migrations;"
```

**Ожидаемый вывод**:
```
 id | app_name |         migration_id         |         created_at
----+----------+------------------------------+----------------------------
  1 | TgPost   | 2025-11-02T13:00:00:000000  | 2025-11-02 13:00:00.123456
```

## ✅ Тест 2: Идемпотентность (повторный запуск)

### Шаг 1: Перезапустить контейнер

```bash
docker-compose restart tgpost
```

### Шаг 2: Проверить логи

```bash
docker-compose logs tgpost | tail -20
```

**Ожидаемый вывод**:
```
📋 Checking Piccolo migrations...
✅ All migrations are up to date
✨ Setup complete! Starting application...
```

**Обратите внимание**: Миграции **НЕ применяются** повторно, т.к. уже применены.

## ✅ Тест 3: Вставка данных

### Вставить тестовые данные

```bash
docker-compose exec postgres psql -U app_user -d app_db -c "
INSERT INTO posts (id, content, view_count, id_channels) 
VALUES 
  (1, 'Test post 1', 100, 123),
  (2, 'Test post 2', 200, 123),
  (3, 'Test post 3', 300, 456);
"
```

### Проверить вставку

```bash
docker-compose exec postgres psql -U app_user -d app_db -c "
SELECT id, content, view_count, id_channels FROM posts;
"
```

**Ожидаемый вывод**:
```
 id |   content    | view_count | id_channels
----+--------------+------------+-------------
  1 | Test post 1  |        100 |         123
  2 | Test post 2  |        200 |         123
  3 | Test post 3  |        300 |         456
```

### Тест ON CONFLICT UPDATE

```bash
docker-compose exec postgres psql -U app_user -d app_db -c "
INSERT INTO posts (id, content, view_count) 
VALUES (1, 'Updated post 1', 999)
ON CONFLICT (id) DO UPDATE 
SET content = EXCLUDED.content, view_count = EXCLUDED.view_count;
"
```

### Проверить обновление

```bash
docker-compose exec postgres psql -U app_user -d app_db -c "
SELECT id, content, view_count FROM posts WHERE id = 1;
"
```

**Ожидаемый вывод**:
```
 id |     content      | view_count
----+------------------+------------
  1 | Updated post 1   |        999
```

## ✅ Тест 4: Makefile команды

```bash
# Проверить все make команды
make help

# Должен показать список команд
```

Попробовать основные:

```bash
make ps              # Статус контейнеров
make logs-tgpost     # Логи TgPost
make db-shell        # PostgreSQL shell
make migrate-check   # Статус миграций
```

## 🎯 Чеклист успешной настройки

- [ ] Docker контейнеры запускаются без ошибок
- [ ] В логах видно "✅ Migrations applied successfully!"
- [ ] Таблица `posts` существует с правильной структурой
- [ ] Индексы `idx_posts_id_channels` и `idx_posts_timestamp` созданы
- [ ] Таблица `piccolo_migrations` содержит запись о миграции
- [ ] Повторный запуск не применяет миграции заново
- [ ] Вставка данных работает
- [ ] ON CONFLICT UPDATE работает
- [ ] Make команды работают

## 🐛 Если что-то не работает

### Логи показывают ошибку

```bash
# Полные логи TgPost
docker-compose logs tgpost

# Логи PostgreSQL
docker-compose logs postgres

# Ошибки entrypoint
docker-compose logs tgpost | grep -i error
```

### Таблица не создалась

```bash
# Применить миграции вручную
docker-compose exec tgpost piccolo migrations forwards TgPost

# Проверить подключение к БД
docker-compose exec tgpost python -c "
from src.Ship.utils.db import get_db_engine
import asyncio
asyncio.run(get_db_engine().execute_query('SELECT 1'))
print('DB OK')
"
```

### PostgreSQL не готов

```bash
# Проверить health check
docker-compose exec postgres pg_isready -U app_user -d app_db

# Должно быть: accepting connections
```

## 📊 Результаты

Если все тесты прошли успешно:

✅ **Автоматическое создание таблиц через Piccolo работает!**

Вы можете:
- Запускать `docker-compose up` без дополнительных команд
- Таблицы создаются автоматически при первом запуске
- Повторные запуски безопасны (идемпотентны)
- Миграции отслеживаются в БД

## 🔄 Очистка после тестов

```bash
# Удалить тестовые данные
docker-compose exec postgres psql -U app_user -d app_db -c "TRUNCATE TABLE posts;"

# Или полностью пересоздать
docker-compose down -v
docker-compose up -d
```

---

**Инструкция по проверке** | TgPost Service | 2025-11-02  
**Статус**: Готово к тестированию ✅

