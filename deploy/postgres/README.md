# PostgreSQL Manifests

Манифесты для PostgreSQL в namespace `databases`. Две среды: **test** (текущий кластер) и **prod** (отдельный VPS).

## Статус файлов

### test/

| Файл | Статус | Комментарий |
| --- | --- | --- |
| `deploy.yaml` | deployed | Deployment `postgres:18`, тестовая БД на текущем кластере |
| `postgres-conf.yaml` | deployed | ConfigMap `postgres-config` с `postgresql.conf` |
| `pv-pvc.yaml` | deployed | PV/PVC 20Gi, local-storage `/mnt/storage/` |
| `postgres-service.yaml` | deployed | ClusterIP:5432 |
| `secret.yaml` | deployed | Secret с кредами тестовой БД |
| `configMap.yml` | deployed | ConfigMap с именем БД (`main`) |

### prod/

| Файл | Статус | Комментарий |
| --- | --- | --- |
| `deploy.yaml` | target | Deployment `postgres-prod`, `postgres:18.3` (pinned), probes, securityContext, initContainer, limits 2CPU/3.5Gi |
| `postgres-conf.yaml` | target | ConfigMap `postgres-prod-config` — тюнинг под 4GB VPS (shared_buffers=1GB, aggressive autovacuum) |
| `pv-pvc.yaml` | target | PV/PVC 50Gi, local-storage `/root/postgres-data` |
| `service.yaml` | target | ClusterIP:5432 |
| `configmap.yaml` | target | ConfigMap с именем БД (`main`) |
| `secret.yaml` | target | **Заглушка** — заменить base64-креды перед деплоем |

## Среды

### test (текущий кластер)

- **Образ**: `postgres:18` (без точной фиксации минорной версии)
- **Ресурсы**: requests 2Gi/500m, limits 12Gi/4CPU
- **Диск**: 20Gi local-storage на `/mnt/storage/`
- **Назначение**: тестовая БД для разработки

### prod (VPS 2CPU / 4GB / 80GB)

- **Образ**: `postgres:18.3` (зафиксирована точная версия)
- **Ресурсы**: requests 1Gi/500m, limits 3.5Gi/2CPU
- **Диск**: 50Gi local-storage на `/root/postgres-data` (~30Gi остаётся на систему)
- **Назначение**: авторизация + автопостер
- **postgresql.conf**: тюнинг под 4GB — `shared_buffers=1GB`, `effective_cache_size=2560MB`, агрессивный autovacuum для массовых DELETE

## Перед деплоем (prod)

1. Создать директорию на VPS: `mkdir -p /root/postgres-data`
2. Создать секрет (см. ниже)
3. Убедиться, что namespace `databases` существует: `kubectl create ns databases --dry-run=client -o yaml | kubectl apply -f -`
4. Убедиться, что StorageClass `local-storage` создан
5. Применить в порядке: secret → `configmap.yaml` → `postgres-conf.yaml` → `pv-pvc.yaml` → `service.yaml` → `deploy.yaml`

### Создание секрета

**Вариант 1** — через `kubectl` (рекомендуемый, ничего не попадает в git):

```bash
kubectl create secret generic postgres-prod-secret \
  -n databases \
  --from-literal=postgres-root-username='postgres' \
  --from-literal=postgres-root-password='$(openssl rand -base64 32)'
```

**Вариант 2** — генерация пароля вручную и применение файла:

```bash
# 1. Сгенерировать пароль
openssl rand -base64 32

# 2. Закодировать username и password в base64
echo -n 'postgres' | base64
echo -n '<сгенерированный_пароль>' | base64

# 3. Подставить значения в prod/secret.yaml вместо CHANGE_ME
# 4. Применить
kubectl apply -f prod/secret.yaml

# 5. ВАЖНО: откатить secret.yaml, чтобы не закоммитить реальные креды
git checkout -- prod/secret.yaml
```

**Проверка** — убедиться, что секрет создан:

```bash
kubectl get secret postgres-prod-secret -n databases -o jsonpath='{.data}' | jq
```

## Принципы

- Секреты в `prod/secret.yaml` — заглушки; реальные креды применяются отдельно, никогда не коммитятся в git
- Перед `kubectl apply` конфигов — всегда `kubectl diff` для сверки с кластером
- ConfigMap и Secret на кластере могут содержать ручные hot-fix правки; их нельзя затирать вслепую
