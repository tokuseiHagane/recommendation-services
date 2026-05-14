# API Reference

## Авторизация

Все эндпоинты (кроме health) требуют JWT в cookie `auth_token`.

Cookie устанавливается AuthorizationService после успешной VK OAuth авторизации.

---

## POST /api/v1/parse/vk

Парсинг VK профилей и групп.

### Request

```http
POST /api/v1/parse/vk
Cookie: auth_token=<jwt>
Content-Type: application/json
```

```json
{
  "links": [
    "https://vk.com/lentach",
    "https://vk.com/mdk"
  ],
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-01-31T23:59:59",
  "top_n": 10,
  "sort_params": {
    "date": {"priority": 1, "reverse": false},
    "views": {"priority": 2, "reverse": true},
    "engagement_rate": {"priority": 1, "reverse": true},
    "comments": {"priority": 1, "reverse": true},
    "reposts": {"priority": 1, "reverse": true}
  }
}
```

### Parameters

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `links` | array[string] | Да | Ссылки на VK профили/группы |
| `start_date` | datetime | Да | Начало периода |
| `end_date` | datetime | Да | Конец периода |
| `top_n` | integer | Нет | Количество топ постов (default: 10) |
| `sort_params` | object | Нет | Параметры сортировки |

### Response

```json
{
  "status": "success",
  "data": {
    "lentach": {
      "members_count": 1234567,
      "posts_count": 150,
      "top_posts": [...],
      "down_posts": [...],
      "period_posts_metrics": {
        "total_likes": 50000,
        "total_views": 1000000,
        "engagement_rate": 3.5
      },
      "members_info": {
        "males": 60,
        "females": 35,
        "avg_age": 25
      }
    }
  },
  "domains_count": 1
}
```

---

## GET /api/v1/search/vk

Поиск VK профилей и групп.

### Request

```http
GET /api/v1/search/vk?q=lentach
Cookie: auth_token=<jwt>
```

### Parameters

| Параметр | Тип | Обязательно | Описание |
|----------|-----|-------------|----------|
| `q` | string | Да | Поисковый запрос |

### Response

```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "type": "group",
        "group": {
          "id": 12345,
          "name": "Лентач",
          "screen_name": "lentach",
          "photo_100": "https://..."
        }
      }
    ]
  },
  "count": 10
}
```

---

## GET /api/v1/health

Проверка здоровья сервиса.

### Request

```http
GET /api/v1/health
```

### Response (с авторизацией)

```json
{
  "status": "healthy",
  "service": "vk-parser-service",
  "authenticated": true,
  "has_vk_token": true,
  "account_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Response (без авторизации)

```json
{
  "status": "healthy",
  "service": "vk-parser-service",
  "authenticated": false,
  "has_vk_token": false,
  "account_id": null
}
```

---

## Коды ошибок

| HTTP Code | Описание |
|-----------|----------|
| 200 | Успешный запрос |
| 400 | Неверные параметры запроса |
| 401 | Не авторизован / нет VK токена |
| 429 | Rate limit VK API |
| 500 | Внутренняя ошибка сервера |
| 502 | Ошибка VK API |

### Формат ошибки

```json
{
  "error": {
    "code": "VK_AUTH_ERROR",
    "message": "VK token not found",
    "details": {
      "account_id": "550e8400-..."
    }
  }
}
```

