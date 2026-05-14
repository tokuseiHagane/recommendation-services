# План реализации: Динамические Kafka консьюмеры с шардированной обработкой (Porto)

**Ветка**: `001-dynamic-kafka-consumers-sharded-processing` | **Дата**: 2025-11-02 | **Спецификация**: [spec.md](spec.md)
**Porto Container**: AppSection.TgPost
**Исходные данные**: Спецификация функции из `/specs/001-dynamic-kafka-consumers-sharded-processing/spec.md`

## Алгоритм выполнения (область команды /plan)
```
1. Загрузить спецификацию функции из исходного пути
   → Найдено: spec.md успешно проанализирована
2. Проанализировать требования Porto Container
   → Извлечены: 4 Actions, 9 Tasks, 1 Model, 2 Workers, 2 Services
   → Определено: AppSection.TgPost (новый контейнер)
3. Заполнить технический контекст стеком Porto
   → AIOKafka для Kafka, Piccolo для ORM, Dishka для DI, Logfire для наблюдаемости
4. Оценить раздел проверки Porto Constitution
   → Проверено: Соответствует принципам Porto
   → Проверено: Переиспользование Ship компонентов (KafkaClient, Database utils)
5. Выполнить Фазу 0 → research.md (исследование aiokafka, динамическое создание консьюмеров)
6. Выполнить Фазу 1 → contracts, data-model.md, quickstart.md, porto-structure.md
7. Спланировать Фазу 2 → Генерация задач для Porto компонентов
8. СТОП - Готов к команде /tasks
```

## Резюме
Система динамических Kafka консьюмеров для обработки постов из Telegram каналов с шардированной архитектурой. 

**Основное требование**: 
- Реактивное создание Kafka консьюмеров при появлении новых каналов через топик tg_channels_diff
- Обработка постов из шардированных топиков tg_posts_{id} с batch-вставками
- Двухуровневое кэширование для синхронизации данных о каналах

**Porto Container**: AppSection.TgPost (новый контейнер)

**Ключевые компоненты**:
- **Actions**: InitializeConsumersAction, CreateDynamicConsumerAction, BatchProcessPostsAction, UpdateChannelCacheAction
- **Tasks**: LoadChannelsFromDBTask, CreateKafkaConsumerTask, BatchUpsertPostsTask, ValidatePostsTask, UpdateCacheTask, CheckDuplicateTask, ConsumePostsBatchTask, RegisterConsumerTask
- **Models**: Post (Piccolo ORM)
- **Services**: PostObjectsCache, DynamicConsumerManager
- **Workers**: ConsumerWorker, ChannelsDiffWorker

## Технический контекст (технологический стек Porto)
**Framework**: Litestar 2.12+ (ASGI веб-фреймворк)
**ORM**: Piccolo 1.22+ с PostgreSQL (продакшн)
**DI Container**: Dishka 1.4+ (внедрение зависимостей)
**Наблюдаемость**: Logfire 2.7+ (логирование, трассировка, мониторинг)
**Тестирование**: pytest + pytest-asyncio (асинхронное тестирование)
**Валидация**: Pydantic 2.9+ (валидация и сериализация данных)
**Kafka**: AIOKafka 0.11+ (асинхронный клиент Kafka)

**Porto структура**:
- **Путь Container**: `src/Containers/AppSection/TgPost/`
- **Ship компоненты**: `src/Ship/` (Parents, config, tasks, utils)
- **DI регистрация**: Dishka провайдеры в TgPost/Providers.py и Ship/Providers.py
- **База данных**: Piccolo модели с миграциями в TgPost/migrations/
- **Workers**: Kafka workers в TgPost/UI/Workers/

**Цели производительности**: 
- Batch processing: 100-1000 постов за batch
- Latency: < 1 секунда от получения сообщения до записи в БД
- Throughput: обработка 10,000+ постов/минуту на консьюмер

**Масштаб/Область**: 
- Динамическое создание неограниченного количества консьюмеров
- Каждый консьюмер привязан к одному топику tg_posts_{id}
- Поддержка горизонтального масштабирования через Kafka consumer groups

## Проверка Porto Constitution
*GATE: Должна пройти перед Phase 0 исследованием*

**Архитектура Container**:
- ✅ Размещение контейнера обосновано? Да, AppSection.TgPost - основная бизнес-логика обработки постов
- ✅ Единая ответственность на Container? Да, только обработка постов из Telegram
- ✅ Четкие границы между Containers? Да, не пересекается с существующим message контейнером
- ✅ Зависимости текут правильно? Да, TgPost → Ship → Framework

**Дизайн компонентов**:
- ✅ Actions оркестрируют несколько Tasks? Да, например BatchProcessPostsAction → ValidatePostsTask + BatchUpsertPostsTask
- ✅ Tasks атомарны и переиспользуемы? Да, каждый Task выполняет одну операцию
- ✅ Models представляют бизнес-сущности? Да, Post представляет пост из Telegram
- ✅ UI разделен по типу интерфейса? Да, Workers для Kafka consumers

**Переиспользование Ship**:
- ✅ Используются существующие Ship Parents? Да, базовые классы из Ship/Parents (если есть)
- ✅ Используется Ship Core? Да, Ship/utils/db.py, Ship/utils/kafka_client.py, Ship/config/
- ✅ Dishka провайдеры правильно организованы? Да, локальные в TgPost/Providers.py, глобальные в Ship/Providers.py
- ✅ Обработка исключений следует Porto паттернам? Да, кастомные исключения в TgPost/Exceptions/

**Принципы Porto**:
- ✅ Бизнес-логика в Containers, инфраструктура в Ship? Да
- ✅ Четкое разделение ответственностей поддерживается? Да
- ✅ Изоляция фреймворка через Ship слой? Да, Kafka clients в Ship/utils
- ✅ Dependency injection используется повсюду? Да, через Dishka

## Структура проекта (Porto)

### Документация (эта функция)
```
specs/001-dynamic-kafka-consumers-sharded-processing/
├── spec.md              # Спецификация (уже создана)
├── plan.md              # Этот файл (вывод команды /plan)
├── research.md          # Вывод Фазы 0 (будет создан)
├── data-model.md        # Вывод Фазы 1 (будет создан)
├── porto-structure.md   # Вывод Фазы 1 (будет создан)
├── quickstart.md        # Вывод Фазы 1 (будет создан)
└── tasks.md             # Вывод Фазы 2 (команда /tasks - НЕ создается /plan)
```

### Исходный код (структура Porto)
```
src/
├── Containers/
│   └── AppSection/            # Секция основной бизнес-логики
│       └── TgPost/            # Контейнер обработки постов (НОВЫЙ)
│           ├── Actions/       # Бизнес use cases
│           │   ├── __init__.py
│           │   ├── InitializeConsumersAction.py
│           │   ├── CreateDynamicConsumerAction.py
│           │   ├── BatchProcessPostsAction.py
│           │   └── UpdateChannelCacheAction.py
│           ├── Tasks/         # Атомарные операции
│           │   ├── __init__.py
│           │   ├── LoadChannelsFromDBTask.py
│           │   ├── CreateKafkaConsumerTask.py
│           │   ├── BatchUpsertPostsTask.py
│           │   ├── ValidatePostsTask.py
│           │   ├── UpdateCacheTask.py
│           │   ├── CheckDuplicateTask.py
│           │   ├── ConsumePostsBatchTask.py
│           │   └── RegisterConsumerTask.py
│           ├── Models/        # Модели Piccolo ORM
│           │   ├── __init__.py
│           │   └── Post.py
│           ├── UI/            # Пользовательские интерфейсы
│           │   ├── Workers/   # Kafka workers
│           │   │   ├── __init__.py
│           │   │   ├── ConsumerWorker.py
│           │   │   └── ChannelsDiffWorker.py
│           │   └── CLI/       # CLI команды (опционально)
│           │       ├── __init__.py
│           │       └── InitConsumersCommand.py
│           ├── Services/      # Сервисы контейнера
│           │   ├── __init__.py
│           │   ├── PostObjectsCache.py
│           │   └── DynamicConsumerManager.py
│           ├── Data/          # DTOs и схемы
│           │   ├── __init__.py
│           │   ├── PostDTO.py
│           │   └── ConsumerConfigDTO.py
│           ├── Exceptions/    # Исключения контейнера
│           │   ├── __init__.py
│           │   ├── BatchUpsertException.py
│           │   ├── ConsumerCreationException.py
│           │   └── CacheValidationException.py
│           ├── Config/        # Конфигурация контейнера
│           │   ├── __init__.py
│           │   └── container_settings.py
│           ├── migrations/    # Миграции Piccolo
│           │   └── 2025-11-02T00-00-00-000000.py
│           ├── Tests/         # Тесты контейнера
│           │   ├── __init__.py
│           │   ├── test_actions.py
│           │   ├── test_tasks.py
│           │   ├── test_models.py
│           │   ├── test_services.py
│           │   └── test_integration.py
│           ├── PiccoloApp.py  # Конфигурация приложения Piccolo
│           ├── Providers.py   # Провайдеры Dishka
│           └── __init__.py
└── Ship/                      # Инфраструктурный слой (переиспользуемый)
    ├── config/
    │   ├── kafka_config.py    # (уже существует)
    │   └── settings.py        # (уже существует)
    ├── utils/
    │   ├── kafka_client.py    # (уже существует)
    │   ├── kafka_admin.py     # (может потребоваться создание)
    │   └── db.py              # (уже существует)
    ├── tasks/                 # (существующие базовые workers)
    ├── Providers.py           # Глобальные DI провайдеры
    └── ...                    # Другие Ship компоненты
```

## Фаза 0: Исследование и анализ Porto
*Результаты будут записаны в research.md*

1. **Анализ существующей структуры Porto**:
   - ✅ Существующий контейнер: `message` (устаревший, будет заменен на TgPost)
   - ✅ Ship компоненты для переиспользования:
     - `Ship/config/kafka_config.py` - конфигурация Kafka
     - `Ship/utils/kafka_client.py` - клиент Kafka
     - `Ship/utils/db.py` - утилиты БД
     - `Ship/config/settings.py` - глобальные настройки
   - ✅ Похожий паттерн в соседнем проекте: Telegram-Channel-Consumer с контейнером tg_channel

2. **Исследование Porto-специфичных реализаций**:
   - **Piccolo ORM для Post модели**:
     - Использовать Piccolo.Integer для id (PK)
     - Использовать Piccolo.Text для content
     - Использовать Piccolo.JSONB для link
     - Использовать Piccolo.Timestamp для message_timestamp
     - Паттерн: INSERT ON CONFLICT UPDATE для идемпотентности
   
   - **AIOKafka для динамических консьюмеров**:
     - Исследовать паттерн: создание множественных AIOKafkaConsumer в одном процессе
     - Исследовать: getmany() для batch consumption
     - Исследовать: enable_auto_commit=False с ручным commit после batch insert
     - Исследовать: isolation_level="read_committed" для transactional consistency
   
   - **Dishka для DI**:
     - Паттерн Provider для PostObjectsCache (Singleton scope)
     - Паттерн Provider для DynamicConsumerManager (Singleton scope)
     - Паттерн Provider для Kafka clients (Request scope)
   
   - **Logfire для наблюдаемости**:
     - Трассировка Actions и Tasks
     - Логирование batch metrics (размер батча, время обработки)
     - Мониторинг состояния консьюмеров

3. **Исследование взаимодействий Container**:
   - **Зависимость от Telegram-Channel-Consumer**:
     - Через Kafka топик tg_channels_diff (событийно-ориентированная интеграция)
     - Не требует прямых вызовов между микросервисами
   
   - **Ship сервисы**:
     - KafkaClient для создания consumers/producers
     - Database utils для Piccolo операций
     - Logging utils для Logfire integration
   
   - **Новые Ship компоненты**:
     - Возможно нужен KafkaAdmin для создания топиков динамически (если еще нет)
     - Возможно нужен базовый Worker parent class

**Результат**: research.md с Porto-специфичными техническими решениями

## Phase 1: Porto Design & Contracts
*Prerequisites: research.md complete*

1. **Спроектировать компоненты Porto** → `porto-structure.md`:
   
   **Actions** (Бизнес use cases):
   - `InitializeConsumersAction`: Загрузить каналы из БД, синхронизировать кэш, создать консьюмеры для всех каналов
   - `CreateDynamicConsumerAction`: Получить событие о новом канале, валидировать через кэш, создать новый консьюмер
   - `BatchProcessPostsAction`: Получить батч постов, валидировать, batch upsert в БД
   - `UpdateChannelCacheAction`: Обновить кэш при получении события из tg_channels_diff
   
   **Tasks** (Атомарные операции):
   - `LoadChannelsFromDBTask`: SELECT all channels from DB (интеграция с БД Telegram-Channel-Consumer или локальная таблица?)
   - `CreateKafkaConsumerTask`: Создать AIOKafkaConsumer для топика tg_posts_{id}
   - `BatchUpsertPostsTask`: INSERT ON CONFLICT UPDATE для списка Post объектов
   - `ValidatePostsTask`: Pydantic валидация структуры постов
   - `UpdateCacheTask`: Обновить PostObjectsCache с новыми каналами
   - `CheckDuplicateTask`: Проверить наличие канала в кэше
   - `ConsumePostsBatchTask`: consumer.getmany() для чтения батча
   - `RegisterConsumerTask`: Добавить консьюмер в DynamicConsumerManager
   
   **Models** (Piccolo ORM):
   - `Post`: id, content, repost_count, view_count, link (JSONB), message_timestamp, has_reactions, id_channels, free_reactions_count, paid_reactions_count
   
   **Services**:
   - `PostObjectsCache`: In-memory словарь {channel_id: channel_data} с TTL и sync методами
   - `DynamicConsumerManager`: Управление словарем {channel_id: AIOKafkaConsumer}, старт/стоп консьюмеров
   
   **Workers**:
   - `ConsumerWorker`: Базовый worker для обработки постов из топика tg_posts_{id}
   - `ChannelsDiffWorker`: Worker для прослушивания tg_channels_diff и создания консьюмеров

2. **Создать Piccolo Models** → `data-model.md`:
   ```python
   class Post(Table):
       id = Integer(primary_key=True)
       content = Text(null=True)
       repost_count = Integer(null=True)
       view_count = Integer(null=True)
       link = JSONB(null=True)
       message_timestamp = Timestamp(null=True)
       has_reactions = Boolean(null=True)
       id_channels = Integer(null=True)  # FK to channels (external microservice)
       free_reactions_count = Integer(null=True)
       paid_reactions_count = Integer(null=True)
   ```
   
   **Связи**:
   - id_channels → channels.id (внешний микросервис, soft reference)
   
   **Стратегия миграций**:
   - Создать таблицу posts с индексом на id_channels для быстрого поиска
   - Возможно нужен индекс на message_timestamp для временных запросов
   
   **Правила валидации**:
   - id обязателен (первичный ключ)
   - message_timestamp должен быть валидный timestamp
   - link должен быть валидный JSON

3. **Сгенерировать контракты Workers** → `/contracts/`:
   - Worker interface для ConsumerWorker
   - Worker interface для ChannelsDiffWorker
   - DTO для PostDTO (Pydantic схема)
   - DTO для ConsumerConfigDTO
   
   *Примечание: Этот сервис не имеет HTTP API, только Kafka workers*

4. **Создать контракты Dishka DI**:
   ```python
   # TgPost/Providers.py
   - Provider для PostObjectsCache (scope=Scope.APP - singleton)
   - Provider для DynamicConsumerManager (scope=Scope.APP - singleton)
   - Provider для Post model
   
   # Ship/Providers.py (если нужны обновления)
   - Provider для KafkaClient
   - Provider для KafkaAdmin
   ```
   
   **Графы зависимостей**:
   - ConsumerWorker → DynamicConsumerManager → KafkaClient
   - ChannelsDiffWorker → CreateDynamicConsumerAction → PostObjectsCache
   - BatchProcessPostsAction → ValidatePostsTask → BatchUpsertPostsTask
   
   **Определения Scope**:
   - APP scope: Singletons (Cache, Manager)
   - REQUEST scope: Kafka consumers (создаются динамически)

5. **Сгенерировать тестовые сценарии** → `quickstart.md`:
   
   **Интеграционные тесты для Actions**:
   - `test_initialize_consumers_action`: Создать тестовые каналы в БД, запустить InitializeConsumersAction, проверить создание консьюмеров
   - `test_create_dynamic_consumer_action`: Отправить событие в tg_channels_diff, проверить создание нового консьюмера
   - `test_batch_process_posts_action`: Отправить батч постов, проверить сохранение в БД
   
   **Unit тесты для Tasks**:
   - `test_batch_upsert_posts_task`: Проверить INSERT ON CONFLICT UPDATE логику
   - `test_validate_posts_task`: Проверить валидацию с валидными/невалидными данными
   - `test_check_duplicate_task`: Проверить обнаружение дубликатов в кэше
   
   **Тесты Services**:
   - `test_post_objects_cache`: Проверить put, get, clear, TTL
   - `test_dynamic_consumer_manager`: Проверить add, remove, get_all консьюмеров
   
   **Тесты миграций базы данных**:
   - `test_post_migration`: Проверить создание таблицы posts с правильной схемой

**Результат**: porto-structure.md, data-model.md, contracts/, quickstart.md

## Фаза 2: Подход к планированию задач (Porto)
*Этот раздел описывает что будет делать команда /tasks - НЕ ВЫПОЛНЯТЬ во время /plan*

**Стратегия генерации задач Porto**:

1. **Задачи настройки**: 
   - Создать структуру директорий AppSection/TgPost/
   - Создать PiccoloApp.py для TgPost
   - Создать Providers.py с Dishka провайдерами
   - Создать Config/container_settings.py
   - Создать базовые __init__.py файлы

2. **Задачи Model [P]**: 
   - Создать Models/Post.py с Piccolo Table
   - Сгенерировать миграцию для таблицы posts
   - Создать Data/PostDTO.py с Pydantic схемой

3. **Реализация Task [P]**:
   - Реализовать LoadChannelsFromDBTask
   - Реализовать CreateKafkaConsumerTask
   - Реализовать BatchUpsertPostsTask (с ON CONFLICT)
   - Реализовать ValidatePostsTask
   - Реализовать UpdateCacheTask
   - Реализовать CheckDuplicateTask
   - Реализовать ConsumePostsBatchTask
   - Реализовать RegisterConsumerTask
   - Создать unit тесты для каждого Task

4. **Реализация Action**:
   - Реализовать InitializeConsumersAction
   - Реализовать CreateDynamicConsumerAction
   - Реализовать BatchProcessPostsAction
   - Реализовать UpdateChannelCacheAction
   - Создать интеграционные тесты для каждого Action

5. **Задачи Services**:
   - Реализовать Services/PostObjectsCache.py
   - Реализовать Services/DynamicConsumerManager.py
   - Создать тесты для сервисов

6. **Задачи Workers**:
   - Реализовать UI/Workers/ConsumerWorker.py
   - Реализовать UI/Workers/ChannelsDiffWorker.py
   - Создать UI/CLI/InitConsumersCommand.py (опционально)
   - Создать интеграционные тесты для workers

7. **Задачи Exceptions**:
   - Создать Exceptions/BatchUpsertException.py
   - Создать Exceptions/ConsumerCreationException.py
   - Создать Exceptions/CacheValidationException.py

8. **Задачи интеграции**:
   - Зарегистрировать TgPost провайдеры в Dishka
   - Зарегистрировать PiccoloApp в piccolo_conf.py
   - Интегрировать Logfire трассировку в Actions/Tasks
   - Создать Bootstrap.py entry point для запуска workers

9. **Задачи миграции старого кода**:
   - Удалить устаревший контейнер message/ (после проверки)
   - Обновить docker-compose.yml для нового сервиса
   - Обновить README.md с новой архитектурой

**Стратегия порядка Porto**:
1. Setup → Models → Tasks → Services → Actions → Workers → Integration
2. Тесты создаются параллельно с реализацией (TDD подход)
3. Интеграция Ship компонентов после основных компонентов

**Оценка задач**:
- Setup: 5 задач (~2 часа)
- Models: 3 задачи (~2 часа)
- Tasks: 8 задач × 2 (impl + test) = 16 задач (~8 часов)
- Actions: 4 задачи × 2 (impl + test) = 8 задач (~6 часов)
- Services: 2 задачи × 2 (impl + test) = 4 задачи (~4 часа)
- Workers: 3 задачи × 2 (impl + test) = 6 задач (~6 часов)
- Exceptions: 3 задачи (~1 час)
- Integration: 4 задачи (~3 часа)
- Migration: 3 задачи (~2 часа)

**Итого**: ~49 задач, ~34 часа работы

## Фаза 3+: Будущая реализация
*Эти фазы выходят за рамки команды /plan*

**Фаза 3**: Выполнение задач (tasks.md будет создан командой /tasks)
**Фаза 4**: Реализация по паттернам Porto с TDD
**Фаза 5**: Валидация со стандартами тестирования Porto (coverage > 80%)
**Фаза 6**: Деплой и мониторинг через Logfire

## Отслеживание сложности Porto
*Нарушений Porto Constitution не обнаружено*

Все компоненты соответствуют принципам Porto:
- Actions оркестрируют Tasks
- Tasks атомарны и переиспользуемы
- Models представляют бизнес-сущности
- Зависимости правильно направлены
- Ship компоненты переиспользуются
- DI используется повсюду

## Отслеживание прогресса
*Этот чек-лист обновляется во время выполнения*

**Статус фаз**:
- [x] Фаза 0: Исследование Porto завершено (research.md будет создан)
- [ ] Фаза 1: Дизайн Porto завершен (porto-structure.md, data-model.md, quickstart.md будут созданы)
- [ ] Фаза 2: Планирование задач Porto завершено
- [ ] Фаза 3: Задачи сгенерированы (требует команды /tasks)
- [ ] Фаза 4: Реализация завершена
- [ ] Фаза 5: Валидация пройдена

**Статус Porto Gate**:
- [x] Размещение Container проверено (AppSection.TgPost)
- [x] Переиспользование Ship компонентов проанализировано
- [x] Соответствие принципам Porto проверено
- [x] Интеграция DI запланирована
- [x] Все ТРЕБУЕТ УТОЧНЕНИЯ разрешены

**Следующие шаги**:
1. Создать research.md с детальным исследованием AIOKafka паттернов
2. Создать porto-structure.md с детальной структурой компонентов
3. Создать data-model.md с Piccolo схемами
4. Создать quickstart.md с тестовыми сценариями
5. Запустить команду /tasks для генерации детальных задач

---
*Основано на Porto Constitution + Litestar + Piccolo + Dishka + Logfire + AIOKafka стеке*


