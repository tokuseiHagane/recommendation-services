# Tasks: Динамические Kafka консьюмеры - Implementation Roadmap

**Дата**: 2025-11-02  
**Фаза**: Phase 2 - Task Generation  
**Общее количество задач**: 49  
**Оценка времени**: ~34 часа

## Обзор

Этот документ содержит детальный список всех задач для реализации TgPost контейнера в порядке их выполнения согласно Porto архитектуре.

**Порядок реализации**:
```
Setup → Models → Services → Tasks → Actions → Workers → Integration → Testing → Migration
```

**Стратегия**:
- ✅ TDD подход: тест → реализация → проверка
- ✅ Порядок: Models → Tasks → Actions → Workers
- ✅ Параллельно: тесты создаются вместе с реализацией
- ✅ Интеграция: в конце после всех компонентов

---

## Phase 1: Setup (5 задач, ~2 часа)

### TASK-001: Создать структуру директорий TgPost контейнера
**Приоритет**: P0  
**Зависимости**: Нет  
**Оценка**: 15 минут

**Описание**:
Создать полную структуру директорий для AppSection.TgPost контейнера

**Чеклист**:
- [ ] Создать `src/Containers/AppSection/TgPost/`
- [ ] Создать поддиректории: `Actions/`, `Tasks/`, `Models/`, `Services/`, `UI/Workers/`, `UI/CLI/`, `Data/`, `Exceptions/`, `Config/`, `migrations/`, `Tests/`
- [ ] Создать все `__init__.py` файлы
- [ ] Проверить структуру командой `tree src/Containers/AppSection/TgPost/`

**Критерии приемки**:
- Структура соответствует porto-structure.md
- Все директории созданы
- `__init__.py` файлы на месте

---

### TASK-002: Создать PiccoloApp.py для TgPost
**Приоритет**: P0  
**Зависимости**: TASK-001  
**Оценка**: 15 минут

**Описание**:
Создать конфигурацию Piccolo app для TgPost контейнера

**Чеклист**:
- [ ] Создать `src/Containers/AppSection/TgPost/PiccoloApp.py`
- [ ] Настроить `APP_CONFIG` с правильными путями
- [ ] Указать `table_classes` для автопоиска моделей
- [ ] Указать путь к миграциям

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

**Критерии приемки**:
- PiccoloApp.py создан
- Конфигурация валидна
- Можно импортировать `from src.Containers.AppSection.TgPost.PiccoloApp import APP_CONFIG`

---

### TASK-003: Зарегистрировать TgPost app в piccolo_conf.py
**Приоритет**: P0  
**Зависимости**: TASK-002  
**Оценка**: 10 минут

**Описание**:
Добавить TgPost app в глобальную конфигурацию Piccolo

**Чеклист**:
- [ ] Открыть `piccolo_conf.py` в корне проекта
- [ ] Добавить `"src.Containers.AppSection.TgPost.PiccoloApp"` в `APP_REGISTRY.apps`
- [ ] Проверить командой `piccolo app list`

**Критерии приемки**:
- TgPost отображается в списке apps
- Команда `piccolo app list` работает без ошибок

---

### TASK-004: Создать Config/container_settings.py
**Приоритет**: P0  
**Зависимости**: TASK-001  
**Оценка**: 20 минут

**Описание**:
Создать конфигурацию контейнера TgPost

**Чеклист**:
- [ ] Создать `Config/container_settings.py`
- [ ] Определить `TgPostContainerSettings` dataclass
- [ ] Добавить все настройки: Kafka, batch processing, cache, consumer
- [ ] Создать singleton instance `container_settings`

**Файл**: Смотреть porto-structure.md раздел 8.1

**Критерии приемки**:
- container_settings.py создан
- Все настройки определены
- Можно импортировать `from src.Containers.AppSection.TgPost.Config.container_settings import container_settings`

---

### TASK-005: Создать базовые Exceptions
**Приоритет**: P0  
**Зависимости**: TASK-001  
**Оценка**: 30 минут

**Описание**:
Создать все кастомные исключения для TgPost контейнера

**Чеклист**:
- [ ] Создать `Exceptions/BatchUpsertException.py`
- [ ] Создать `Exceptions/ConsumerCreationException.py`
- [ ] Создать `Exceptions/CacheValidationException.py`
- [ ] Создать `Exceptions/__init__.py` с exports

**Файлы**: Смотреть porto-structure.md раздел 7

**Критерии приемки**:
- Все 3 исключения созданы
- Можно импортировать из `Exceptions/__init__.py`

---

## Phase 2: Models & Data (3 задачи, ~2 часа)

### TASK-006: Создать Post Model (Piccolo ORM)
**Приоритет**: P0  
**Зависимости**: TASK-002  
**Оценка**: 45 минут

**Описание**:
Реализовать Piccolo Table для Post модели согласно data-model.md

**Чеклист**:
- [ ] Создать `Models/Post.py`
- [ ] Определить все колонки согласно SQL схеме (id, content, repost_count, view_count, link, message_timestamp, has_reactions, id_channels, free_reactions_count, paid_reactions_count)
- [ ] Добавить docstrings и help_text
- [ ] Создать `Models/__init__.py` с export

**Файл**: Смотреть data-model.md раздел 1.1

**Критерии приемки**:
- Post модель создана
- Все поля определены правильно
- Можно импортировать `from src.Containers.AppSection.TgPost.Models.Post import Post`
- `piccolo table list` показывает Post

---

### TASK-007: Создать миграцию для Post таблицы
**Приоритет**: P0  
**Зависимости**: TASK-006  
**Оценка**: 30 минут

**Описание**:
Сгенерировать и настроить миграцию для создания posts таблицы с индексами

**Чеклист**:
- [ ] Запустить `piccolo migrations new TgPost --auto`
- [ ] Проверить сгенерированную миграцию
- [ ] Добавить CREATE INDEX для idx_posts_id_channels
- [ ] Добавить CREATE INDEX для idx_posts_timestamp
- [ ] Добавить backwards() с DROP INDEX

**Команда**:
```bash
piccolo migrations new TgPost --auto
```

**Файл**: Смотреть data-model.md раздел 2.1

**Критерии приемки**:
- Миграция создана в `migrations/`
- Миграция содержит все колонки и индексы
- `piccolo migrations check TgPost` показывает миграцию
- `piccolo migrations forwards TgPost` работает без ошибок

---

### TASK-008: Создать Pydantic DTOs
**Приоритет**: P1  
**Зависимости**: TASK-006  
**Оценка**: 30 минут

**Описание**:
Создать Pydantic схемы для валидации данных

**Чеклист**:
- [ ] Создать `Data/PostDTO.py` с валидацией
- [ ] Создать `Data/ChannelDTO.py` с валидацией
- [ ] Добавить field validators где нужно
- [ ] Создать `Data/__init__.py` с exports

**Файлы**: Смотреть porto-structure.md раздел 6

**Критерии приемки**:
- PostDTO и ChannelDTO созданы
- Валидация работает
- Можно импортировать оба DTO

---

## Phase 3: Services (4 задачи, ~4 часа)

### TASK-009: Реализовать PostObjectsCache service
**Приоритет**: P0  
**Зависимости**: TASK-001  
**Оценка**: 1 час

**Описание**:
Реализовать in-memory кэш для каналов с TTL

**Чеклист**:
- [ ] Создать `Services/PostObjectsCache.py`
- [ ] Реализовать `__init__` с TTL
- [ ] Реализовать `put_channels()`
- [ ] Реализовать `get_channel()`
- [ ] Реализовать `has_channel()`
- [ ] Реализовать `get_all_channels()`
- [ ] Реализовать `clear()`
- [ ] Реализовать `_is_expired()`
- [ ] Добавить docstrings

**Файл**: Адаптировать из `../Telegram-Channel-Consumer/.../channel_objects_cache.py`
Смотреть porto-structure.md раздел 4.1

**Критерии приемки**:
- PostObjectsCache реализован
- Все методы работают
- TTL логика корректна

---

### TASK-010: Написать тесты для PostObjectsCache
**Приоритет**: P0  
**Зависимости**: TASK-009  
**Оценка**: 45 минут

**Описание**:
Создать полный набор тестов для PostObjectsCache

**Чеклист**:
- [ ] Создать `Tests/test_post_objects_cache.py`
- [ ] Тест: `test_cache_put_and_get`
- [ ] Тест: `test_cache_has_channel`
- [ ] Тест: `test_cache_get_all`
- [ ] Тест: `test_cache_clear`
- [ ] Тест: `test_cache_ttl_expiration`
- [ ] Запустить тесты `pytest Tests/test_post_objects_cache.py -v`

**Файл**: Смотреть quickstart.md раздел 3.1

**Критерии приемки**:
- Все тесты проходят
- Coverage > 90%

---

### TASK-011: Реализовать DynamicConsumerManager service
**Приоритет**: P0  
**Зависимости**: TASK-009  
**Оценка**: 1.5 часа

**Описание**:
Реализовать менеджер для управления множественными Kafka консьюмерами

**Чеклист**:
- [ ] Создать `Services/DynamicConsumerManager.py`
- [ ] Реализовать `__init__` с инициализацией
- [ ] Реализовать `add_consumer()` с thread-safety (asyncio.Lock)
- [ ] Реализовать `remove_consumer()` с graceful stop
- [ ] Реализовать `get_consumer()`
- [ ] Реализовать `get_all_consumers()`
- [ ] Реализовать `get_all_consumer_ids()`
- [ ] Реализовать `shutdown_all()`
- [ ] Реализовать `get_stats()`
- [ ] Добавить Logfire метрики
- [ ] Создать `Services/__init__.py` с exports

**Файл**: Смотреть porto-structure.md раздел 4.2

**Критерии приемки**:
- DynamicConsumerManager реализован
- Thread-safety обеспечен через asyncio.Lock
- Все методы работают
- Logfire метрики добавлены

---

### TASK-012: Написать тесты для DynamicConsumerManager
**Приоритет**: P0  
**Зависимости**: TASK-011  
**Оценка**: 45 минут

**Описание**:
Создать полный набор тестов для DynamicConsumerManager

**Чеклист**:
- [ ] Создать `Tests/test_dynamic_consumer_manager.py`
- [ ] Тест: `test_manager_add_consumer`
- [ ] Тест: `test_manager_add_duplicate_consumer`
- [ ] Тест: `test_manager_get_consumer`
- [ ] Тест: `test_manager_remove_consumer`
- [ ] Тест: `test_manager_shutdown_all`
- [ ] Запустить тесты `pytest Tests/test_dynamic_consumer_manager.py -v`

**Файл**: Смотреть quickstart.md раздел 3.2

**Критерии приемки**:
- Все тесты проходят
- Coverage > 90%

---

## Phase 4: Tasks Implementation (16 задач, ~8 часов)

### TASK-013: Реализовать BatchUpsertPostsTask
**Приоритет**: P0  
**Зависимости**: TASK-006, TASK-005  
**Оценка**: 30 минут

**Описание**:
Реализовать atomic task для batch upsert постов с ON CONFLICT UPDATE

**Чеклист**:
- [ ] Создать `Tasks/BatchUpsertPostsTask.py`
- [ ] Реализовать дедупликацию по id
- [ ] Реализовать создание Post instances
- [ ] Реализовать `Post.insert().on_conflict()`
- [ ] Добавить error handling с BatchUpsertException
- [ ] Добавить logging

**Файл**: Смотреть porto-structure.md раздел 2.3

**Критерии приемки**:
- Task реализован
- ON CONFLICT UPDATE работает
- Дедупликация работает

---

### TASK-014: Написать тесты для BatchUpsertPostsTask
**Приоритет**: P0  
**Зависимости**: TASK-013  
**Оценка**: 30 минут

**Описание**:
Unit тесты для BatchUpsertPostsTask

**Чеклист**:
- [ ] Создать `Tests/test_batch_upsert_posts_task.py`
- [ ] Тест: `test_batch_upsert_posts_success`
- [ ] Тест: `test_batch_upsert_posts_idempotency`
- [ ] Тест: `test_batch_upsert_posts_deduplication`
- [ ] Тест: `test_batch_upsert_posts_empty_list`
- [ ] Запустить тесты

**Файл**: Смотреть quickstart.md раздел 1.1

**Критерии приемки**:
- Все тесты проходят
- Coverage > 90%

---

### TASK-015: Реализовать ValidatePostsTask
**Приоритет**: P0  
**Зависимости**: TASK-008  
**Оценка**: 20 минут

**Описание**:
Реализовать валидацию постов через Pydantic

**Чеклист**:
- [ ] Создать `Tasks/ValidatePostsTask.py`
- [ ] Реализовать валидацию через PostDTO
- [ ] Реализовать пропуск невалидных с logging warning
- [ ] Добавить logging

**Файл**: Смотреть porto-structure.md раздел 2.4

**Критерии приемки**:
- Task реализован
- Валидация работает
- Невалидные посты пропускаются

---

### TASK-016: Написать тесты для ValidatePostsTask
**Приоритет**: P0  
**Зависимости**: TASK-015  
**Оценка**: 20 минут

**Описание**:
Unit тесты для ValidatePostsTask

**Чеклист**:
- [ ] Создать `Tests/test_validate_posts_task.py`
- [ ] Тест: `test_validate_posts_success`
- [ ] Тест: `test_validate_posts_skip_invalid`
- [ ] Тест: `test_validate_posts_empty_list`

**Файл**: Смотреть quickstart.md раздел 1.2

**Критерии приемки**:
- Все тесты проходят
- Coverage > 90%

---

### TASK-017: Реализовать UpdateCacheTask
**Приоритет**: P1  
**Зависимости**: TASK-009  
**Оценка**: 15 минут

**Описание**:
Task для обновления PostObjectsCache

**Чеклист**:
- [ ] Создать `Tasks/UpdateCacheTask.py`
- [ ] Реализовать вызов `cache.put_channels()`
- [ ] Добавить logging

**Файл**: Смотреть porto-structure.md раздел 2.5

---

### TASK-018: Реализовать CheckDuplicateTask
**Приоритет**: P1  
**Зависимости**: TASK-009  
**Оценка**: 15 минут

**Описание**:
Task для проверки дубликатов в кэше

**Чеклист**:
- [ ] Создать `Tasks/CheckDuplicateTask.py`
- [ ] Реализовать вызов `cache.has_channel()`
- [ ] Добавить logging

**Файл**: Смотреть porto-structure.md раздел 2.6

---

### TASK-019: Написать тесты для CheckDuplicateTask
**Приоритет**: P1  
**Зависимости**: TASK-018  
**Оценка**: 15 минут

**Файл**: Смотреть quickstart.md раздел 1.3

---

### TASK-020: Реализовать ConsumePostsBatchTask
**Приоритет**: P0  
**Зависимости**: TASK-004  
**Оценка**: 30 минут

**Описание**:
Task для чтения батча из Kafka через getmany

**Чеклист**:
- [ ] Создать `Tasks/ConsumePostsBatchTask.py`
- [ ] Реализовать `consumer.getmany()`
- [ ] Реализовать парсинг JSON
- [ ] Реализовать ограничение batch_size
- [ ] Добавить error handling для невалидного JSON
- [ ] Добавить logging

**Файл**: Смотреть porto-structure.md раздел 2.7

---

### TASK-021: Написать тесты для ConsumePostsBatchTask
**Приоритет**: P0  
**Зависимости**: TASK-020  
**Оценка**: 30 минут

**Описание**:
Unit тесты с моками AIOKafkaConsumer

**Чеклист**:
- [ ] Создать `Tests/test_consume_posts_batch_task.py`
- [ ] Тест: `test_consume_posts_batch_success`
- [ ] Тест: `test_consume_posts_batch_empty`
- [ ] Тест: `test_consume_posts_batch_size_limit`

**Файл**: Смотреть quickstart.md раздел 1.4

---

### TASK-022: Реализовать CreateKafkaConsumerTask
**Приоритет**: P0  
**Зависимости**: TASK-004, TASK-005  
**Оценка**: 30 минут

**Описание**:
Task для создания AIOKafkaConsumer

**Чеклист**:
- [ ] Создать `Tasks/CreateKafkaConsumerTask.py`
- [ ] Реализовать создание AIOKafkaConsumer с правильной конфигурацией
- [ ] Реализовать `await consumer.start()`
- [ ] Добавить error handling с ConsumerCreationException
- [ ] Добавить logging

**Файл**: Смотреть porto-structure.md раздел 2.2

---

### TASK-023: Реализовать RegisterConsumerTask
**Приоритет**: P1  
**Зависимости**: TASK-011  
**Оценка**: 15 минут

**Описание**:
Task для регистрации консьюмера в DynamicConsumerManager

**Чеклист**:
- [ ] Создать `Tasks/RegisterConsumerTask.py`
- [ ] Реализовать вызов `manager.add_consumer()`
- [ ] Добавить logging

**Файл**: Смотреть porto-structure.md раздел 2.8

---

### TASK-024: Реализовать LoadChannelsFromDBTask
**Приоритет**: P1  
**Зависимости**: TASK-006  
**Оценка**: 30 минут

**Описание**:
Task для загрузки каналов из БД

**Чеклист**:
- [ ] Создать `Tasks/LoadChannelsFromDBTask.py`
- [ ] Определить источник данных (локальная таблица или shared DB)
- [ ] Реализовать SELECT запрос
- [ ] Добавить error handling
- [ ] Добавить logging

**Файл**: Смотреть porto-structure.md раздел 2.1

**Примечание**: Требует решения о том, откуда брать данные о каналах (локальная таблица или доступ к БД Telegram-Channel-Consumer)

---

### TASK-025: Реализовать ValidateChannelDataTask
**Приоритет**: P1  
**Зависимости**: TASK-008, TASK-005  
**Оценка**: 20 минут

**Описание**:
Task для валидации данных канала через Pydantic

**Чеклист**:
- [ ] Создать `Tasks/ValidateChannelDataTask.py`
- [ ] Реализовать валидацию через ChannelDTO
- [ ] Добавить error handling с CacheValidationException

**Файл**: Смотреть porto-structure.md раздел 2.9

---

### TASK-026: Создать Tasks/__init__.py с exports
**Приоритет**: P2  
**Зависимости**: TASK-013 до TASK-025  
**Оценка**: 10 минут

**Описание**:
Создать __init__.py для удобного импорта всех Tasks

---

## Phase 5: Actions Implementation (8 задач, ~6 часов)

### TASK-027: Реализовать BatchProcessPostsAction
**Приоритет**: P0  
**Зависимости**: TASK-015, TASK-013  
**Оценка**: 45 минут

**Описание**:
Action для оркестрации обработки батча постов

**Чеклист**:
- [ ] Создать `Actions/BatchProcessPostsAction.py`
- [ ] Реализовать вызов ValidatePostsTask
- [ ] Реализовать вызов BatchUpsertPostsTask
- [ ] Добавить Logfire трассировку
- [ ] Добавить error handling

**Файл**: Смотреть porto-structure.md раздел 1.3

**Критерии приемки**:
- Action реализован
- Оркестрация Tasks работает
- Logfire трассировка добавлена

---

### TASK-028: Написать integration тесты для BatchProcessPostsAction
**Приоритет**: P0  
**Зависимости**: TASK-027  
**Оценка**: 30 минут

**Чеклист**:
- [ ] Создать `Tests/test_batch_process_posts_action.py`
- [ ] Тест: `test_batch_process_posts_success`
- [ ] Тест: `test_batch_process_posts_with_invalid`
- [ ] Тест: `test_batch_process_posts_empty`

**Файл**: Смотреть quickstart.md раздел 2.1

---

### TASK-029: Реализовать CreateDynamicConsumerAction
**Приоритет**: P0  
**Зависимости**: TASK-018, TASK-017, TASK-022, TASK-023  
**Оценка**: 1 час

**Описание**:
Action для реактивного создания нового консьюмера

**Чеклист**:
- [ ] Создать `Actions/CreateDynamicConsumerAction.py`
- [ ] Реализовать workflow: CheckDuplicateTask → UpdateCacheTask → CreateKafkaConsumerTask → RegisterConsumerTask
- [ ] Добавить Logfire трассировку
- [ ] Добавить error handling

**Файл**: Смотреть porto-structure.md раздел 1.2

---

### TASK-030: Написать integration тесты для CreateDynamicConsumerAction
**Приоритет**: P0  
**Зависимости**: TASK-029  
**Оценка**: 30 минут

**Чеклист**:
- [ ] Создать `Tests/test_create_dynamic_consumer_action.py`
- [ ] Тест: `test_create_dynamic_consumer_new_channel`
- [ ] Тест: `test_create_dynamic_consumer_duplicate`

**Файл**: Смотреть quickstart.md раздел 2.2

---

### TASK-031: Реализовать InitializeConsumersAction
**Приоритет**: P0  
**Зависимости**: TASK-024, TASK-017, TASK-022, TASK-023  
**Оценка**: 1 час

**Описание**:
Action для инициализации всех консьюмеров при старте

**Чеклист**:
- [ ] Создать `Actions/InitializeConsumersAction.py`
- [ ] Реализовать workflow: LoadChannelsFromDBTask → UpdateCacheTask → (для каждого канала) CreateKafkaConsumerTask + RegisterConsumerTask
- [ ] Добавить Logfire трассировку
- [ ] Добавить error handling

**Файл**: Смотреть porto-structure.md раздел 1.1

---

### TASK-032: Написать integration тесты для InitializeConsumersAction
**Приоритет**: P0  
**Зависимости**: TASK-031  
**Оценка**: 30 минут

**Чеклист**:
- [ ] Создать `Tests/test_initialize_consumers_action.py`
- [ ] Тест: `test_initialize_consumers_success` с моками

**Файл**: Смотреть quickstart.md раздел 2.3

---

### TASK-033: Реализовать UpdateChannelCacheAction
**Приоритет**: P1  
**Зависимости**: TASK-025, TASK-017  
**Оценка**: 30 минут

**Описание**:
Action для обновления кэша при получении событий

**Чеклист**:
- [ ] Создать `Actions/UpdateChannelCacheAction.py`
- [ ] Реализовать workflow: ValidateChannelDataTask → UpdateCacheTask
- [ ] Добавить Logfire трассировку

**Файл**: Смотреть porto-structure.md раздел 1.4

---

### TASK-034: Создать Actions/__init__.py с exports
**Приоритет**: P2  
**Зависимости**: TASK-027 до TASK-033  
**Оценка**: 10 минут

---

## Phase 6: Workers Implementation (6 задач, ~6 часов)

### TASK-035: Реализовать ConsumerWorker
**Приоритет**: P0  
**Зависимости**: TASK-020, TASK-027, TASK-011  
**Оценка**: 2 часа

**Описание**:
Worker для обработки постов из топика tg_posts_{id}

**Чеклист**:
- [ ] Создать `UI/Workers/ConsumerWorker.py`
- [ ] Реализовать `__init__` с параметрами
- [ ] Реализовать `start()` с основным loop
- [ ] Реализовать вызов ConsumePostsBatchTask
- [ ] Реализовать вызов BatchProcessPostsAction
- [ ] Реализовать manual commit после обработки
- [ ] Реализовать `stop()` для graceful shutdown
- [ ] Добавить error handling и retry логику
- [ ] Добавить logging

**Файл**: Смотреть porto-structure.md раздел 5.1

**Критерии приемки**:
- ConsumerWorker реализован
- Loop работает
- Manual commit работает
- Graceful shutdown работает

---

### TASK-036: Написать тесты для ConsumerWorker
**Приоритет**: P0  
**Зависимости**: TASK-035  
**Оценка**: 1 час

**Чеклист**:
- [ ] Создать `Tests/test_consumer_worker.py`
- [ ] Тест: `test_consumer_worker_full_workflow` с моками

**Файл**: Смотреть quickstart.md раздел 4.1

---

### TASK-037: Реализовать ChannelsDiffWorker
**Приоритет**: P0  
**Зависимости**: TASK-029, TASK-011  
**Оценка**: 2 часа

**Описание**:
Worker для прослушивания tg_channels_diff и создания консьюмеров

**Чеклист**:
- [ ] Создать `UI/Workers/ChannelsDiffWorker.py`
- [ ] Реализовать `__init__` с параметрами
- [ ] Реализовать создание consumer для tg_channels_diff
- [ ] Реализовать `start()` с основным loop
- [ ] Реализовать парсинг событий о каналах
- [ ] Реализовать вызов CreateDynamicConsumerAction
- [ ] Реализовать создание и запуск ConsumerWorker для нового канала
- [ ] Реализовать `stop()` для graceful shutdown
- [ ] Добавить error handling
- [ ] Добавить logging

**Файл**: Смотреть porto-structure.md раздел 5.2

**Критерии приемки**:
- ChannelsDiffWorker реализован
- Прослушивание tg_channels_diff работает
- Динамическое создание консьюмеров работает

---

### TASK-038: Написать тесты для ChannelsDiffWorker
**Приоритет**: P0  
**Зависимости**: TASK-037  
**Оценка**: 45 минут

**Чеклист**:
- [ ] Создать `Tests/test_channels_diff_worker.py`
- [ ] Тест E2E workflow с моками

---

### TASK-039: Создать InitConsumersCommand (CLI) (опционально)
**Приоритет**: P2  
**Зависимости**: TASK-031  
**Оценка**: 30 минут

**Описание**:
CLI команда для ручного запуска инициализации

**Чеклист**:
- [ ] Создать `UI/CLI/InitConsumersCommand.py`
- [ ] Реализовать вызов InitializeConsumersAction
- [ ] Добавить аргументы командной строки

---

### TASK-040: Создать UI/__init__.py
**Приоритет**: P2  
**Зависимости**: TASK-035, TASK-037  
**Оценка**: 5 минут

---

## Phase 7: Integration & DI (4 задачи, ~3 часа)

### TASK-041: Создать Dishka Providers для TgPost
**Приоритет**: P0  
**Зависимости**: TASK-009, TASK-011, TASK-027, TASK-029  
**Оценка**: 1.5 часа

**Описание**:
Настроить DI providers для всех компонентов TgPost

**Чеклист**:
- [ ] Создать `Providers.py`
- [ ] Добавить provider для PostObjectsCache (APP scope)
- [ ] Добавить provider для DynamicConsumerManager (APP scope)
- [ ] Добавить providers для всех Actions (REQUEST scope)
- [ ] Настроить dependency injection между компонентами
- [ ] Проверить корректность графа зависимостей

**Файл**: Смотреть porto-structure.md раздел 9.1

**Критерии приемки**:
- Providers.py создан
- Все компоненты зарегистрированы
- DI работает

---

### TASK-042: Обновить Ship/Providers.py (если нужно)
**Приоритет**: P1  
**Зависимости**: TASK-041  
**Оценка**: 30 минут

**Описание**:
Добавить глобальные providers в Ship если нужно

**Чеклист**:
- [ ] Проверить Ship/Providers.py
- [ ] Добавить providers для Kafka components если нужно
- [ ] Зарегистрировать TgPostProvider

---

### TASK-043: Создать Bootstrap.py для TgPost service
**Приоритет**: P0  
**Зависимости**: TASK-041, TASK-035, TASK-037  
**Оценка**: 1 час

**Описание**:
Создать entry point для запуска всего сервиса

**Чеклист**:
- [ ] Создать/обновить `src/Bootstrap.py`
- [ ] Реализовать `bootstrap_tg_post_service()`
- [ ] Настроить Dishka container
- [ ] Запустить InitializeConsumersAction
- [ ] Запустить ChannelsDiffWorker
- [ ] Запустить ConsumerWorkers для существующих каналов
- [ ] Настроить graceful shutdown

**Файл**: Смотреть research.md раздел 7.2

**Критерии приемки**:
- Bootstrap.py создан
- Сервис запускается
- Все workers стартуют
- Graceful shutdown работает

---

### TASK-044: Интегрировать Logfire трассировку
**Приоритет**: P1  
**Зависимости**: TASK-027, TASK-029, TASK-031  
**Оценка**: 30 минут

**Описание**:
Добавить Logfire spans и metrics во все Actions и критические точки

**Чеклист**:
- [ ] Проверить все Actions имеют logfire.span()
- [ ] Добавить метрики в DynamicConsumerManager
- [ ] Добавить метрики в Workers
- [ ] Проверить логи работают

**Критерии приемки**:
- Logfire трассировка работает
- Метрики собираются
- Spans видны в Logfire dashboard

---

## Phase 8: Testing & Documentation (3 задачи, ~3 часа)

### TASK-045: Запустить все unit и integration тесты
**Приоритет**: P0  
**Зависимости**: Все предыдущие тесты  
**Оценка**: 1 час

**Описание**:
Запустить полный test suite и исправить failing тесты

**Чеклист**:
- [ ] Запустить `pytest src/Containers/AppSection/TgPost/Tests/ -v`
- [ ] Исправить все failing тесты
- [ ] Запустить `pytest --cov=src/Containers/AppSection/TgPost --cov-report=html`
- [ ] Проверить coverage > 80%
- [ ] Исправить проблемы с coverage если нужно

**Критерии приемки**:
- Все тесты проходят
- Coverage > 80%

---

### TASK-046: Создать conftest.py для TgPost тестов
**Приоритет**: P1  
**Зависимости**: TASK-007  
**Оценка**: 30 минут

**Описание**:
Настроить pytest fixtures для тестов

**Чеклист**:
- [ ] Создать `Tests/conftest.py`
- [ ] Добавить fixture `setup_test_db`
- [ ] Добавить fixture `cleanup_posts`
- [ ] Проверить fixtures работают

**Файл**: Смотреть quickstart.md раздел Setup

---

### TASK-047: Обновить документацию проекта
**Приоритет**: P1  
**Зависимости**: TASK-043  
**Оценка**: 1.5 часа

**Описание**:
Обновить README и создать документацию для TgPost

**Чеклист**:
- [ ] Обновить главный README.md с информацией о TgPost
- [ ] Обновить architecture.md с новой структурой
- [ ] Обновить docker-compose.yml для TgPost сервиса
- [ ] Создать GETTING_STARTED.md для TgPost
- [ ] Добавить примеры использования

**Критерии приемки**:
- Документация обновлена
- Инструкции понятны
- Docker compose конфигурация работает

---

## Phase 9: Migration & Cleanup (3 задачи, ~2 часа)

### TASK-048: Удалить устаревший контейнер message/
**Приоритет**: P2  
**Зависимости**: TASK-045  
**Оценка**: 30 минут

**Описание**:
Удалить старый message контейнер после проверки TgPost работает

**Чеклист**:
- [ ] Проверить TgPost полностью работает
- [ ] Удалить `src/Containers/message/` директорию
- [ ] Обновить импорты если есть ссылки
- [ ] Обновить конфигурацию

**Критерии приемки**:
- Старый контейнер удален
- Проект работает без ошибок

---

### TASK-049: Финальное тестирование E2E
**Приоритет**: P0  
**Зависимости**: TASK-043, TASK-045  
**Оценка**: 1 час

**Описание**:
Провести полное E2E тестирование с реальным Kafka

**Чеклист**:
- [ ] Запустить Kafka через docker-compose
- [ ] Запустить TgPost сервис
- [ ] Отправить тестовые сообщения в tg_channels_diff
- [ ] Проверить создание консьюмеров
- [ ] Отправить тестовые посты в tg_posts_{id}
- [ ] Проверить сохранение в БД
- [ ] Проверить Logfire метрики
- [ ] Проверить graceful shutdown

**Критерии приемки**:
- E2E workflow работает
- Все компоненты интегрированы
- Метрики собираются

---

## Резюме

### Статистика задач:
- **Setup**: 5 задач (~2 часа)
- **Models & Data**: 3 задачи (~2 часа)
- **Services**: 4 задачи (~4 часа)
- **Tasks**: 16 задач (~8 часов)
- **Actions**: 8 задач (~6 часов)
- **Workers**: 6 задач (~6 часов)
- **Integration**: 4 задачи (~3 часа)
- **Testing**: 3 задачи (~3 часа)
- **Migration**: 2 задачи (~1.5 часа)

**Итого**: 49 задач, ~34 часа работы

### Критический путь:
```
TASK-001 (Setup) →
TASK-006 (Post Model) → TASK-007 (Migration) →
TASK-009 (PostObjectsCache) → TASK-011 (DynamicConsumerManager) →
TASK-013 (BatchUpsertPostsTask) → TASK-015 (ValidatePostsTask) →
TASK-027 (BatchProcessPostsAction) →
TASK-035 (ConsumerWorker) → TASK-037 (ChannelsDiffWorker) →
TASK-041 (Providers) → TASK-043 (Bootstrap) →
TASK-045 (Testing) → TASK-049 (E2E)
```

### Порядок выполнения:
1. **День 1-2**: Setup + Models + Services (Tasks 1-12)
2. **День 3-4**: Tasks implementation (Tasks 13-26)
3. **День 5-6**: Actions implementation (Tasks 27-34)
4. **День 7-8**: Workers + Integration (Tasks 35-44)
5. **День 9**: Testing + Documentation + E2E (Tasks 45-49)

### Следующие шаги:
1. ✅ Все артефакты Phase 0 и Phase 1 созданы
2. ✅ Детальный список задач (tasks.md) создан
3. → Начать реализацию с TASK-001

---

**Tasks Generation завершена**: 2025-11-02  
**Готово к реализации**: 49 задач спланировано
**Estimated completion**: ~5-9 рабочих дней


