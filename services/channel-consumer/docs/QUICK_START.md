# Quick Start Guide - Batch Processing

Быстрое руководство по запуску и тестированию пакетной обработки сообщений.

## Предварительные требования

- Docker и Docker Compose
- Python 3.11+
- PostgreSQL (или используйте Docker Compose)
- Kafka (или используйте Docker Compose)

## Шаг 1: Настройка окружения

### Через Docker Compose (рекомендуется)

```bash
# Запустить все сервисы (PostgreSQL, Kafka, Zookeeper)
docker compose up -d

# Проверить статус
docker compose ps
```

### Локально

Создайте `.env` файл в корне проекта:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=message_db

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=messages
KAFKA_GROUP_ID=message-consumer-group

# Batch Processing
BATCH_SIZE=100
BATCH_TIMEOUT=5.0

# Application
LOG_LEVEL=INFO
```

## Шаг 2: Установка зависимостей

```bash
# Установить проект в режиме разработки
pip install -e .

# Или с uv (быстрее)
uv pip install -e .
```

## Шаг 3: Создание таблиц БД

```bash
# Применить миграции Piccolo
piccolo migrations forwards message

# Или создать таблицы напрямую
python -c "
import asyncio
from src.Containers.message.model.message_model import create_tables
asyncio.run(create_tables())
"
```

## Шаг 4: Запуск Kafka Worker

```bash
# В отдельном терминале
python -m src.Ship.tasks.kafka_worker

# Или через uvicorn (если используете web интерфейс)
uvicorn src.Bootstrap:app --reload
```

Вы должны увидеть:

```
INFO:src.Ship.tasks.kafka_worker:Kafka consumer started for topic: messages (batch_size=100, batch_timeout=5.0s)
```

## Шаг 5: Отправка тестовых сообщений

### Вариант 1: Простой тест (100 сообщений)

```bash
python scripts/send_test_messages.py
```

### Вариант 2: Больше сообщений

```bash
# Отправить 500 сообщений
python scripts/send_test_messages.py --count 500

# С задержкой между сообщениями
python scripts/send_test_messages.py --count 200 --delay 0.05
```

### Вариант 3: Benchmark (с измерением производительности)

```bash
# Отправить 1000 сообщений и замерить производительность
python scripts/benchmark_batch_processing.py --messages 1000

# Больше сообщений для стресс-теста
python scripts/benchmark_batch_processing.py --messages 5000 --batch-size 500
```

## Шаг 6: Проверка результатов

### Через psql

```bash
# Подключиться к БД
psql -h localhost -U postgres -d message_db

# Проверить количество сообщений
SELECT COUNT(*) FROM messages;

# Посмотреть последние 10 сообщений
SELECT id, message_id, topic, partition, offset, received_at 
FROM messages 
ORDER BY received_at DESC 
LIMIT 10;

# Статистика по минутам
SELECT 
    DATE_TRUNC('minute', received_at) as minute,
    COUNT(*) as messages_count
FROM messages 
GROUP BY minute 
ORDER BY minute DESC 
LIMIT 10;
```

### Через Python

```python
import asyncio
from src.Containers.message.model.message_model import Message

async def check_stats():
    total = await Message.count()
    print(f"Total messages: {total}")
    
    recent = await Message.select().order_by(
        Message.received_at, 
        ascending=False
    ).limit(5)
    
    for msg in recent:
        print(f"- {msg['message_id']}: {msg['payload']}")

asyncio.run(check_stats())
```

## Мониторинг в реальном времени

### Логи worker

```bash
# С подробным выводом
LOG_LEVEL=DEBUG python -m src.Ship.tasks.kafka_worker

# Только ошибки
LOG_LEVEL=ERROR python -m src.Ship.tasks.kafka_worker
```

Типичный вывод при работе:

```
INFO:src.Ship.tasks.kafka_worker:Kafka consumer started for topic: messages (batch_size=100, batch_timeout=5.0s)
INFO:src.Ship.tasks.kafka_worker:Flushed batch: 100 messages inserted (out of 100 received)
INFO:src.Ship.tasks.kafka_worker:Flushed batch: 100 messages inserted (out of 100 received)
INFO:src.Ship.tasks.kafka_worker:Flushed batch: 50 messages inserted (out of 50 received)
```

### Мониторинг Kafka

```bash
# Проверить offset consumer group
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group message-consumer-group --describe

# Количество сообщений в топике
kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic messages
```

## Примеры сценариев

### Сценарий 1: Тест высокой пропускной способности

```bash
# 1. Настроить для высокой пропускной способности
export BATCH_SIZE=500
export BATCH_TIMEOUT=10.0

# 2. Запустить worker
python -m src.Ship.tasks.kafka_worker &

# 3. Отправить много сообщений
python scripts/send_test_messages.py --count 5000

# 4. Наблюдать в логах большие батчи (500 сообщений)
```

### Сценарий 2: Тест низкой латентности

```bash
# 1. Настроить для низкой латентности
export BATCH_SIZE=50
export BATCH_TIMEOUT=1.0

# 2. Запустить worker
python -m src.Ship.tasks.kafka_worker &

# 3. Отправлять сообщения с задержкой
python scripts/send_test_messages.py --count 200 --delay 0.1

# 4. Наблюдать частые маленькие батчи
```

### Сценарий 3: Тест таймаута

```bash
# 1. Запустить worker с defaults
python -m src.Ship.tasks.kafka_worker &

# 2. Отправить несколько сообщений
python scripts/send_test_messages.py --count 30

# 3. Подождать ~5 секунд
# 4. Увидеть flush по таймауту (30 сообщений, хотя BATCH_SIZE=100)
```

## Тестирование

```bash
# Запустить все тесты
pytest src/Containers/message/tests/

# Только тесты батчинга
pytest src/Containers/message/tests/test_batch_insert_task.py -v
pytest src/Containers/message/tests/test_batch_store_action.py -v

# С покрытием кода
pytest --cov=src/Containers/message --cov-report=html

# Открыть отчет о покрытии
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

## Troubleshooting

### Проблема: Worker не получает сообщения

**Решение:**
```bash
# Проверить, запущен ли Kafka
docker compose ps

# Проверить топик
kafka-topics.sh --bootstrap-server localhost:9092 --list

# Проверить переменные окружения
echo $KAFKA_BOOTSTRAP_SERVERS
echo $KAFKA_TOPIC
```

### Проблема: Сообщения не попадают в БД

**Решение:**
```bash
# Проверить подключение к БД
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1"

# Проверить таблицу
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\dt"

# Проверить логи с DEBUG уровнем
LOG_LEVEL=DEBUG python -m src.Ship.tasks.kafka_worker
```

### Проблема: Высокая задержка

**Решение:**
```env
# Уменьшить размер батча и таймаут
BATCH_SIZE=50
BATCH_TIMEOUT=1.0
```

### Проблема: Высокая нагрузка на БД

**Решение:**
```env
# Увеличить размер батча
BATCH_SIZE=300
BATCH_TIMEOUT=5.0
```

## Дополнительные ресурсы

- **[BATCH_PROCESSING.md](./BATCH_PROCESSING.md)** - Полная техническая документация
- **[CONFIGURATION.md](./CONFIGURATION.md)** - Детальная настройка и тюнинг
- **[../README.md](../README.md)** - Общая информация о проекте

## Следующие шаги

1. ✅ Базовая настройка работает
2. 📊 Запустите benchmark для оценки производительности
3. ⚙️ Настройте `BATCH_SIZE` и `BATCH_TIMEOUT` под свои нужды
4. 🔍 Настройте мониторинг (Prometheus, Grafana)
5. 🚀 Деплой в production

---

Остались вопросы? Смотрите полную документацию или создайте issue в репозитории.

