# Parsers Namespace

Kubernetes manifests for parsing services in namespace `parsers`.

## Services

> **Текущий скоуп — только VK-пайплайн.** TG-контур (tg-модуль в tg-channel-consumer и `tg-posts-consumer-*` Deployment из posts-consumer) **не разворачивается**. Манифесты под него лежат в репо как заготовки, но в apply-плане они пропущены.

- **vkparser** — VK Parser Service (Litestar API; Kafka **producer** → `vk_groups`, `vk_posts_{group_id}`). **Уже развёрнут.** `vkparser_db` создана, в ней есть таблицы `groups`, `posts`, `cached_periods`, `account_tokens`.
- **tg-channel-consumer** — Litestar + Kafka consumer/producer. В test-контуре включён **только VK-модуль** (`ENABLE_VK_MODULE=true`, `ENABLE_TG_MODULE=false`). Читает `vk_groups`, пишет в `vk_groups_diff`, upsert в таблицу `groups` в **`vkparser_db`**.
- **posts-consumer** — чистый Kafka consumer (без HTTP). В test-контуре применяем **только `vk-posts-consumer-*`** (`python -m src.BootstrapVk`). Мониторит `vk_groups_diff` → динамически подписывается на `vk_posts_{group_id}` → upsert в таблицы `posts`/`groups` в **`vkparser_db`**.

## Layout

```
parsers/
├── namespace.yaml
├── cert-secret.sh           # копирует cert-secret из ns front
├── ghcr-login-secret.sh     # копирует ghcr-login-secret из ns bots
├── test/                    # vkparser test (историческое расположение)
├── prod/                    # vkparser prod (configmap/deployment/service/ingress/secret)
├── tg-channel-consumer/
│   ├── test/
│   └── prod/
└── posts-consumer/
    ├── test/      # tg-*.yaml + vk-*.yaml
    └── prod/
```

## Кто куда пишет (FDVK-18, VK-скоуп)

Единый **VK parse-flow** `parser → Kafka → consumer` стекается в одну БД — это требование аналитики и pipeline-документации парсера. У всех VK test-деплоев DSN **полностью совпадает** с `vkparser-test-secret.DATABASE_URL`:

```
postgresql://root:XjcZYWHuxnxU@postgres.databases.svc.cluster.local:5432/vkparser_db
```

| Сервис | Состояние | Роль Kafka | Топики (потребляет) | Топики (пишет) | БД (test) | Таблицы |
|--------|-----------|------------|---------------------|----------------|-----------|---------|
| vkparser | **развёрнут** | producer | — | `vk_groups`, `vk_posts_{gid}` | `vkparser_db` | `groups`, `posts`, `cached_periods`, `account_tokens` |
| tg-channel-consumer (VK-модуль) | разворачиваем | consumer + producer | `vk_groups` | `vk_groups_diff` | `vkparser_db` | `groups` (общая с vkparser) |
| vk-posts-consumer | разворачиваем | consumer | `vk_groups_diff`, `vk_posts_{gid}` | — | `vkparser_db` | `posts`, `groups` (общие с vkparser) |
| tg-channel-consumer (TG-модуль) | **out of scope** (`ENABLE_TG_MODULE=false`) | — | — | — | — | — |
| tg-posts-consumer | **out of scope** (Deployment не применяем) | — | — | — | — | — |

Все таблицы в схеме **`public`**.

### Общие таблицы VKParserService ↔ VK-консьюмеры

Таблицы `groups`/`posts` уже созданы VKParserService — консьюмеры их не пересоздают, только пишут upsert'ы по `id`:

- **tg-channel-consumer (VK)**: в lifespan `create_db_tables(if_not_exists=True)` → `groups` уже есть, шаг no-op. Consumer пишет `id/name/screen_name/members_count`, поле `last_parsed_at` от VKParserService не трогает.
- **vk-posts-consumer**: использует `piccolo migrations forwards VkPost`. Миграция `vkpost_2026_02_01t20_04_43_605037.py` содержит `add_table("posts")` + `add_table("groups")` — в `vkparser_db` упадёт с `relation already exists`. Поэтому **перед первым apply деплоймента нужно применить одноразовый Job** `posts-consumer/test/vk-migrate-fake-job.yaml` — он выполняет `piccolo migrations forwards VkPost --fake` (помечает миграцию применённой без создания таблиц). См. `posts-consumer/README.md`.

## Setup (VK-скоуп, test)

VKParserService и БД `vkparser_db` уже развёрнуты — базу создавать не нужно. Задача — добавить двух VK-консьюмеров в тот же DSN.

```bash
# 0. kubectl context
kubectl config use-context back

# 1. Namespace и общие секреты (уже применены для vkparser, идемпотентны)
kubectl apply -f namespace.yaml
bash ghcr-login-secret.sh
bash cert-secret.sh

# 2. Channel consumer (только VK-модуль, TG отключён флагом)
kubectl apply -f tg-channel-consumer/test/

# 3. Fake-миграция Piccolo VkPost в vkparser_db (ОДИН раз, до первого apply vk-deployment)
kubectl apply -f posts-consumer/test/vk-migrate-fake-job.yaml
kubectl -n parsers wait --for=condition=complete job/vk-posts-consumer-test-migrate-fake --timeout=120s
kubectl -n parsers logs job/vk-posts-consumer-test-migrate-fake

# 4. VK Posts consumer
kubectl apply -f posts-consumer/test/vk-configmap.yaml \
              -f posts-consumer/test/vk-secret.yaml \
              -f posts-consumer/test/vk-deployment.yaml

# 5. Проверка
kubectl -n parsers get pods -l provider=vk
kubectl -n parsers logs -l app=tg-channel-consumer-test --tail=50
kubectl -n parsers logs -l app=vk-posts-consumer-test  --tail=50
```

TG-манифесты (`tg-channel-consumer/test/configmap.yaml` у TG-модуля, `posts-consumer/test/tg-*.yaml`) пока **не применяем** — TG-пайплайн out of scope.

## Cluster conventions

- **context:** `back`
- **nodeSelector:** `kubernetes.io/hostname=angron-node0`
- **ingress:** `testanalytics.fatdataseo.com/api` (только vkparser; консьюмеры внутренние)
- **brokers:** `redpanda.redpanda.svc.cluster.local:9092` (без SASL/mTLS)
- **postgres test:** `postgres.databases.svc.cluster.local:5432`, user `root`
- **postgres prod:** `postgres-prod.databases.svc.cluster.local:5432`, user `root`

## Секреты

- Test: `VK_DB_PASSWORD` в `*/secret.yaml` = `XjcZYWHuxnxU` (тот же root, что в `vkparser-test-secret.DATABASE_URL`). Открытый паттерн уже принят в этом репо.
- Prod: значения в репо — `CHANGE_ME`. Реальные пароли прописываются **только на кластере** через `kubectl edit secret` / `kubectl create secret generic ... --dry-run=client -o yaml | kubectl apply -f -`. См. также правило `no-overwrite-server-locals`.

## Prod

Prod-манифесты VKParserService лежат в `backend/parsers/prod/` (`configmap.yaml`, `deployment.yaml`, `service.yaml`, `ingress.yaml`, `secret.yaml`). Ingress поднимает `analytics.fatdataseo.com/api` → `vkparser-prod-service:8000`. Контур prod **пока не применён** — перед первым `kubectl apply` нужно:

1. Заполнить реальный `DATABASE_URL` (prod Postgres `postgres-prod.databases.svc.cluster.local`, БД `vkparser_db` — унифицированная с VK-консьюмерами), `AUTH_BACKEND_SHARED_SECRET`, `JWT_SECRET_KEY`, `VK_ACCESS_TOKEN`, `LOGFIRE_TOKEN` в `secret.yaml` (см. `no-overwrite-server-locals`).
2. Убедиться, что `auth-prod-configmap` содержит `COOKIE_DOMAIN=.fatdataseo.com` (чтобы сессионная кука шарилась между `auth.fatdataseo.com` и `analytics.fatdataseo.com`). `FRONTEND_URL` у auth-prod указывает на его собственный тестовый фронт (`https://auth.fatdataseo.com`), а не на analytics — это штатный сценарий.
3. Прогнать Piccolo fake-миграцию VK-консьюмеров (аналогично test) — если `vkparser_db` будет общей с консьюмерами.
