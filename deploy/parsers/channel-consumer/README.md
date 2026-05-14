# tg-channel-consumer

Kubernetes манифесты для [Telegram-Channel-Consumer](https://github.com/FatDataProduct/Telegram-Channel-Consumer).

## Что это

Litestar-приложение с двумя модулями (`ENABLE_TG_MODULE` / `ENABLE_VK_MODULE`). В **test-контуре сейчас включён только VK-модуль** (`ENABLE_TG_MODULE=false`), TG-контур — out of scope (см. `../README.md`).

- **VK** (активен): Kafka consumer на `vk_groups` → upsert в таблицу `groups` → publish diff-событий в `vk_groups_diff`.
  - DSN = **точно совпадает** с `vkparser-test-secret.DATABASE_URL`: `postgres.databases.svc.cluster.local:5432/vkparser_db`, user `root`, password `XjcZYWHuxnxU`.
  - Таблица `groups` уже создана VKParserService. `create_db_tables(if_not_exists=True)` в lifespan — no-op. Consumer пишет только `id/name/screen_name/members_count`, `last_parsed_at` VKParserService не трогает.

При `ENABLE_TG_MODULE=false` код `start_tg_module()` в `app.py` делает early-return, TG-импорты (`tg_channel_model`, `tg_channel_kafka_worker`) не грузятся, к TG-БД не подключается. Поэтому `TG_DB_*` в configmap/secret не передаём (в `Settings` есть defaults).

HTTP-сервер на `:8000` с `/health` для probes.

## Контуры

| Env | Image | Deployment | Service |
|-----|-------|-----------|---------|
| test | `ghcr.io/fatdataproduct/social-channel-consumer/tg-channel-consumer-test:latest` | `tg-channel-consumer-test` | `tg-channel-consumer-test-service` |
| prod | `ghcr.io/fatdataproduct/social-channel-consumer/tg-channel-consumer-prod:latest` | `tg-channel-consumer-prod` | `tg-channel-consumer-prod-service` |

## Apply

```bash
# Prerequisites:
# - namespace parsers (уже есть, применён для vkparser)
# - ghcr-login-secret, cert-secret (уже есть)
# - vkparser_db (уже создана VKParserService)

kubectl apply -f test/
```

Prod разворачивать пока рано — у VKParserService ещё нет prod-манифестов.

## Запуск в контейнере

Образ из Dockerfile имеет `CMD ["python", "-m", "src.Bootstrap"]`, но этот модуль **без Kafka consumer'ов** (dev). В Deployment мы переопределяем команду на запуск `app.py` через uvicorn:

```yaml
command: ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Таблица `groups` авто-создаётся в `lifespan` через `create_db_tables(..., if_not_exists=True)` — в `vkparser_db` она уже есть, поэтому шаг идемпотентен.

## Секреты

- test: в `secret.yaml` только `VK_DB_PASSWORD` (= root-пароль VKParserService). `TG_DB_PASSWORD` не нужен — TG-модуль выключен, Settings берёт default.
- prod: `CHANGE_ME` — реальные значения прописываются на кластере (см. правило `no-overwrite-server-locals`).
