# Getting Started - Telegram Channels Consumer

Быстрое руководство для начала работы с сервисом обработки Telegram каналов.

## 📋 Предварительные требования

- Docker и Docker Compose
- Python 3.11+ (опционально, для локальной разработки)
- Git

## 🚀 Запуск за 5 минут

### Шаг 1: Клонирование репозитория

```bash
git clone <repository-url>
cd Telegram-Channel-Consumer
```

### Шаг 2: Запуск сервисов

```bash
# Запустить все сервисы (Kafka, PostgreSQL, Application)
docker compose up -d

# Проверить статус
docker compose ps
```

Ожидаемый вывод:
```
NAME                  STATUS
kafka                 Up
postgres              Up
zookeeper             Up
app                   Up
```

### Шаг 3: Проверка работы

```bash
# Health check
curl http://localhost:8000/
# Ожидается: {"status": "ok"}

# Проверка логов
docker compose logs -f app
# Должно быть: "Kafka consumer started for topic: tg_channels"
```

### Шаг 4: Отправка тестовых данных

```bash
# Установить Kafka Python клиент (если нужно)
pip install kafka-python

# Запустить тестовый скрипт
python scripts/send_test_channels.py
```

### Шаг 5: Проверка результатов

```bash
# Проверить логи обработки
docker compose logs app | grep "Flushed channel batch"

# Подключиться к базе данных
docker compose exec postgres psql -U postgres -d telegram_channels

# Проверить данные
SELECT channel_id, channel_username, channel_title, members_count 
FROM tg_channels 
ORDER BY channel_id;
```

## ✅ Что должно работать

После выполнения всех шагов:

1. ✅ Kafka consumer работает и читает топик `tg_channels`
2. ✅ 10 тестовых каналов записаны в базу данных
3. ✅ 10 таблиц сообщений созданы (`tg_channel_*_messages`)
4. ✅ Upsert работает (канал 100000001 обновлен)
5. ✅ Валидация работает (3 невалидных канала пропущены)

## 📊 Проверка данных

### SQL запросы

```sql
-- Подключение к БД
docker compose exec postgres psql -U postgres -d telegram_channels

-- Количество каналов
SELECT COUNT(*) FROM tg_channels;
-- Ожидается: 10

-- Список каналов
SELECT channel_id, channel_username, members_count 
FROM tg_channels 
ORDER BY channel_id;

-- Проверка upsert (канал должен быть обновлен)
SELECT channel_username, members_count, created_at, updated_at 
FROM tg_channels 
WHERE channel_id = 100000001;
-- Ожидается: username=test_channel_1_updated, members=5000

-- Список таблиц сообщений
SELECT tablename 
FROM pg_tables 
WHERE tablename LIKE 'tg_channel_%_messages' 
ORDER BY tablename;
-- Ожидается: 10 таблиц
```

## 🔧 Конфигурация

### Переменные окружения

Создайте файл `.env` (или используйте значения по умолчанию):

```env
# Database
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=telegram_channels

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_GROUP_ID=tg-channel-consumer

# Batch Processing
BATCH_SIZE=100
BATCH_TIMEOUT=5.0

# Application
LOG_LEVEL=INFO
```

### Настройка производительности

Для высокой пропускной способности:
```env
BATCH_SIZE=500
BATCH_TIMEOUT=10.0
```

Для низкой задержки:
```env
BATCH_SIZE=50
BATCH_TIMEOUT=1.0
```

## 📝 Отправка собственных данных

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
    "channel_title": "My Channel",
    "channel_type": "channel",
    "members_count": 1000,
    "is_active": True
}

producer.send('tg_channels', channel)
producer.flush()
producer.close()

print("✅ Channel sent!")
```

### Через Kafka CLI

```bash
# Войти в Kafka контейнер
docker compose exec kafka bash

# Запустить producer
kafka-console-producer --broker-list localhost:9092 --topic tg_channels

# Вставить JSON (одной строкой):
{"channel_id": 987654321, "channel_username": "test", "channel_title": "Test Channel"}

# Ctrl+C для выхода
```

## 🐛 Troubleshooting

### Проблема: Kafka не запускается

```bash
# Проверить логи
docker compose logs kafka

# Перезапустить
docker compose restart kafka

# Если не помогает - полный перезапуск
docker compose down
docker compose up -d
```

### Проблема: База данных не доступна

```bash
# Проверить статус
docker compose ps postgres

# Проверить подключение
docker compose exec postgres psql -U postgres -c "SELECT 1;"

# Пересоздать базу
docker compose down -v
docker compose up -d
```

### Проблема: Приложение не обрабатывает сообщения

```bash
# Проверить логи на ошибки
docker compose logs app | grep ERROR

# Проверить что топик создан
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Создать топик вручную
docker compose exec kafka kafka-topics \
    --create \
    --topic tg_channels \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1
```

### Проблема: Валидационные ошибки

Проверьте формат данных:
```json
{
    "channel_id": 123456789,     // ✅ Положительное число
    "channel_username": "test",  // ✅ Строка (@ удалится автоматически)
    "members_count": 1000        // ✅ >= 0
}
```

Неправильный формат:
```json
{
    "channel_id": -123,          // ❌ Отрицательное
    "members_count": -100        // ❌ Отрицательное
}
```

## 📚 Дополнительная документация

### Основная
- **[TG_CHANNELS.md](docs/TG_CHANNELS.md)** - Полное руководство
- **[QUICK_START_TG_CHANNELS.md](docs/QUICK_START_TG_CHANNELS.md)** - Детальный quick start
- **[TG_CHANNELS_SUMMARY.md](TG_CHANNELS_SUMMARY.md)** - Краткий обзор

### Техническая
- **[IMPLEMENTATION_SUMMARY_TG_CHANNELS.md](docs/IMPLEMENTATION_SUMMARY_TG_CHANNELS.md)** - Детали реализации
- **[BATCH_PROCESSING.md](docs/BATCH_PROCESSING.md)** - Batch processing
- **[CONFIGURATION.md](docs/CONFIGURATION.md)** - Конфигурация

### Разработка
- **[Porto Spec Kit](spec-kit/)** - Porto архитектура
- **[CHANGELOG.md](CHANGELOG.md)** - История изменений

## 🧪 Запуск тестов

```bash
# Все тесты
pytest src/Containers/tg_channel/tests/

# С покрытием
pytest src/Containers/tg_channel/tests/ --cov=src.Containers.tg_channel

# Конкретный тест
pytest src/Containers/tg_channel/tests/test_batch_upsert_task.py -v
```

## 🛑 Остановка сервисов

```bash
# Остановить все сервисы
docker compose down

# Остановить и удалить volumes (очистить БД)
docker compose down -v

# Остановить только приложение
docker compose stop app
```

## 🔄 Обновление и перезапуск

```bash
# Пересобрать образ приложения
docker compose up -d --build app

# Перезапустить все сервисы
docker compose restart

# Просмотр логов
docker compose logs -f
```

## 📞 Следующие шаги

1. ✅ Сервис запущен и работает
2. ✅ Тестовые данные обработаны
3. 📖 Изучите [полную документацию](docs/TG_CHANNELS.md)
4. 🔧 Настройте [конфигурацию](docs/CONFIGURATION.md) под ваши нужды
5. 🚀 Интегрируйте с вашим Telegram парсером
6. 📊 Настройте мониторинг и алерты

## 💡 Полезные команды

```bash
# Логи в реальном времени
docker compose logs -f app

# Статус всех сервисов
docker compose ps

# Использование ресурсов
docker stats

# Подключение к PostgreSQL
docker compose exec postgres psql -U postgres -d telegram_channels

# Подключение к Kafka
docker compose exec kafka bash

# Проверка Kafka consumer groups
docker compose exec kafka kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --group tg-channel-consumer \
    --describe
```

## 🎉 Готово!

Сервис запущен и готов к работе. Если возникли проблемы - смотрите раздел Troubleshooting или полную документацию.

---

**Версия**: 2.0.0  
**Статус**: ✅ Production Ready  
**Поддержка**: См. документацию

