# Quick Start - Telegram Channels Processing

Быстрое руководство по запуску и тестированию обработки Telegram каналов.

## Предварительные требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)
- Kafka (запускается через Docker Compose)

## Шаг 1: Запуск инфраструктуры

### Запуск Kafka и PostgreSQL

```bash
# Запустить все сервисы
docker compose up -d

# Проверить статус
docker compose ps
```

Сервисы:
- **PostgreSQL**: `localhost:5432`
- **Kafka**: `localhost:9092`
- **Zookeeper**: `localhost:2181`
- **Application**: `localhost:8000`

## Шаг 2: Проверка работы

### Проверка health endpoint

```bash
curl http://localhost:8000/
# Ожидаемый ответ: {"status": "ok"}
```

### Проверка логов

```bash
# Логи приложения
docker compose logs -f app

# Должны увидеть:
# INFO: Kafka consumer started for topic: tg_channels (batch_size=100, batch_timeout=5.0s)
```

## Шаг 3: Отправка тестовых данных

### Установка Kafka Python клиента (если нужно)

```bash
pip install kafka-python
```

### Запуск тестового скрипта

```bash
python scripts/send_test_channels.py
```

Скрипт отправит:
- 10 тестовых каналов
- 1 обновление существующего канала (демо upsert)
- 3 невалидных канала (демо валидации)

### Ожидаемый вывод

```
INFO: Connected to Kafka at localhost:9092
INFO: Sending 10 test channels to topic 'tg_channels'...
INFO: [1/10] Sent channel_id=100000001 to partition 0 at offset 0
...
INFO: Successfully sent 10 test channels!
INFO: Sent UPDATE for channel_id=100000001 to partition 0 at offset 10
INFO: Invalid channels sent. Check logs for validation errors.
✅ All test data sent successfully!
```

## Шаг 4: Проверка результатов

### Проверка логов приложения

```bash
docker compose logs app | grep "Flushed channel batch"
```

Ожидаемый вывод:
```
INFO: Flushed channel batch: 10 upserted, 10 tables created, 0 errors (out of 10 received)
INFO: Flushed channel batch: 1 upserted, 1 tables created, 0 errors (out of 1 received)
INFO: Flushed channel batch: 0 upserted, 0 tables created, 3 errors (out of 3 received)
```

### Проверка базы данных

```bash
# Подключиться к PostgreSQL
docker compose exec postgres psql -U postgres -d telegram_channels

# Проверить каналы
SELECT channel_id, channel_username, channel_title, members_count 
FROM tg_channels 
ORDER BY channel_id;

# Проверить созданные таблицы
SELECT tablename 
FROM pg_tables 
WHERE tablename LIKE 'tg_channel_%_messages' 
ORDER BY tablename;

# Проверить конкретный канал
SELECT * FROM tg_channels WHERE channel_id = 100000001;
```

Ожидаемый результат:
```
 channel_id  | channel_username          | channel_title              | members_count 
-------------+---------------------------+----------------------------+---------------
 100000001   | test_channel_1_updated    | Test Channel 1 - UPDATED   | 5000
 100000002   | test_channel_2            | Test Channel 2             | 2000
 ...
```

### Проверка upsert механизма

```sql
-- Проверить что created_at не изменился после update
SELECT 
    channel_id, 
    channel_username, 
    members_count,
    created_at,
    updated_at
FROM tg_channels 
WHERE channel_id = 100000001;
```

Вы должны увидеть:
- `channel_username` = "test_channel_1_updated" (обновлено)
- `members_count` = 5000 (обновлено с 1000)
- `created_at` < `updated_at` (created_at не изменился)

## Шаг 5: Отправка собственных данных

### Через Python

```python
import json
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Ваш канал
channel = {
    "channel_id": 123456789,
    "channel_username": "my_channel",
    "channel_title": "My Test Channel",
    "channel_type": "channel",
    "members_count": 1000,
    "metadata": {
        "description": "My channel description"
    },
    "is_active": True
}

producer.send('tg_channels', channel)
producer.flush()
producer.close()
```

### Через kafka-console-producer

```bash
# Подключиться к Kafka контейнеру
docker compose exec kafka bash

# Отправить сообщение
kafka-console-producer --broker-list localhost:9092 --topic tg_channels

# Вставить JSON (одной строкой):
{"channel_id": 987654321, "channel_username": "test", "channel_title": "Test"}

# Ctrl+C для выхода
```

## Шаг 6: Мониторинг

### Логи в реальном времени

```bash
docker compose logs -f app
```

### Метрики Kafka

```bash
# Проверить offset consumer group
docker compose exec kafka kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --group tg-channel-consumer \
    --describe
```

### Статистика базы данных

```sql
-- Количество каналов
SELECT COUNT(*) FROM tg_channels;

-- Количество таблиц сообщений
SELECT COUNT(*) 
FROM pg_tables 
WHERE tablename LIKE 'tg_channel_%_messages';

-- Активные каналы
SELECT COUNT(*) FROM tg_channels WHERE is_active = true;

-- Топ каналов по подписчикам
SELECT channel_username, channel_title, members_count 
FROM tg_channels 
ORDER BY members_count DESC 
LIMIT 10;
```

## Troubleshooting

### Проблема: Kafka не запускается

```bash
# Проверить логи Kafka
docker compose logs kafka

# Перезапустить сервисы
docker compose down
docker compose up -d
```

### Проблема: Приложение не подключается к Kafka

```bash
# Проверить что Kafka доступен
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Создать топик вручную (если нужно)
docker compose exec kafka kafka-topics \
    --create \
    --topic tg_channels \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1
```

### Проблема: Данные не записываются в БД

```bash
# Проверить подключение к БД
docker compose exec postgres psql -U postgres -d telegram_channels -c "SELECT 1;"

# Проверить что таблица создана
docker compose exec postgres psql -U postgres -d telegram_channels -c "\dt tg_channels"

# Проверить логи приложения на ошибки
docker compose logs app | grep ERROR
```

### Проблема: Валидационные ошибки

Проверьте формат данных:
- `channel_id` должен быть положительным целым числом
- `members_count` (если указан) должен быть >= 0
- `metadata` (если указан) должен быть объектом

```python
# Правильный формат
{
    "channel_id": 123456789,  # ✅ Положительное число
    "members_count": 1000,    # ✅ >= 0
    "metadata": {}            # ✅ Объект
}

# Неправильный формат
{
    "channel_id": -123,       # ❌ Отрицательное
    "members_count": -100,    # ❌ Отрицательное
    "metadata": "string"      # ❌ Не объект
}
```

## Остановка сервисов

```bash
# Остановить все сервисы
docker compose down

# Остановить и удалить volumes (БД будет очищена)
docker compose down -v
```

## Следующие шаги

1. Изучите [полную документацию](TG_CHANNELS.md)
2. Настройте [конфигурацию batch processing](CONFIGURATION.md)
3. Запустите [тесты](../src/Containers/tg_channel/tests/)
4. Интегрируйте с вашим Telegram парсером

## Полезные команды

```bash
# Перезапуск только приложения
docker compose restart app

# Пересборка образа приложения
docker compose up -d --build app

# Просмотр всех контейнеров
docker compose ps -a

# Очистка логов
docker compose logs --tail=0 -f app

# Проверка использования ресурсов
docker stats
```

## Дополнительная информация

- **Документация**: [docs/TG_CHANNELS.md](TG_CHANNELS.md)
- **Архитектура**: [docs/ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)
- **Batch Processing**: [docs/BATCH_PROCESSING.md](BATCH_PROCESSING.md)
- **Конфигурация**: [docs/CONFIGURATION.md](CONFIGURATION.md)

