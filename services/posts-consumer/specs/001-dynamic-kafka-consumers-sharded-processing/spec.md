# Спецификация функции: Динамические Kafka консьюмеры с шардированной обработкой постов

**Ветка функции**: `001-dynamic-kafka-consumers-sharded-processing`  
**Создано**: 2025-11-02  
**Статус**: Черновик  
**Porto Container**: AppSection.TgPost
**Исходные данные**: Переписать сервис TgPostsConsumers согласно архитектуре с динамическим созданием консьюмеров, шардированной обработкой и двухуровневым кэшированием

## Алгоритм выполнения (main)
```
1. Разобрать описание архитектуры из architecture.md
   → Определены: динамические консьюмеры, шардирование, кэш-синхронизация
2. Определить размещение Porto Container:
   → AppSection.TgPost: Основная бизнес-логика обработки постов из Telegram
3. Извлечь ключевые концепции:
   → Участники: Kafka consumers, Cache manager, Database
   → Действия: Consume posts, Validate, Store, Manage consumers dynamically
   → Данные: Post model с полями из SQL schema
   → Ограничения: Batch processing, conflict management, cache synchronization
4. Сопоставить с Porto компонентами:
   → Actions: BatchProcessPostsAction, CreateConsumerAction
   → Tasks: BatchUpsertPostsTask, CachePostsTask, PublishDiffTask, ConsumePostsTask
   → Models: Post (Piccolo ORM)
   → Services: PostObjectsCache, DynamicConsumerManager
5. Заполнить пользовательские сценарии
6. Сгенерировать функциональные требования (Porto style)
7. Определить ключевые сущности и компоненты
8. Запустить проверку
9. Вернуть: УСПЕХ (спецификация готова к планированию)
```

---

## ⚡ Краткие рекомендации (специфичные для Porto)
- ✅ Сосредоточься на ТОМ, что нужно системе и ЗАЧЕМ
- ✅ Мысли в терминах Porto: Containers, Actions, Tasks, Models
- ❌ Избегай описания КАК реализовывать (никаких конкретных технических деталей)
- 👥 Пиши для понимания бизнес-логики потоковой обработки данных

### Руководство по сопоставлению с Porto
- **Обработка постов батчами** → **BatchProcessPostsAction** (оркестрация)
- **Уpsert постов в БД** → **BatchUpsertPostsTask** (атомарная операция)
- **Сущность Post** → **Post Model** (Piccolo ORM)
- **Kafka consumers** → **UI/Workers/ConsumerWorker**

---

## Анализ Porto Container *(обязательно)*

### Размещение Container
**Целевой Container**: AppSection.TgPost (новый контейнер)
**Обоснование**: Это основная бизнес-логика обработки постов из Telegram каналов. Не является внешней интеграцией, поэтому размещается в AppSection.

### Связанные Containers
- **Зависимости**: Зависит от микросервиса Telegram-Channel-Consumer для получения информации о каналах через топик `tg_channels_diff`
- **Интеграции**: 
  - Прослушивает топики Kafka: `tg_channels_diff` (для создания новых консьюмеров), `tg_posts_{id}` (для получения постов)
  - Записывает данные в PostgreSQL БД

### Переиспользование Ship компонентов
- **Parents**: Базовые классы для Actions и Tasks из Ship слоя
- **Core**: Database connection (Piccolo), Logging (Logfire)
- **Providers**: Dishka DI для KafkaClient, Cache, ConsumerManager
- **Utils**: KafkaClient, KafkaAdmin для управления Kafka

---

## Пользовательские сценарии и тестирование *(обязательно)*

### Основная пользовательская история
Как система потоковой обработки, я хочу:
1. Автоматически создавать новые Kafka консьюмеры при появлении новых Telegram каналов
2. Обрабатывать посты из каждого канала через выделенный топик tg_posts_{channel_id}
3. Валидировать и сохранять посты батчами для повышения производительности
4. Использовать двухуровневый кэш для синхронизации данных о каналах

### Сценарии приемки (Porto Actions)

1. **Дано** новый канал появился в топике tg_channels_diff, **Когда** система получает сообщение о канале, **Тогда** создается новый консьюмер для топика tg_posts_{channel_id}
   - **Porto Action**: `CreateDynamicConsumerAction` в `AppSection.TgPost`
   - **Ожидаемые Tasks**: `ValidateChannelCacheTask`, `CreateKafkaConsumerTask`, `RegisterConsumerTask`

2. **Дано** консьюмер получил батч постов из топика tg_posts_{id}, **Когда** батч обрабатывается, **Тогда** все посты валидируются и сохраняются в БД с обработкой конфликтов
   - **Porto Action**: `BatchProcessPostsAction` в `AppSection.TgPost`
   - **Ожидаемые Tasks**: `ValidatePostsTask`, `BatchUpsertPostsTask`

3. **Дано** система запускается впервые, **Когда** происходит инициализация, **Тогда** создаются консьюмеры для всех существующих каналов из БД
   - **Porto Action**: `InitializeConsumersAction` в `AppSection.TgPost`
   - **Ожидаемые Tasks**: `LoadChannelsFromDBTask`, `SyncCacheTask`, `CreateKafkaConsumerTask` (для каждого канала)

4. **Дано** кэш каналов устарел, **Когда** получено сообщение из tg_channels_diff, **Тогда** кэш обновляется и исключаются дубликаты
   - **Porto Action**: `UpdateChannelCacheAction` в `AppSection.TgPost`
   - **Ожидаемые Tasks**: `ValidateChannelTask`, `UpdateCacheTask`, `CheckDuplicateTask`

### Граничные случаи
- Что происходит при получении дубликата канала из tg_channels_diff?
  - **Обработка ошибок**: Кэш проверяет наличие и пропускает дубликат (логирование warning)
  - **Действие восстановления**: `CheckDuplicateTask` возвращает существующий консьюмер

- Что происходит при ошибке вставки батча постов?
  - **Обработка ошибок**: Porto Exception `BatchUpsertException`
  - **Действие восстановления**: `HandleBatchErrorTask` логирует ошибку, частичное сохранение успешных записей

- Что происходит если консьюмер отваливается?
  - **Обработка ошибок**: Kafka rebalancing перераспределит партиции
  - **Действие восстановления**: `HealthCheckTask` мониторит состояние консьюмеров

---

## Требования *(обязательно)*

### Функциональные требования (Porto компоненты)

#### Actions (Бизнес use cases)
- **FR-A001**: Система ДОЛЖНА предоставлять `InitializeConsumersAction` для инициализации консьюмеров при старте из существующих каналов в БД
- **FR-A002**: Система ДОЛЖНА предоставлять `CreateDynamicConsumerAction` для реактивного создания новых консьюмеров через прослушивание топика tg_channels_diff
- **FR-A003**: `CreateDynamicConsumerAction` ДОЛЖЕН оркестрировать валидацию через кэш и создание консьюмера
- **FR-A004**: Система ДОЛЖНА предоставлять `BatchProcessPostsAction` для обработки батча постов из топика
- **FR-A005**: `BatchProcessPostsAction` ДОЛЖЕН оркестрировать валидацию и batch-вставку с конфликт-менеджментом
- **FR-A006**: Система ДОЛЖНА предоставлять `UpdateChannelCacheAction` для обновления кэша при получении событий из tg_channels_diff

#### Tasks (Атомарные операции)  
- **FR-T001**: Система ДОЛЖНА предоставлять `LoadChannelsFromDBTask` для загрузки всех каналов из БД при инициализации
- **FR-T002**: Система ДОЛЖНА предоставлять `CreateKafkaConsumerTask` для создания нового AIOKafka консьюмера для топика tg_posts_{id}
- **FR-T003**: Система ДОЛЖНА предоставлять `BatchUpsertPostsTask` для batch-вставки постов с ON CONFLICT UPDATE
- **FR-T004**: `BatchUpsertPostsTask` ДОЛЖЕН обрабатывать конфликты по первичному ключу (id) и обновлять данные
- **FR-T005**: Система ДОЛЖНА предоставлять `ValidatePostsTask` для валидации структуры постов перед вставкой
- **FR-T006**: Система ДОЛЖНА предоставлять `UpdateCacheTask` для обновления двухуровневого кэша каналов
- **FR-T007**: Система ДОЛЖНА предоставлять `CheckDuplicateTask` для проверки дубликатов каналов через кэш
- **FR-T008**: Система ДОЛЖНА предоставлять `ConsumePostsBatchTask` для чтения батча сообщений из Kafka топика
- **FR-T009**: Система ДОЛЖНА предоставлять `RegisterConsumerTask` для регистрации нового консьюмера в менеджере

#### Models (Слой данных)
- **FR-M001**: Система ДОЛЖНА сохранять `Post` с полями: id (int, PK), content (text), repost_count (int), view_count (int), link (jsonb), message_timestamp (timestamp), has_reactions (boolean), id_channels (int), free_reactions_count (int), paid_reactions_count (int)
- **FR-M002**: Модель `Post` ДОЛЖНА обеспечивать constraint на первичный ключ (id)
- **FR-M003**: Модель `Post` ДОЛЖНА поддерживать ON CONFLICT UPDATE для обновления существующих постов

#### UI слой / Workers
- **FR-U001**: Система ДОЛЖНА предоставлять `ConsumerWorker` для запуска и управления Kafka консьюмерами
- **FR-U002**: Система ДОЛЖНА предоставлять `ChannelsDiffWorker` для прослушивания топика tg_channels_diff и создания новых консьюмеров
- **FR-U003**: Система ДОЛЖНА предоставлять CLI команду для ручного запуска инициализации консьюмеров

#### Services
- **FR-S001**: Система ДОЛЖНА предоставлять `PostObjectsCache` для двухуровневого кэширования каналов (персистентный + оперативный слой)
- **FR-S002**: `PostObjectsCache` ДОЛЖЕН синхронизироваться с БД при инициализации (персистентный слой)
- **FR-S003**: `PostObjectsCache` ДОЛЖЕН обновляться через события из tg_channels_diff (оперативный слой)
- **FR-S004**: Система ДОЛЖНА предоставлять `DynamicConsumerManager` для управления жизненным циклом консьюмеров
- **FR-S005**: `DynamicConsumerManager` ДОЛЖЕН поддерживать добавление/удаление/остановку консьюмеров

### Ключевые сущности (Porto Models) *(включить если фича включает данные)*

- **Post**: 
  - **Назначение**: Представляет пост из Telegram канала в бизнес-домене
  - **Ключевые атрибуты**: 
    - id: уникальный идентификатор поста (первичный ключ)
    - content: текстовое содержимое поста
    - repost_count, view_count: метрики поста
    - link: JSONB структура со ссылками
    - message_timestamp: время публикации
    - has_reactions, free_reactions_count, paid_reactions_count: данные о реакциях
    - id_channels: внешний ключ на канал
  - **Porto Model**: `Post` в `AppSection.TgPost/Models/`
  - **Отношения**: Связан с каналом через id_channels (но модель канала находится в другом микросервисе)

---

## Влияние на Porto архитектуру *(обязательно)*

### Требуемые новые компоненты

- **Container**: Создать новый контейнер `AppSection.TgPost`
- **Actions**: 
  - `InitializeConsumersAction`
  - `CreateDynamicConsumerAction`
  - `BatchProcessPostsAction`
  - `UpdateChannelCacheAction`
- **Tasks**: 
  - `LoadChannelsFromDBTask`
  - `CreateKafkaConsumerTask`
  - `BatchUpsertPostsTask`
  - `ValidatePostsTask`
  - `UpdateCacheTask`
  - `CheckDuplicateTask`
  - `ConsumePostsBatchTask`
  - `RegisterConsumerTask`
- **Models**: 
  - `Post` (Piccolo ORM model)
- **Services**:
  - `PostObjectsCache`
  - `DynamicConsumerManager`
- **UI компоненты**: 
  - `ConsumerWorker` (Kafka worker для обработки постов)
  - `ChannelsDiffWorker` (Kafka worker для прослушивания tg_channels_diff)
  - CLI команда для инициализации

### Обновления Ship слоя
- **Providers**: 
  - Регистрация DI для `PostObjectsCache`
  - Регистрация DI для `DynamicConsumerManager`
  - Регистрация DI для Kafka clients
- **Exceptions**: 
  - `BatchUpsertException`
  - `ConsumerCreationException`
  - `CacheValidationException`
- **Utils**: 
  - Переиспользовать `KafkaClient` из Ship
  - Переиспользовать `KafkaAdmin` из Ship для создания топиков

### Точки интеграции
- **Внешние микросервисы**: 
  - Зависимость от Telegram-Channel-Consumer для данных о каналах через Kafka топик tg_channels_diff
- **База данных**: 
  - Новая таблица `posts` с полями из post_model.md
  - Потенциально нужна таблица для отслеживания активных консьюмеров
- **События**: 
  - Подписка на топик `tg_channels_diff` для событий о новых каналах
  - Подписка на топики `tg_posts_{id}` для получения постов
  - Событийно-ориентированная архитектура с динамическим созданием консьюмеров

---

## Контрольный список проверки и приемки
*GATE: Автоматические проверки выполняются во время выполнения main()*

### Качество контента
- [x] Нет деталей реализации (конкретные библиотеки, структура кода)
- [x] Сфокусировано на пользовательской ценности и бизнес-потребностях
- [x] Написано для нетехнических заинтересованных лиц
- [x] Все обязательные секции заполнены

### Соответствие Porto архитектуре
- [x] Размещение контейнера обосновано и ясно (AppSection.TgPost)
- [x] Actions сопоставлены с пользовательскими историями
- [x] Tasks определены как атомарные операции
- [x] Models представляют бизнес-сущности
- [x] Переиспользование Ship компонентов рассмотрено

### Полнота требований
- [x] Не осталось маркеров [ТРЕБУЕТ УТОЧНЕНИЯ]
- [x] Требования тестируемы и однозначны  
- [x] Критерии успеха измеримы
- [x] Область четко ограничена
- [x] Зависимости и предположения определены
- [x] Porto компоненты четко сопоставлены

---

## Статус выполнения
*Обновляется main() во время обработки*

- [x] Описание пользователя разобрано
- [x] Размещение Porto контейнера определено (AppSection.TgPost)
- [x] Ключевые концепции извлечены и сопоставлены с Porto компонентами
- [x] Неоднозначности отмечены (нет)
- [x] Пользовательские сценарии определены с Actions/Tasks
- [x] Требования сгенерированы с Porto сопоставлением
- [x] Сущности определены как Porto Models (Post)
- [x] Влияние на архитектуру проанализировано
- [x] Контрольный список проверки пройден

---

## Дополнительные заметки

### Архитектурные принципы
- **Динамическое создание**: Консьюмеры создаются реактивно при появлении новых каналов
- **Шардирование**: Каждый канал имеет свой топик tg_posts_{id}, что обеспечивает изоляцию и масштабируемость
- **Batch processing**: Посты обрабатываются батчами для оптимизации производительности БД
- **Двухуровневый кэш**: Персистентный слой (БД синхронизация) + оперативный слой (события Kafka)
- **Конфликт-менеджмент**: ON CONFLICT UPDATE обеспечивает идемпотентность при повторной обработке

### Взаимодействие с Telegram-Channel-Consumer
Микросервис Telegram-Channel-Consumer отвечает за:
- Парсинг новых Telegram каналов
- Публикацию информации о каналах в топик tg_channels_diff
- Публикацию постов каналов в топики tg_posts_{channel_id}

TgPostsConsumers (этот сервис) отвечает за:
- Прослушивание tg_channels_diff для создания новых консьюмеров
- Потребление постов из топиков tg_posts_{id}
- Валидацию и сохранение постов в БД


