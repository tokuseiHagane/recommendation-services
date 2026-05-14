# 🐋 Настройка Docker Compose

Проект разделен на два docker-compose файла для гибкости развертывания:

1. **docker-compose.kafka.yml** - Kafka кластер (Zookeeper + Broker)
2. **docker-compose.yml** - Приложение и PostgreSQL

## 📦 Структура

```
.
├── docker-compose.kafka.yml  # Kafka инфраструктура
├── docker-compose.yml        # Приложение + PostgreSQL
├── Dockerfile                # Образ приложения
└── src/                      # Исходный код
```

## 🚀 Быстрый старт

### Вариант 1: Запуск всего (рекомендуется)

```bash
# Запустить Kafka кластер
docker compose -f docker-compose.kafka.yml up -d

# Подождать пока Kafka запустится (10-15 секунд)
sleep 15

# Запустить приложение
docker compose up -d

# Проверить статус
docker compose ps
docker compose -f docker-compose.kafka.yml ps
```

### Вариант 2: Одной командой

```bash
# Запустить всё одновременно
docker compose -f docker-compose.kafka.yml -f docker-compose.yml up -d
```

## 📋 Подробные инструкции

### 1. Запуск Kafka кластера

```bash
# Запустить
docker compose -f docker-compose.kafka.yml up -d

# Проверить логи
docker compose -f docker-compose.kafka.yml logs -f

# Проверить статус
docker compose -f docker-compose.kafka.yml ps
```

**Ожидаемый вывод:**
```
NAME        IMAGE                             STATUS    PORTS
broker      confluentinc/cp-kafka:7.3.0      Up        0.0.0.0:9092->9092/tcp, 0.0.0.0:29092->29092/tcp
zookeeper   confluentinc/cp-zookeeper:7.3.0  Up        0.0.0.0:2181->2181/tcp
```

### 2. Проверка Kafka

```bash
# Список топиков
docker exec -it broker kafka-topics --bootstrap-server localhost:9092 --list

# Создать тестовый топик
docker exec -it broker kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --topic messages \
  --partitions 3 \
  --replication-factor 1

# Проверить health check
docker exec -it broker kafka-broker-api-versions --bootstrap-server localhost:9092
```

### 3. Запуск приложения

```bash
# Запустить
docker compose up -d

# Проверить логи
docker compose logs -f app

# Проверить статус
docker compose ps
```

**Ожидаемый вывод:**
```
NAME             IMAGE                    STATUS    PORTS
tg-channel-consumer    tg-channel-consumer    Up        0.0.0.0:8000->8000/tcp
postgres_kafka_db postgres:18-alpine      Up        0.0.0.0:5432->5432/tcp
```

### 4. Проверка работы

```bash
# API health check
curl http://localhost:8000/

# Получить сообщения
curl http://localhost:8000/messages

# Проверить подключение к Kafka в логах
docker logs tg-channel-consumer | grep "Kafka consumer started"
```

## 🔌 Сети Docker

Проект использует две Docker сети:

### kafka-network (внешняя)
- Создается при запуске `docker-compose.kafka.yml`
- Используется для связи Kafka компонентов
- Приложение подключается к ней для доступа к Kafka

### porto-network (внутренняя)
- Создается при запуске `docker-compose.yml`
- Используется для связи приложения и PostgreSQL

**Схема подключений:**
```
┌─────────────────────────────────────────┐
│        kafka-network (external)         │
│  ┌──────────┐      ┌────────────┐      │
│  │ Zookeeper│◄────►│   Broker   │      │
│  └──────────┘      └─────▲──────┘      │
│                           │              │
│                           │              │
│  ┌────────────────────────┼──────────┐  │
│  │  porto-network         │          │  │
│  │    ┌──────────┐    ┌───┴────┐    │  │
│  │    │   App    │◄──►│  Kafka │    │  │
│  │    └────┬─────┘    └────────┘    │  │
│  │         │                         │  │
│  │         ▼                         │  │
│  │   ┌──────────┐                   │  │
│  │   │ Postgres │                   │  │
│  │   └──────────┘                   │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## 🛑 Остановка сервисов

### Остановить только приложение
```bash
docker compose down
```

### Остановить только Kafka
```bash
docker compose -f docker-compose.kafka.yml down
```

### Остановить всё
```bash
docker compose down
docker compose -f docker-compose.kafka.yml down
```

### Остановить и удалить volumes (полная очистка)
```bash
docker compose down -v
docker compose -f docker-compose.kafka.yml down -v
```

## 🔄 Перезапуск

### Перезапустить приложение
```bash
docker compose restart app
```

### Перезапустить Kafka
```bash
docker compose -f docker-compose.kafka.yml restart broker
```

### Пересобрать приложение
```bash
docker compose build --no-cache app
docker compose up -d app
```

## 📊 Мониторинг

### Логи в реальном времени

```bash
# Все сервисы приложения
docker compose logs -f

# Только приложение
docker compose logs -f app

# Только Kafka
docker compose -f docker-compose.kafka.yml logs -f broker

# Только Zookeeper
docker compose -f docker-compose.kafka.yml logs -f zookeeper

# Только PostgreSQL
docker compose logs -f postgres
```

### Использование ресурсов

```bash
# Статистика контейнеров
docker stats

# Размер volumes
docker system df -v

# Детали конкретного контейнера
docker inspect tg-channel-consumer
```

## 🧪 Тестирование

### Отправка тестового сообщения в Kafka

```bash
# Через kafka-console-producer
echo '{"event": "test", "data": "Hello Kafka!"}' | \
  docker exec -i broker kafka-console-producer \
  --broker-list localhost:9092 \
  --topic messages

# Проверить что приложение получило сообщение
docker logs tg-channel-consumer | tail -20
curl http://localhost:8000/messages
```

### Чтение сообщений из топика

```bash
# Прочитать последние сообщения
docker exec -it broker kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic messages \
  --from-beginning \
  --max-messages 10
```

## 🔧 Troubleshooting

### Приложение не может подключиться к Kafka

**Проблема:**
```
ERROR: Unable connect to "broker:29092"
```

**Решение:**
```bash
# 1. Проверить что Kafka запущен
docker compose -f docker-compose.kafka.yml ps

# 2. Проверить сеть kafka-network
docker network ls | grep kafka-network

# 3. Если сеть не существует, пересоздать Kafka
docker compose -f docker-compose.kafka.yml down
docker compose -f docker-compose.kafka.yml up -d

# 4. Перезапустить приложение
docker compose restart app
```

### Kafka не запускается

**Проблема:**
```
broker exited with code 1
```

**Решение:**
```bash
# Посмотреть логи
docker compose -f docker-compose.kafka.yml logs broker

# Очистить volumes и перезапустить
docker compose -f docker-compose.kafka.yml down -v
docker compose -f docker-compose.kafka.yml up -d
```

### База данных не доступна

**Проблема:**
```
ERROR: could not connect to server: Connection refused
```

**Решение:**
```bash
# Проверить статус PostgreSQL
docker compose ps postgres

# Проверить логи
docker compose logs postgres

# Пересоздать контейнер
docker compose restart postgres
```

### Порты заняты

**Проблема:**
```
Error: port is already allocated
```

**Решение:**
```bash
# Найти процесс использующий порт
# Windows:
netstat -ano | findstr :9092
# Linux/Mac:
lsof -i :9092

# Остановить конфликтующий сервис или изменить порт в docker-compose
```

## 🔄 Обновление

### Обновить образы

```bash
# Kafka
docker compose -f docker-compose.kafka.yml pull
docker compose -f docker-compose.kafka.yml up -d

# Приложение
docker compose pull
docker compose up -d
```

### Обновить код приложения

```bash
# Пересобрать образ
docker compose build app

# Перезапустить с новым образом
docker compose up -d app
```

## 🎯 Production рекомендации

### Для production использовать:

1. **Отдельные volumes для данных:**
```yaml
volumes:
  kafka-data:
    driver: local
    driver_opts:
      type: none
      device: /mnt/kafka-data
      o: bind
```

2. **Health checks:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/"]
  interval: 30s
  timeout: 10s
  retries: 3
```

3. **Resource limits:**
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

4. **Restart policies:**
```yaml
restart: unless-stopped
```

## 📝 Переменные окружения

### Kafka кластер (docker-compose.kafka.yml)

Без дополнительных переменных - всё настроено.

### Приложение (docker-compose.yml)

Можно переопределить через `.env` файл:

```bash
# .env
ENV=production
DEBUG=false
LOG_LEVEL=WARNING
BATCH_SIZE=500
BATCH_TIMEOUT=10.0

DB_HOST=postgres
DB_PORT=5432
DB_USER=app_user
DB_PASSWORD=secure_password_here
DB_NAME=app_db

KAFKA_BOOTSTRAP_SERVERS=broker:29092
KAFKA_TOPIC=messages
KAFKA_GROUP_ID=message-consumer-group
```

## ✅ Checklist для запуска

- [ ] Docker и Docker Compose установлены
- [ ] Порты 9092, 2181, 8000, 5432 свободны
- [ ] Достаточно места на диске (минимум 5GB)
- [ ] Запущен `docker-compose.kafka.yml`
- [ ] Kafka готов к работе (проверить логи)
- [ ] Запущен `docker-compose.yml`
- [ ] Приложение подключилось к Kafka
- [ ] API доступно на http://localhost:8000
- [ ] Отправлено тестовое сообщение
- [ ] Сообщение попало в базу данных

---

**Готово! Все сервисы запущены и работают. 🎉**

