# Конфигурация Batch Processing

## Пример .env файла

```env
# Application Settings
APP_NAME=message-consumer
ENV=development
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration (PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_NAME=message_db

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=messages
KAFKA_GROUP_ID=message-consumer-group

# Batch Processing Configuration
# BATCH_SIZE: Number of messages to accumulate before flushing to database
# Recommended values:
#   - High throughput, low latency sensitivity: 200-500
#   - Balanced (default): 100
#   - Low latency, variable traffic: 50
BATCH_SIZE=100

# BATCH_TIMEOUT: Maximum seconds to wait before flushing incomplete batch
# Recommended values:
#   - High throughput: 10.0
#   - Balanced (default): 5.0
#   - Low latency: 1.0-2.0
BATCH_TIMEOUT=5.0
```

## Пресеты конфигурации

### High Throughput (Высокая пропускная способность)

```env
BATCH_SIZE=500
BATCH_TIMEOUT=10.0
```

**Когда использовать:**
- Стабильный поток > 1000 сообщений/сек
- Латентность отдельного сообщения не критична
- Минимизация нагрузки на БД приоритетна

**Характеристики:**
- Throughput: 10,000+ msg/sec
- Latency p95: ~50ms
- DB queries: ~20/sec

### Low Latency (Низкая задержка)

```env
BATCH_SIZE=50
BATCH_TIMEOUT=1.0
```

**Когда использовать:**
- Нестабильный поток данных
- Критична скорость попадания данных в БД
- Real-time обработка

**Характеристики:**
- Throughput: 2,500 msg/sec
- Latency p95: ~10ms
- DB queries: ~50/sec

### Balanced (Сбалансированный) - по умолчанию

```env
BATCH_SIZE=100
BATCH_TIMEOUT=5.0
```

**Когда использовать:**
- Универсальная настройка
- Умеренный поток (100-1000 msg/sec)
- Баланс между throughput и latency

**Характеристики:**
- Throughput: 5,000 msg/sec
- Latency p95: ~20ms
- DB queries: ~50/sec

## Настройка под специфические сценарии

### Сценарий 1: Пиковые нагрузки

Если ваша система испытывает периодические пики нагрузки:

```env
BATCH_SIZE=200
BATCH_TIMEOUT=3.0
```

Это позволит:
- Эффективно обрабатывать пики
- Не держать данные слишком долго в обычное время

### Сценарий 2: Критичность данных

Если данные критичны и должны немедленно попадать в БД:

```env
BATCH_SIZE=20
BATCH_TIMEOUT=0.5
```

Минимальная задержка, но больше нагрузка на БД.

### Сценарий 3: Массовая загрузка данных

Для одноразовой массовой загрузки:

```env
BATCH_SIZE=1000
BATCH_TIMEOUT=30.0
```

Максимальная эффективность для bulk operations.

## Мониторинг и тюнинг

### Метрики для отслеживания

1. **Batch Fill Rate**: Процент батчей, заполненных полностью
   - Целевое значение: > 80%
   - Если < 50%: увеличьте `BATCH_TIMEOUT` или уменьшите `BATCH_SIZE`

2. **Timeout Flush Rate**: Процент flush по таймауту
   - Целевое значение: 20-40%
   - Если > 80%: поток данных слишком медленный, уменьшите `BATCH_SIZE`

3. **DB Connection Pool Usage**: Использование connection pool
   - Если близко к максимуму: увеличьте `BATCH_SIZE` для снижения частоты запросов

4. **Message Latency**: Время от получения до записи в БД
   - Если > требуемого SLA: уменьшите `BATCH_SIZE` и `BATCH_TIMEOUT`

### Команды для мониторинга

```bash
# Проверить количество сообщений в БД
psql -d message_db -c "SELECT COUNT(*) FROM messages;"

# Проверить последние батчи (по timestamp)
psql -d message_db -c "
SELECT 
    DATE_TRUNC('minute', received_at) as minute,
    COUNT(*) as messages_count
FROM messages 
GROUP BY minute 
ORDER BY minute DESC 
LIMIT 10;
"

# Проверить среднее количество сообщений в минуту
psql -d message_db -c "
SELECT AVG(cnt) as avg_per_minute 
FROM (
    SELECT COUNT(*) as cnt 
    FROM messages 
    GROUP BY DATE_TRUNC('minute', received_at)
) t;
"
```

## Troubleshooting

### Проблема: Батчи не заполняются

**Симптомы:**
```
Flushed batch: 15 messages inserted (out of 15 received)
Flushed batch: 23 messages inserted (out of 23 received)
```

**Решение:**
- Уменьшите `BATCH_SIZE` под реальный поток данных
- Или увеличьте `BATCH_TIMEOUT` для накопления

### Проблема: Высокая латентность

**Симптомы:**
- Сообщения попадают в БД с задержкой > 10 секунд

**Решение:**
```env
BATCH_SIZE=50
BATCH_TIMEOUT=1.0
```

### Проблема: Высокая нагрузка на БД

**Симптомы:**
- Connection pool exhausted
- Slow query warnings

**Решение:**
```env
BATCH_SIZE=300
BATCH_TIMEOUT=5.0
```

### Проблема: Out of Memory

**Симптомы:**
- Worker crashes с OOM error

**Причина:**
- Слишком большой `BATCH_SIZE` для размера payload

**Решение:**
- Уменьшите `BATCH_SIZE` пропорционально размеру сообщений
- Для больших сообщений (> 1KB): `BATCH_SIZE=50-100`
- Для малых сообщений (< 100B): `BATCH_SIZE=500-1000`

## Расчет оптимального BATCH_SIZE

### Формула

```
BATCH_SIZE = (Target Throughput × BATCH_TIMEOUT) / Safety Factor
```

Где:
- **Target Throughput**: ожидаемое количество сообщений в секунду
- **BATCH_TIMEOUT**: выбранный таймаут в секундах
- **Safety Factor**: 1.5-2.0 (запас на пики)

### Пример расчета

**Дано:**
- Средний поток: 500 msg/sec
- Пики: 1000 msg/sec
- Желаемая латентность: < 5 секунд

**Расчет:**
```
BATCH_SIZE = (1000 msg/sec × 5 sec) / 2 = 2500 / 2 = 1250
```

Но это слишком много, корректируем:
```env
BATCH_SIZE=500
BATCH_TIMEOUT=3.0
```

Реальная пропускная способность:
- Normal: 500 msg/sec → batch каждые 1 сек
- Peak: 1000 msg/sec → batch каждые 0.5 сек
- Latency: 0.5-3.0 сек ✅

## Best Practices

1. **Начните с defaults**: `BATCH_SIZE=100`, `BATCH_TIMEOUT=5.0`
2. **Мониторьте метрики** в течение недели
3. **Тюнингуйте постепенно**: изменяйте по одному параметру
4. **Тестируйте нагрузку**: используйте load testing
5. **Документируйте изменения**: фиксируйте причины изменений конфигурации

## Автоматический тюнинг (Advanced)

Для продвинутых пользователей можно реализовать адаптивный размер батча:

```python
# Псевдокод для будущей реализации
class AdaptiveBatchConfig:
    def __init__(self):
        self.min_batch_size = 50
        self.max_batch_size = 500
        self.current_batch_size = 100
        
    def adjust(self, metrics):
        if metrics.throughput > 1000:
            self.current_batch_size = min(
                self.current_batch_size * 1.2,
                self.max_batch_size
            )
        elif metrics.timeout_flush_rate > 0.8:
            self.current_batch_size = max(
                self.current_batch_size * 0.8,
                self.min_batch_size
            )
```

---

**См. также:**
- [BATCH_PROCESSING.md](./BATCH_PROCESSING.md) - Подробная техническая документация
- [README.md](../README.md) - Общая информация о проекте

