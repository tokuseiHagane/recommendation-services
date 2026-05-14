# Задачи: [НАЗВАНИЕ ФУНКЦИИ] (Porto)

**Исходные данные**: Документы дизайна Porto из `/specs/[###-feature-name]/`
**Container**: [AppSection/VendorSection].[ContainerName]
**Предварительные требования**: plan.md (обязательно), research.md, data-model.md, contracts/, porto-structure.md

## Алгоритм выполнения (main)
```
1. Загрузить plan.md и porto-structure.md из каталога функции
   → Извлечь: размещение Container, Actions, Tasks, Models, UI компоненты
2. Загрузить документы дизайна Porto:
   → data-model.md: Извлечь Piccolo модели → задачи для моделей
   → contracts/: Каждая конечная точка → задачи контроллер/маршрут
   → research.md: Извлечь настройку Dishka/Logfire → задачи интеграции
3. Сгенерировать Porto-специфичные задачи по категориям:
   → Настройка: структура Container, приложение Piccolo, DI провайдеры
   → Модели: Piccolo модели с миграциями [P]
   → Задачи: Атомарные операции с Ship Parents [P]
   → Действия: Оркестрация бизнес-логики
   → UI: Контроллеры, маршруты, трансформеры
   → Интеграция: Регистрация DI, интеграция Ship, Logfire
   → Тесты: TDD для всех компонентов
4. Применить правила задач Porto:
   → Разные файлы = отметить [P] для параллельного выполнения
   → Следовать зависимостям Porto: Модели → Задачи → Действия → UI
   → Интеграция Ship после основных компонентов
5. Пронумеровать задачи последовательно (T001, T002...)
6. Сгенерировать граф зависимостей Porto
7. Проверить полноту Porto:
   → У всех моделей есть миграции?
   → У всех компонентов есть DI провайдеры?
   → У всех Actions есть соответствующие контроллеры?
8. Вернуть: УСПЕХ (задачи Porto готовы к выполнению)
```

## Формат: `[ID] [P?] Описание`
- **[P]**: Может выполняться параллельно (разные файлы, нет зависимостей Porto)
- Включать точные пути файлов Porto в описаниях

## Соглашения о путях Porto
```
src/Containers/[Section]/[Container]/
├── Actions/[Action]Action.py
├── Tasks/[Task]Task.py  
├── Models/[Model].py
├── UI/API/Controllers/[Controller].py
├── Data/[DTO].py
├── Exceptions/[Exception].py
├── migrations/[timestamp]_[description].py
├── PiccoloApp.py
└── Providers.py
```

## Фаза 3.1: Настройка Porto Container
- [ ] T001 Создать структуру каталогов Container в `src/Containers/[Section]/[Container]/`
- [ ] T002 Инициализировать файлы `__init__.py` для правильных импортов
- [ ] T003 [P] Создать `PiccoloApp.py` с конфигурацией Piccolo
- [ ] T004 [P] Создать `Providers.py` со скелетом Dishka провайдера
- [ ] T005 [P] Создать `shortcuts.py` для импортов уровня контейнера

## Фаза 3.2: Модели Piccolo и миграции (TDD) ⚠️ ДОЛЖНО БЫТЬ ЗАВЕРШЕНО ПЕРЕД 3.3
**КРИТИЧНО: Сначала создать модели и миграции, затем тесты**
- [ ] T006 [P] Создать `[Model1]` в `src/Containers/[Section]/[Container]/Models/[Model1].py`
- [ ] T007 [P] Создать `[Model2]` в `src/Containers/[Section]/[Container]/Models/[Model2].py`
- [ ] T008 Сгенерировать миграцию Piccolo для моделей: `piccolo migrations new [container] --auto`
- [ ] T009 [P] Интеграционный тест модели в `tests/integration/test_[model1]_model.py`
- [ ] T010 [P] Интеграционный тест модели в `tests/integration/test_[model2]_model.py`

## Фаза 3.3: Porto Tasks (Атомарные операции)
**КРИТИЧНО: Сначала создать тесты, затем реализацию**
- [ ] T011 [P] Тест для `[Task1]Task` в `tests/unit/test_[task1]_task.py`
- [ ] T012 [P] Тест для `[Task2]Task` в `tests/unit/test_[task2]_task.py`
- [ ] T013 [P] Реализовать `[Task1]Task` в `src/Containers/[Section]/[Container]/Tasks/[Task1].py`
- [ ] T014 [P] Реализовать `[Task2]Task` в `src/Containers/[Section]/[Container]/Tasks/[Task2].py`

## Фаза 3.4: Porto Actions (Бизнес-логика)
**КРИТИЧНО: Actions зависят от Tasks, сначала создать тесты**
- [ ] T015 Тест для `[Action1]Action` в `tests/integration/test_[action1]_action.py`
- [ ] T016 Тест для `[Action2]Action` в `tests/integration/test_[action2]_action.py`
- [ ] T017 Реализовать `[Action1]Action` в `src/Containers/[Section]/[Container]/Actions/[Action1].py`
- [ ] T018 Реализовать `[Action2]Action` в `src/Containers/[Section]/[Container]/Actions/[Action2].py`

## Фаза 3.5: Слой данных (DTOs и Transformers)
- [ ] T019 [P] Создать DTOs в `src/Containers/[Section]/[Container]/Data/[DTO].py`
- [ ] T020 [P] Создать трансформеры в `src/Containers/[Section]/[Container]/UI/API/Transformers/[Transformer].py`
- [ ] T021 [P] Тесты валидации DTO в `tests/unit/test_[dto]_validation.py`

## Фаза 3.6: Слой UI Litestar
**КРИТИЧНО: Controllers зависят от Actions**
- [ ] T022 Тест контроллера для `[Controller]` в `tests/integration/test_[controller]_api.py`
- [ ] T023 Реализовать `[Controller]Controller` в `src/Containers/[Section]/[Container]/UI/API/Controllers/[Controller].py`
- [ ] T024 Создать маршруты в `src/Containers/[Section]/[Container]/UI/API/Routes/[routes].py`
- [ ] T025 [P] CLI команды в `src/Containers/[Section]/[Container]/UI/CLI/[commands].py` (если нужно)

## Фаза 3.7: Исключения Container
- [ ] T026 [P] Создать исключения контейнера в `src/Containers/[Section]/[Container]/Exceptions/[Exception].py`
- [ ] T027 [P] Тесты обработки исключений в `tests/unit/test_[container]_exceptions.py`

## Фаза 3.8: Интеграция Dishka DI
- [ ] T028 Завершить `Providers.py` со всеми регистрациями компонентов
- [ ] T029 Зарегистрировать провайдер контейнера в `src/Ship/Providers/App.py`
- [ ] T030 Тест интеграции DI в `tests/integration/test_[container]_di.py`

## Фаза 3.9: Интеграция Piccolo и базы данных
- [ ] T031 Зарегистрировать PiccoloApp в `piccolo_conf.py`
- [ ] T032 Запустить миграцию базы данных: `piccolo migrations forwards [container]`
- [ ] T033 Тест интеграции базы данных в `tests/integration/test_[container]_database.py`

## Фаза 3.10: Интеграция Ship и наблюдаемость
- [ ] T034 Добавить трассировку Logfire к Actions (используя Ship Parents)
- [ ] T035 Настроить специфичное для контейнера логирование в Ship
- [ ] T036 [P] Обновить `src/Ship/App.py` для включения новых контроллеров
- [ ] T037 [P] Интеграционный тест для полного потока запросов в `tests/e2e/test_[feature]_e2e.py`

## Фаза 3.11: Документация и доработка
- [ ] T038 [P] Обновить `__init__.py` контейнера с правильными экспортами
- [ ] T039 [P] Добавить docstrings ко всем публичным методам
- [ ] T040 [P] Обновить документацию OpenAPI
- [ ] T041 [P] Создать примеры использования в `examples/[feature]_usage.py`

## Зависимости Porto
```
Настройка (T001-T005) → Модели (T006-T010) → Tasks (T011-T014) → Actions (T015-T018)
                      ↘ Данные (T019-T021) → UI (T022-T025) → Исключения (T026-T027)
                                          ↘ DI (T028-T030) → База данных (T031-T033)
                                                          ↘ Интеграция Ship (T034-T037)
                                                                          ↘ Доработка (T038-T041)
```

## Примеры параллельного выполнения (Porto)
```bash
# Фаза 3.2: Модели (можно выполнять параллельно)
Задача: "Создать модель User в src/Containers/AppSection/User/Models/User.py"
Задача: "Создать модель Profile в src/Containers/AppSection/User/Models/Profile.py"

# Фаза 3.3: Tasks (можно выполнять параллельно) 
Задача: "Реализовать CreateUserTask в src/Containers/AppSection/User/Tasks/CreateUser.py"
Задача: "Реализовать FindUserTask в src/Containers/AppSection/User/Tasks/FindUser.py"
```

## Контрольный список проверки Porto
*КОНТРОЛЬНАЯ ТОЧКА: Проверяется main() перед возвратом*

### Структура Container
- [ ] Все каталоги Porto созданы правильно
- [ ] PiccoloApp настроен и зарегистрирован
- [ ] Dishka провайдеры правильно структурированы
- [ ] Ship Parents используются для базовых классов

### Зависимости компонентов  
- [ ] Модели созданы перед Tasks
- [ ] Tasks созданы перед Actions
- [ ] Actions созданы перед Controllers
- [ ] Все компоненты имеют правильную регистрацию DI

### Соответствие архитектуре Porto
- [ ] Бизнес-логика в Actions (оркестрация)
- [ ] Атомарные операции в Tasks (переиспользуемые)
- [ ] Персистентность данных в Models (Piccolo)
- [ ] Ship компоненты переиспользованы где возможно
- [ ] Изоляция фреймворка поддерживается

### Стратегия тестирования
- [ ] TDD соблюден: тесты перед реализацией
- [ ] Интеграционные тесты для операций с БД
- [ ] Модульные тесты для бизнес-логики
- [ ] E2E тесты для полных пользовательских потоков
- [ ] Все тесты используют реалистичные данные (не моки)

---
*Porto Architecture + Litestar + Piccolo + Dishka + Logfire*
