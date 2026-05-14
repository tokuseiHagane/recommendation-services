# Авторизация

Основной trust-contract для VK Parser Service теперь такой:

1. Frontend получает JWT в AuthService через `/api/auth/token`.
2. Frontend отправляет JWT в `Authorization: Bearer <jwt>`.
3. Parser офлайн валидирует JWT через JWKS (`PyJWT` + `PyJWKClient`) с `iss=fdauth-service`.
4. Parser вызывает внутренний backend-only endpoint AuthService и получает VK token текущего пользователя, пробрасывая Bearer JWT и внутренний shared secret.
5. Parser использует полученный VK token для VK API.

## Основной поток

```text
Frontend -- Bearer JWT --> VK Parser Service
                              |
                              |- verify JWT via JWKS
                              |    AUTH_JWKS_URL
                              |
                              '- GET AUTH_VK_TOKEN_ENDPOINT
                                   Authorization: Bearer <same-jwt>
                                   X-Auth-Backend-Secret: <shared-secret>
                                   on AUTH_SERVICE_URL
```

## HTTP контракт

### Запрос к parser API

```http
POST /api/v1/parse/vk
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6Ii4uLiJ9...
Content-Type: application/json
```

```http
GET /api/v1/search/vk?q=lentach
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6Ii4uLiJ9...
```

### Ожидаемые claims JWT

```json
{
  "sub": "clxxxxxxxxxxxxxxxxx",
  "iss": "fdauth-service",
  "iat": 1704063600,
  "exp": 1704067200
}
```

Parser требует наличие `sub`, `iss`, `iat`, `exp` и проверяет `iss` на значение `AUTH_JWT_ISSUER`.

## Конфигурация

### Основные настройки

```env
AUTH_SERVICE_URL=http://auth-service:3000
AUTH_JWKS_URL=http://auth-service:3000/api/auth/jwks
AUTH_JWT_ISSUER=fdauth-service
AUTH_JWT_ALGORITHMS=["RS256"]
AUTH_JWT_LEEWAY_SECONDS=30
AUTH_JWKS_CACHE_TTL_SECONDS=300
AUTH_VK_TOKEN_ENDPOINT=/api/internal/auth/vk-account
AUTH_BACKEND_SHARED_SECRET=change-me-in-prod
AUTH_HTTP_TIMEOUT_SECONDS=5.0
```

`AUTH_JWKS_URL` можно не задавать, тогда сервис соберёт URL как `AUTH_SERVICE_URL + "/api/auth/jwks"`.

### Временный compatibility mode

Во время переходного периода поддерживаются вторичные fallback-механизмы:

```env
AUTH_ENABLE_LEGACY_COOKIE_FALLBACK=false
AUTH_ENABLE_LEGACY_DB_FALLBACK=false
VK_ACCESS_TOKEN=
```

Что они делают:

- `AUTH_ENABLE_LEGACY_COOKIE_FALLBACK=true` разрешает временно принять JWT из cookie `auth_token`, если `Authorization` отсутствует.
- `AUTH_ENABLE_LEGACY_DB_FALLBACK=true` разрешает временно взять VK token из legacy-таблицы `account_tokens`, если внутренний endpoint AuthService недоступен или ещё не выкачен.
- `VK_ACCESS_TOKEN` остаётся последним аварийным fallback для локальной отладки.

По умолчанию compatibility-опции должны быть выключены. Включать их стоит только как осознанный временный rollback-механизм во время миграции.

## Ошибки авторизации

| Код | Сообщение | Причина |
|-----|-----------|---------|
| 401 | Authentication required. Send Authorization: Bearer `<jwt>`. | Отсутствует Bearer JWT |
| 401 | Invalid Authorization header. | Неверный формат `Authorization` |
| 401 | Session expired. Please login again. | JWT истёк |
| 401 | Invalid token issuer. | `iss` не совпадает с `AUTH_JWT_ISSUER` |
| 401 | Invalid authentication token. | Неверная подпись или claims JWT |
| 401 | Failed to verify authentication token via JWKS. | Недоступен JWKS или не найден signing key |
| 401 | AuthService rejected authenticated request. | Внутренний auth endpoint отверг Bearer JWT |
| 403 | AuthService rejected backend secret. | Неверный или отсутствующий `X-Auth-Backend-Secret` |
| 401 | VK token not found. Please link your VK account via AuthorizationService. | AuthService и fallback-источники не дали VK token |

## Legacy fallback storage

При включённом `AUTH_ENABLE_LEGACY_DB_FALLBACK` parser временно может читать старую таблицу:

```sql
CREATE TABLE account_tokens (
    id SERIAL PRIMARY KEY,
    account_id UUID NOT NULL,
    user_id VARCHAR(73) NOT NULL,
    access_token VARCHAR(256) NOT NULL,
    refresh_token VARCHAR(256),
    auth_provider VARCHAR(16) DEFAULT 'vk',
    created_timestamp TIMESTAMPTZ DEFAULT NOW(),
    updated_timestamp TIMESTAMPTZ DEFAULT NOW(),
    deleted_timestamp TIMESTAMPTZ,
    expiration_timestamp TIMESTAMPTZ
);
```

Этот путь больше не считается основным контрактом. При переходе на `CUID` в `sub` legacy DB fallback применим только для старых токенов, где `auth_user_id` ещё совместим с UUID.
