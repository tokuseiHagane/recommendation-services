# 🚀 Getting Started с Social Posts Consumer

Пошаговое руководство для быстрого старта с сервисами обработки постов Telegram и VK.

## 📋 Предварительные требования

Убедитесь что у вас установлены:

- ✅ **Docker** 20.10+ (`docker --version`)
- ✅ **Docker Compose** 2.0+ (`docker-compose --version`)
- ✅ **Make** (опционально, для удобных команд)
- ✅ **Запущенный Kafka кластер** (для подключения)
- ✅ **PostgreSQL базы данных** (telegram и vk)

## 🎯 Сценарий 1: Первый запуск (Production)

### Шаг 1: Клонировать репозиторий

```bash
git clone <your-repo-url>
cd Telegram-Posts-Consumers
```

### Шаг 2: Настроить переменные окружения

```bash
# Создать .env из примера
cp env.example .env

# Отредактировать .env
nano .env  # или любой другой редактор
```

**Важные переменные для изменения**:
```env
# Подключение к вашему Kafka кластеру
KAFKA_BOOTSTRAP_SERVERS=your-kafka-server:9092

# PostgreSQL для Telegram
DB_HOST=your-tg-db-host
DB_USER=your-user
DB_PASSWORD=your-secure-password
DB_NAME=telegram

# PostgreSQL для VK
VK_DB_HOST=your-vk-db-host
VK_DB_USER=your-user
VK_DB_PASSWORD=your-secure-password
VK_DB_NAME=vk

# Логирование (для production)
LOG_LEVEL=INFO
DEBUG=false
```

### Шаг 3: Создать Docker сети

```bash
# Создать сети для сервисов
docker network create tg-post-network 2>/dev/null || true
docker network create vk-post-network 2>/dev/null || true
docker network create kafka-network 2>/dev/null || true
```

### Шаг 4: Запустить сервисы

```bash
# Оба сервиса
docker-compose up -d

# Только Telegram сервис
docker-compose up -d tg-service

# Только VK сервис
docker-compose up -d vk-service
```

### Шаг 5: Проверить что всё работает

```bash
# Проверить статус сервисов
docker-compose ps

# Проверить логи Telegram сервиса
docker logs -f tg-post-consumer

# Проверить логи VK сервиса
docker logs -f vk-post-consumer
```

**Готово! 🎉** Оба сервиса запущены и слушают Kafka топики.

---

## 🔧 Сценарий 2: Development режим (с hot reload)

### Шаги 1-3: То же что в Сценарии 1

### Шаг 4: Запустить в dev mode

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

**Development режим включает**:
- ✅ Hot reload (изменения в `src/` применяются автоматически)
- ✅ Debug логирование (`LOG_LEVEL=DEBUG`)
- ✅ Автоматическое применение миграций при старте
- ✅ Volume mounting для live coding

### Разработка с hot reload

```bash
# Изменить файл Telegram контейнера
nano src/Containers/AppSection/TgPost/Tasks/SomeTask.py

# Изменить файл VK контейнера
nano src/Containers/AppSection/VkPost/Tasks/SomeTask.py

# Изменения применятся автоматически (смотри логи)
docker logs -f tg-post-consumer
docker logs -f vk-post-consumer
```

---

## 💻 Сценарий 3: Локальная разработка (без Docker)

### Telegram сервис

```bash
# 1. Установить зависимости
uv pip install -e .

# 2. Настроить переменные окружения
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_NAME=telegram

# 3. Применить миграции
piccolo migrations forwards TgPost

# 4. Запустить сервис
python -m src.BootstrapTg
```

### VK сервис

```bash
# 1. Настроить переменные окружения для VK БД
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export VK_DB_HOST=localhost
export VK_DB_PORT=5432
export VK_DB_USER=postgres
export VK_DB_PASSWORD=postgres
export VK_DB_NAME=vk

# 2. Применить миграции
PICCOLO_CONF=piccolo_conf_vk piccolo migrations forwards VkPost

# 3. Запустить сервис
python -m src.BootstrapVk
```

---

## 🧪 Сценарий 4: Запуск тестов

### Все тесты

```bash
pytest
```

### С покрытием

```bash
pytest --cov=src --cov-report=html

# Открыть HTML отчет
open htmlcov/index.html
```

### Тесты по контейнерам

```bash
# TgPost тесты
pytest src/Containers/AppSection/TgPost/Tests/ -v

# VkPost тесты
pytest src/Containers/AppSection/VkPost/Tests/ -v
```

### Интеграционные тесты с Kafka

Используйте проект **Test-Producers** для отправки тестовых сообщений:

```bash
# Перейти в директорию тестового проекта
cd /path/to/Test-Producers

# Полный интеграционный тест (Telegram + VK)
python full_integration_test.py

# Только Telegram
python full_integration_test.py --telegram-only

# Только VK
python full_integration_test.py --vk-only

# С кастомными параметрами
python full_integration_test.py \
  --tg-channels 5 \
  --tg-posts 100 \
  --vk-groups 5 \
  --vk-posts 100
```

---

## 📊 Сценарий 5: Мониторинг и отладка

### Просмотр логов

```bash
# Telegram сервис (follow mode)
docker logs -f tg-post-consumer

# VK сервис (follow mode)
docker logs -f vk-post-consumer

# Последние 100 строк без follow
docker logs --tail=100 tg-post-consumer
docker logs --tail=100 vk-post-consumer
```

### Интерактивная отладка

```bash
# Подключиться к Telegram контейнеру
docker exec -it tg-post-consumer bash

# Подключиться к VK контейнеру
docker exec -it vk-post-consumer bash

# В контейнере можно:
python  # Открыть Python REPL
piccolo migrations check TgPost  # Проверить миграции TgPost
piccolo migrations check VkPost  # Проверить миграции VkPost (в vk-service)
env | grep KAFKA  # Проверить переменные окружения
```

### Подключиться к БД

```bash
# PostgreSQL shell для Telegram
docker exec -it tg-channel-db psql -U app_user -d telegram

# PostgreSQL shell для VK
docker exec -it vk-group-db psql -U app_user -d vk

# В PostgreSQL можно:
\dt                    # Список таблиц
SELECT COUNT(*) FROM posts;
SELECT * FROM posts LIMIT 10;
```

### Мониторинг ресурсов

```bash
# Статистика контейнеров (CPU, Memory)
docker stats tg-post-consumer vk-post-consumer
```

---

## 🔄 Сценарий 6: Работа с миграциями

### Telegram миграции

```bash
# Проверить статус
docker exec tg-post-consumer piccolo migrations check TgPost

# Применить миграции
docker exec tg-post-consumer piccolo migrations forwards TgPost

# Создать новую миграцию
docker exec tg-post-consumer piccolo migrations new TgPost --auto

# Откатить миграцию
docker exec tg-post-consumer piccolo migrations backwards TgPost
```

### VK миграции

```bash
# Проверить статус
docker exec vk-post-consumer piccolo migrations check VkPost

# Применить миграции
docker exec vk-post-consumer piccolo migrations forwards VkPost

# Создать новую миграцию
docker exec vk-post-consumer piccolo migrations new VkPost --auto

# Откатить миграцию
docker exec vk-post-consumer piccolo migrations backwards VkPost
```

---

## 💾 Сценарий 7: Backup и восстановление БД

### Telegram БД

```bash
# Создать backup
docker exec tg-channel-db pg_dump -U app_user telegram > backup_telegram.sql

# Восстановить из backup
docker exec -i tg-channel-db psql -U app_user -d telegram < backup_telegram.sql
```

### VK БД

```bash
# Создать backup
docker exec vk-group-db pg_dump -U app_user vk > backup_vk.sql

# Восстановить из backup
docker exec -i vk-group-db psql -U app_user -d vk < backup_vk.sql
```

---

## 🛑 Сценарий 8: Остановка и очистка

### Остановить сервисы (данные сохраняются)

```bash
docker-compose down
```

### Остановить конкретный сервис

```bash
# Только Telegram
docker-compose stop tg-service

# Только VK
docker-compose stop vk-service
```

### Остановить и удалить volumes (⚠️ удалит все данные!)

```bash
docker-compose down -v
```

### Пересборка образов

```bash
# Остановить, пересобрать, запустить
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 🐛 Troubleshooting

### Проблема 1: Контейнер не запускается

**Симптомы**: `docker-compose ps` показывает статус Exit/Error

**Решение**:
```bash
# Проверить логи
docker logs tg-post-consumer
docker logs vk-post-consumer

# Пересобрать образ
docker-compose build --no-cache
docker-compose up -d

# Проверить переменные окружения
docker exec tg-post-consumer env
```

### Проблема 2: Не подключается к Kafka

**Симптомы**: В логах ошибки подключения к Kafka

**Решение**:
```bash
# Проверить что Kafka network существует
docker network ls | grep kafka-network

# Проверить KAFKA_BOOTSTRAP_SERVERS
docker exec tg-post-consumer env | grep KAFKA

# Проверить доступность broker
docker exec tg-post-consumer ping broker
```

### Проблема 3: Не подключается к PostgreSQL

**Симптомы**: В логах ошибки `Connection refused` или `password authentication failed`

**Решение**:
```bash
# Проверить что БД контейнеры запущены
docker ps | grep -E "(tg-channel-db|vk-group-db)"

# Проверить переменные подключения
docker exec tg-post-consumer env | grep DB_
docker exec vk-post-consumer env | grep VK_DB_

# Проверить доступность БД
docker exec tg-post-consumer pg_isready -h tg-channel-db -U app_user
docker exec vk-post-consumer pg_isready -h vk-group-db -U app_user
```

### Проблема 4: Таблицы не созданы

**Симптомы**: Ошибка `relation "posts" does not exist`

**Решение**:
```bash
# Применить миграции вручную
docker exec tg-post-consumer piccolo migrations forwards TgPost
docker exec vk-post-consumer piccolo migrations forwards VkPost
```

### Проблема 5: Out of memory

**Симптомы**: Контейнер перезапускается, в логах OOMKilled

**Решение**: Добавить memory limits в `docker-compose.yml`:
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

---

## 📚 Следующие шаги

После успешного запуска:

1. 📖 Прочитайте [DOCKER_SETUP.md](DOCKER_SETUP.md) для продвинутого использования
2. 🏗️ Изучите [Porto Architecture](specs/001-dynamic-kafka-consumers-sharded-processing/porto-structure.md)
3. 📊 Настройте мониторинг через Logfire
4. 🔧 Настройте production окружение (secrets, logging, backups)
5. 🧪 Запустите интеграционные тесты с Test-Producers

---

## 🆘 Помощь

Если возникли проблемы:

1. Проверьте логи: `docker logs tg-post-consumer` / `docker logs vk-post-consumer`
2. Проверьте [DOCKER_SETUP.md](DOCKER_SETUP.md) Troubleshooting секцию
3. Проверьте что все prerequisites установлены
4. Откройте issue в репозитории

---

**Happy Coding! 🚀**
