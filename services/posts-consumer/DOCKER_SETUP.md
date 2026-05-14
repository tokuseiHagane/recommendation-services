# 🐳 Docker Setup для Social Posts Consumer

Руководство по запуску сервисов Telegram и VK через Docker Compose.

## 📋 Предварительные требования

- Docker 20.10+
- Docker Compose 2.0+
- Запущенный Kafka кластер (подключение через kafka-network)
- PostgreSQL базы данных (telegram и vk)

## 🚀 Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd Telegram-Posts-Consumers
```

### 2. Создать .env файл

```bash
cp env.example .env
# Отредактируйте .env под свои нужды
```

### 3. Создать Docker сети

```bash
docker network create tg-post-network 2>/dev/null || true
docker network create vk-post-network 2>/dev/null || true
docker network create kafka-network 2>/dev/null || true
```

### 4. Запустить сервисы

**Production mode**:
```bash
# Оба сервиса
docker-compose up -d

# Только Telegram
docker-compose up -d tg-service

# Только VK
docker-compose up -d vk-service
```

**Development mode** (с hot reload):
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 5. Проверить статус

```bash
# Проверить логи
docker logs -f tg-post-consumer
docker logs -f vk-post-consumer

# Проверить здоровье сервисов
docker-compose ps
```

### 6. Миграции (применяются автоматически)

Если миграции не применились автоматически:

```bash
# Telegram
docker exec tg-post-consumer piccolo migrations forwards TgPost

# VK
docker exec vk-post-consumer piccolo migrations forwards VkPost
```

## 📦 Структура сервисов

### tg-service (Telegram)
| Параметр | Значение |
|----------|----------|
| **Контейнер** | `tg-post-consumer` |
| **Entry point** | `python -m src.BootstrapTg` |
| **База данных** | PostgreSQL (telegram) |
| **Kafka топики** | `tg_channels_diff`, `tg_posts_{id}` |

**Переменные окружения**:
- `KAFKA_BOOTSTRAP_SERVERS` - адрес Kafka кластера
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - настройки PostgreSQL
- `KAFKA_CHANNELS_DIFF_TOPIC` - топик для событий каналов
- `KAFKA_POSTS_TOPIC_PREFIX` - префикс топиков постов

### vk-service (VK)
| Параметр | Значение |
|----------|----------|
| **Контейнер** | `vk-post-consumer` |
| **Entry point** | `python -m src.BootstrapVk` |
| **База данных** | PostgreSQL (vk) |
| **Kafka топики** | `vk_groups_diff`, `vk_posts_{id}` |

**Переменные окружения**:
- `KAFKA_BOOTSTRAP_SERVERS` - адрес Kafka кластера
- `VK_DB_HOST`, `VK_DB_PORT`, `VK_DB_USER`, `VK_DB_PASSWORD`, `VK_DB_NAME` - настройки PostgreSQL для VK
- `KAFKA_GROUPS_DIFF_TOPIC` - топик для событий групп
- `KAFKA_POSTS_TOPIC_PREFIX` - префикс топиков постов

### Databases
| Сервис | Контейнер | База | Порт |
|--------|-----------|------|------|
| Telegram | `tg-channel-db` | telegram | 5432 |
| VK | `vk-group-db` | vk | 5432 |

## 🔧 Полезные команды

### Управление контейнерами

```bash
# Запустить все сервисы
docker-compose up -d

# Запустить конкретный сервис
docker-compose up -d tg-service
docker-compose up -d vk-service

# Остановить все сервисы
docker-compose down

# Остановить и удалить volumes (⚠️ удалит все данные!)
docker-compose down -v

# Перезапустить конкретный сервис
docker-compose restart tg-service
docker-compose restart vk-service

# Посмотреть логи
docker logs -f tg-post-consumer
docker logs -f vk-post-consumer

# Подключиться к контейнеру
docker exec -it tg-post-consumer bash
docker exec -it vk-post-consumer bash
```

### Работа с миграциями

#### Telegram (TgPost)

```bash
# Применить все миграции
docker exec tg-post-consumer piccolo migrations forwards TgPost

# Откатить последнюю миграцию
docker exec tg-post-consumer piccolo migrations backwards TgPost

# Проверить статус миграций
docker exec tg-post-consumer piccolo migrations check TgPost

# Создать новую миграцию
docker exec tg-post-consumer piccolo migrations new TgPost --auto
```

#### VK (VkPost)

```bash
# Применить все миграции
docker exec vk-post-consumer piccolo migrations forwards VkPost

# Откатить последнюю миграцию
docker exec vk-post-consumer piccolo migrations backwards VkPost

# Проверить статус миграций
docker exec vk-post-consumer piccolo migrations check VkPost

# Создать новую миграцию
docker exec vk-post-consumer piccolo migrations new VkPost --auto
```

### Работа с базой данных

#### Telegram БД

```bash
# Подключиться к PostgreSQL
docker exec -it tg-channel-db psql -U app_user -d telegram

# Выполнить SQL запрос
docker exec tg-channel-db psql -U app_user -d telegram -c "SELECT COUNT(*) FROM posts;"

# Сделать backup БД
docker exec tg-channel-db pg_dump -U app_user telegram > backup_telegram.sql

# Восстановить БД из backup
docker exec -i tg-channel-db psql -U app_user -d telegram < backup_telegram.sql
```

#### VK БД

```bash
# Подключиться к PostgreSQL
docker exec -it vk-group-db psql -U app_user -d vk

# Выполнить SQL запрос
docker exec vk-group-db psql -U app_user -d vk -c "SELECT COUNT(*) FROM posts;"

# Сделать backup БД
docker exec vk-group-db pg_dump -U app_user vk > backup_vk.sql

# Восстановить БД из backup
docker exec -i vk-group-db psql -U app_user -d vk < backup_vk.sql
```

### Debugging

```bash
# Посмотреть переменные окружения
docker exec tg-post-consumer env
docker exec vk-post-consumer env

# Проверить Python packages
docker exec tg-post-consumer pip list

# Запустить Python REPL
docker exec -it tg-post-consumer python
docker exec -it vk-post-consumer python

# Проверить подключение к Kafka
docker exec tg-post-consumer python -c "
from aiokafka import AIOKafkaConsumer
import asyncio

async def check():
    consumer = AIOKafkaConsumer(bootstrap_servers='broker:29092')
    await consumer.start()
    print('Kafka OK')
    await consumer.stop()

asyncio.run(check())
"
```

### Мониторинг

```bash
# Статистика ресурсов
docker stats tg-post-consumer vk-post-consumer

# Проверить здоровье
docker-compose ps

# Инспектировать контейнер
docker inspect tg-post-consumer
docker inspect vk-post-consumer
```

## 🧪 Тестирование

### Unit/Integration тесты

```bash
# Запустить тесты внутри контейнера (Telegram)
docker exec tg-post-consumer pytest src/Containers/AppSection/TgPost/Tests/ -v

# Запустить тесты внутри контейнера (VK)
docker exec vk-post-consumer pytest src/Containers/AppSection/VkPost/Tests/ -v

# С покрытием
docker exec tg-post-consumer pytest --cov=src/Containers/AppSection/TgPost --cov-report=html
docker exec vk-post-consumer pytest --cov=src/Containers/AppSection/VkPost --cov-report=html
```

### Интеграционные тесты с Kafka

Используйте **Test-Producers** проект для отправки тестовых сообщений:

```bash
# Перейти в директорию
cd /path/to/Test-Producers

# Полный интеграционный тест
python full_integration_test.py

# Только Telegram
python full_integration_test.py --telegram-only

# Только VK
python full_integration_test.py --vk-only
```

## 🐛 Troubleshooting

### Проблема: Контейнер не запускается

**Решение**:
```bash
# Проверить логи
docker logs tg-post-consumer
docker logs vk-post-consumer

# Пересобрать образ
docker-compose build --no-cache
docker-compose up -d
```

### Проблема: Не подключается к Kafka

**Решение**:
```bash
# Проверить что Kafka network существует
docker network ls | grep kafka-network

# Проверить что broker доступен
docker exec tg-post-consumer ping broker

# Проверить переменную KAFKA_BOOTSTRAP_SERVERS
docker exec tg-post-consumer env | grep KAFKA
```

### Проблема: Не подключается к PostgreSQL

**Решение**:
```bash
# Проверить что БД контейнеры запущены
docker ps | grep -E "(tg-channel-db|vk-group-db)"

# Проверить hostname и credentials
docker exec tg-post-consumer env | grep DB_
docker exec vk-post-consumer env | grep VK_DB_

# Проверить доступность
docker exec tg-post-consumer pg_isready -h tg-channel-db -U app_user
```

### Проблема: Миграции не применяются

**Решение**:
```bash
# Применить вручную
docker exec tg-post-consumer piccolo migrations forwards TgPost
docker exec vk-post-consumer piccolo migrations forwards VkPost

# Проверить подключение к БД
docker exec tg-post-consumer python -c "
from src.Ship.utils.db import get_db_engine
import asyncio

async def check():
    db = get_db_engine()
    print('DB OK')

asyncio.run(check())
"
```

### Проблема: Таблицы не существуют

**Решение**:
```bash
# Проверить статус миграций
docker exec tg-post-consumer piccolo migrations check TgPost
docker exec vk-post-consumer piccolo migrations check VkPost

# Применить миграции
docker exec tg-post-consumer piccolo migrations forwards TgPost
docker exec vk-post-consumer piccolo migrations forwards VkPost

# Проверить что таблицы созданы
docker exec tg-channel-db psql -U app_user -d telegram -c "\dt"
docker exec vk-group-db psql -U app_user -d vk -c "\dt"
```

### Проблема: Out of memory

**Решение**: Добавить memory limits в docker-compose.yml:
```yaml
services:
  tg-service:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
  vk-service:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
```

## 🔒 Production рекомендации

1. **Используйте .env файл** для чувствительных данных (не коммитьте его!)
2. **Настройте логирование** через volume mount или log driver
3. **Используйте secrets** для паролей в production:
   ```yaml
   secrets:
     db_password:
       external: true
   ```
4. **Настройте health checks** для автоматического рестарта
5. **Используйте конкретные версии** образов (не `latest`)
6. **Настройте мониторинг** через Prometheus/Grafana
7. **Backup БД** регулярно (daily cron job)
8. **Разделите ресурсы** для Telegram и VK сервисов

## 📊 Monitoring & Observability

Сервисы используют **Logfire** для observability:

```bash
# Посмотреть метрики в логах
docker logs tg-post-consumer | grep "metric"
docker logs vk-post-consumer | grep "metric"

# Проверить Logfire dashboard (если настроен)
# https://logfire.pydantic.dev/
```

## 🔗 Полезные ссылки

- [Docker Compose документация](https://docs.docker.com/compose/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [Piccolo ORM документация](https://piccolo-orm.readthedocs.io/)
- [AIOKafka документация](https://aiokafka.readthedocs.io/)

## 📝 Примечания

- Volumes персистентны между перезапусками
- Hot reload работает только в dev mode
- Kafka должен быть запущен отдельно (external network)
- Логи сохраняются через Docker logging driver
- Каждый сервис (TgPost/VkPost) имеет свою БД и топики

---

**Created**: 2025-11-02  
**Updated**: 2026-02-01  
**Services**: TgPost (Telegram), VkPost (VK) Dynamic Kafka Consumers
