# posts-consumer

Kubernetes манифесты для [Telegram-Posts-Consumers](https://github.com/FatDataProduct/Telegram-Posts-Consumers).

> **Текущий скоуп — только VK.** Разворачиваем только `vk-posts-consumer-*`. `tg-posts-consumer-*` манифесты лежат в репо как заготовки, но сейчас **не применяются** — TG-пайплайн out of scope (см. `../README.md`).

## Что это

Distributed-monolith с двумя независимыми Kafka consumer'ами (без HTTP-сервера). Один общий Docker-образ, режим выбирается переменной `SERVICE=tg|vk` + `args` в Deployment.

**VkPost** (`python -m src.BootstrapVk`, активный режим):

- Слушает `vk_groups_diff` → динамически подписывается на `vk_posts_{group_id}`.
- Пишет в БД **`vkparser_db`** (тот же DSN, что у VKParserService) в таблицы `posts` и `groups` — они уже созданы парсером. Consumer делает upsert'ы по `id`.

`docker-entrypoint.sh` при старте:
1. Ждёт готовности PostgreSQL (asyncpg ping).
2. При `SERVICE=vk` экспортирует `VK_DB_*` в `DB_*` (требование Piccolo-конфига).
3. Применяет `piccolo migrations forwards VkPost`.
4. `exec "$@"` → `python -m src.BootstrapVk`.

## Контуры (VK)

| Env | Image | Deployment |
|-----|-------|-----------|
| test | `ghcr.io/fatdataproduct/telegram-posts-consumers/posts-consumer-test:latest` | `vk-posts-consumer-test` |
| prod | `ghcr.io/fatdataproduct/telegram-posts-consumers/posts-consumer-prod:latest` | `vk-posts-consumer-prod` (отложено) |

## Apply (test)

Предусловия: `vkparser_db` существует (уже создана VKParserService), `ghcr-login-secret` есть в `parsers`.

### ⚠️ Шаг 1. Fake-миграция (обязательно, один раз)

Piccolo-миграция `VkPost` делает `add_table("posts")` + `add_table("groups")`. В `vkparser_db` эти таблицы уже есть → entrypoint упадёт с `relation "posts" already exists`. Перед первым apply Deployment'а помечаем миграцию применённой через одноразовый Job:

```bash
kubectl apply -f test/vk-configmap.yaml -f test/vk-secret.yaml
kubectl apply -f test/vk-migrate-fake-job.yaml

kubectl -n parsers wait --for=condition=complete job/vk-posts-consumer-test-migrate-fake --timeout=120s
kubectl -n parsers logs job/vk-posts-consumer-test-migrate-fake
```

В логах должна быть строка вроде `Ran VkPost/2026-02-01T20:04:43:605037 in fake mode`. Job удалится автоматически через `ttlSecondsAfterFinished=86400`.

Повторный запуск Job'а в той же БД безопасен (`--fake` идемпотентен).

### Шаг 2. Deployment

```bash
kubectl apply -f test/vk-deployment.yaml

kubectl -n parsers rollout status deployment/vk-posts-consumer-test --timeout=120s
kubectl -n parsers logs -l app=vk-posts-consumer-test --tail=100
```

В логах при старте должно быть: `[entrypoint] Running piccolo migrations forwards VkPost` → `All migrations are up to date` → запуск `src.BootstrapVk` → подписка на `vk_groups_diff`.

## Почему нет Service/Ingress

`BootstrapVk` — чистый asyncio loop без HTTP. Probe'ов HTTP нет; при необходимости можно добавить `exec` probe `pgrep -f BootstrapVk`.

## Секреты

- test: `VK_DB_PASSWORD` = root-пароль VKParserService (`XjcZYWHuxnxU`). Открытый паттерн принят в репо.
- prod: `CHANGE_ME`, правится на кластере (см. правило `no-overwrite-server-locals`).
