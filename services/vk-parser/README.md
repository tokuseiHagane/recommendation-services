# VK Parser Service

Сервис для парсинга данных ВКонтакте, построенный на архитектуре **Porto** с использованием **Litestar**, **Piccolo ORM** и **Logfire**.

## 🔗 Связь с AuthorizationService

VK Parser Service работает в связке с [AuthorizationService](../AuthorizationService):
- **Общая БД** — использует ту же PostgreSQL базу для доступа к VK токенам пользователей
- **JWT авторизация** — проверяет `auth_token` cookie, установленный AuthorizationService
- **VK токены** — получает из таблицы `account_tokens` по `account_id` из JWT

## 🚀 Возможности

- **Парсинг профилей и групп VK** — посты, комментарии, статистика, участники
- **Поиск по VK** — поиск профилей, групп, страниц
- **JWT авторизация** — через cookie от AuthorizationService
- **Porto архитектура** — чистая архитектура с разделением на контейнеры
- **Logfire интеграция** — полная observability и трейсинг

## 📋 Требования

- Python 3.11+
- PostgreSQL 16+ (общая БД с AuthorizationService)
- Redis 7+
- Работающий AuthorizationService (для авторизации)

## 🛠 Установка

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/VKParserService.git
cd VKParserService

# Установить зависимости
uv pip install -e ".[dev]"

# Скопировать и настроить env
cp .env.example .env
# ВАЖНО: JWT_SECRET_KEY должен совпадать с AuthorizationService!
```

## ⚙️ Конфигурация

```env
# Database (та же БД, что и AuthorizationService)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/porto_db

# JWT (ДОЛЖЕН совпадать с AuthorizationService!)
JWT_SECRET_KEY=your-jwt-secret-key-same-as-auth-service
JWT_ALGORITHM=HS256
```

## 🚀 Запуск

```bash
# Разработка
make dev

# Production
make run

# Docker
make docker-up
```

## 🔐 Авторизация

### Процесс аутентификации

1. Пользователь авторизуется через **AuthorizationService** (VK OAuth)
2. AuthorizationService устанавливает JWT в cookie `auth_token`
3. При запросе к VK Parser Service:
   - Читается JWT из cookie `auth_token`
   - Проверяется подпись JWT (тот же `JWT_SECRET_KEY`)
   - Извлекается `account_id` из payload
   - Из БД (таблица `account_tokens`) получается VK access token
   - Выполняется запрос к VK API

### Схема

```
┌─────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│   Client    │────▶│ AuthorizationService│────▶│   PostgreSQL     │
│  (Browser)  │     │  (VK OAuth + JWT)   │     │  (account_tokens)│
└─────────────┘     └─────────────────────┘     └──────────────────┘
       │                                                  ▲
       │ cookie: auth_token                              │
       ▼                                                  │
┌─────────────────┐                                       │
│ VK Parser       │───────────────────────────────────────┘
│ Service         │  SELECT access_token WHERE account_id = ?
└─────────────────┘
```

## 📡 API Endpoints

### Парсинг VK

```http
POST /api/v1/parse/vk
Cookie: auth_token=<jwt>
Content-Type: application/json

{
  "links": ["https://vk.com/lentach"],
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-01-31T23:59:59",
  "top_n": 10
}
```

### Поиск VK

```http
GET /api/v1/search/vk?q=lentach
Cookie: auth_token=<jwt>
```

### Health Check

```http
GET /api/v1/health
```

### Документация

```
http://localhost:8000/api/v1/vk/docs
```

## 🏗 Архитектура

```
src/
├── Bootstrap.py              # Точка входа
├── Ship/                     # Инфраструктура
│   ├── Core/
│   │   ├── Database.py       # Piccolo PostgreSQL
│   │   ├── TokenStorage.py   # Получение VK токенов из БД
│   │   └── Logging.py        # Logfire
│   ├── Configs/App.py        # Настройки
│   └── Parents/              # Базовые классы Porto
└── Containers/AppSection/VkParser/
    ├── Actions/              # Use cases
    ├── Models/
    │   └── AccountTokens.py  # Piccolo модель (read-only)
    └── UI/API/Controllers/   # API контроллеры
```

## 🔧 Технологии

| Технология | Назначение |
|------------|------------|
| **Litestar** | Web framework |
| **Piccolo** | ORM (PostgreSQL) |
| **Dishka** | Dependency Injection |
| **Logfire** | Observability |
| **Redis** | Caching |
| **aiovk** | VK API client |

## 📝 Makefile

```bash
make dev         # Разработка с hot reload
make run         # Production
make test        # Тесты
make docker-up   # Docker
```

## 📄 Лицензия

MIT License
