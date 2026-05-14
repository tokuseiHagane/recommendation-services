# Архитектура

VK Parser Service построен на архитектуре **Porto** — слоистой архитектуре для масштабируемых приложений.

## Структура проекта

```
src/
├── Bootstrap.py              # Точка входа (production)
├── Main.py                   # Точка входа (development)
├── Ship/                     # Инфраструктурный слой
│   ├── App.py                # Litestar application factory
│   ├── Configs/
│   │   └── App.py            # Pydantic Settings
│   ├── Core/
│   │   ├── Database.py       # Piccolo PostgreSQL engine
│   │   ├── TokenStorage.py   # VK токены из БД
│   │   ├── Cache.py          # Redis cache
│   │   └── Logging.py        # Logfire configuration
│   ├── Parents/
│   │   ├── Action.py         # Базовый класс Action
│   │   ├── Task.py           # Базовый класс Task
│   │   ├── Controller.py     # Базовый контроллер
│   │   └── Exception.py      # Porto исключения
│   ├── Plugins/
│   │   └── LogfirePlugin.py  # Litestar плагин
│   ├── Providers/
│   │   └── App.py            # Dishka DI провайдеры
│   └── Exceptions/
│       └── Handlers.py       # Обработчики ошибок
└── Containers/
    └── AppSection/
        └── VkParser/         # Контейнер VK Parser
            ├── Actions/
            │   ├── ParseVkDataAction.py
            │   └── SearchVkAction.py
            ├── Models/
            │   └── AccountTokens.py  # Piccolo модель
            ├── Data/
            │   └── Dto.py            # Pydantic DTOs
            ├── Exceptions/
            │   └── VkParserException.py
            ├── Providers.py          # DI провайдеры
            └── UI/API/Controllers/
                └── VkParserController.py
```

## Компоненты Porto

### Ship (Инфраструктура)

Ship содержит общую инфраструктуру, используемую всеми контейнерами:

- **Configs** — конфигурация приложения через Pydantic Settings
- **Core** — базовые сервисы (БД, кеш, логирование)
- **Parents** — абстрактные базовые классы
- **Providers** — DI провайдеры для Dishka
- **Plugins** — плагины Litestar

### Containers (Бизнес-логика)

Контейнеры содержат бизнес-логику, разделённую по доменам:

#### VkParser Container

- **Actions** — бизнес use cases (ParseVkDataAction, SearchVkAction)
- **Models** — Piccolo ORM модели
- **Data** — DTOs и репозитории
- **UI/API** — контроллеры Litestar

## Поток данных

```
Request → Controller → Action → Task/Service → Response
                         ↓
                    Repository
                         ↓
                      Database
```

## Dependency Injection

Используется **Dishka** для DI:

```python
# Providers.py
class VkParserProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_parse_action(self) -> ParseVkDataAction:
        return ParseVkDataAction()
```

## База данных

Используется **Piccolo ORM** для работы с PostgreSQL:

```python
# Запрос VK токена
token = await AccountTokens.select(
    AccountTokens.access_token
).where(
    AccountTokens.account_id == account_id
).first()
```

## Логирование

**Logfire** для observability:

```python
import logfire

logfire.info("VK parse started", domains=domains)

with logfire.span("ParseVkDataAction"):
    result = await action.run(data)
```

