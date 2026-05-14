# Batch Processing Architecture Diagram

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         KAFKA TOPIC                              │
│                        (messages stream)                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │ msg1, msg2, msg3, ...
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KAFKA WORKER (Ship Layer)                     │
│  src/Ship/tasks/kafka_worker.py                                 │
│                                                                   │
│  ┌────────────────┐   ┌──────────────────────────────────┐     │
│  │  Message       │   │  Triggers:                        │     │
│  │  Buffer        │   │  • Size >= BATCH_SIZE (100)      │     │
│  │  (List)        │───│  • Timeout >= BATCH_TIMEOUT (5s) │     │
│  │                │   │  • Shutdown signal               │     │
│  └────────────────┘   └──────────────────────────────────┘     │
│                                                                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ flush_batch()
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              BATCH STORE ACTION (Container Layer)                │
│  src/Containers/message/actions/batch_store_messages_action.py  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  For each message:                                        │  │
│  │  1. Validate via MessageService                          │  │
│  │  2. Transform to normalized format                       │  │
│  │  3. Skip invalid, collect valid                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ normalized_messages[]
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              BATCH INSERT TASK (Container Layer)                 │
│  src/Containers/message/tasks/batch_insert_messages_task.py     │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Create Message instances                                 │  │
│  │  Piccolo ORM: Message.insert(*message_rows)              │  │
│  │  Single SQL: INSERT INTO messages VALUES (...), (...),   │  │
│  │              (...), ...                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ SQL query
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      POSTGRESQL DATABASE                         │
│                      messages table                              │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Component Diagram

```
┌───────────────────────────────────────────────────────────────────────┐
│                         SHIP LAYER (Infrastructure)                    │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  kafka_worker.py                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ async def consume_messages():                                 │   │
│  │   buffer = []                                                 │   │
│  │   last_flush = time()                                         │   │
│  │                                                               │   │
│  │   async for msg in consumer:                                 │   │
│  │     buffer.append(msg)                                       │   │
│  │                                                               │   │
│  │     if len(buffer) >= BATCH_SIZE or                          │   │
│  │        time() - last_flush >= BATCH_TIMEOUT:                 │   │
│  │                                                               │   │
│  │       await flush_batch(buffer)                              │   │
│  │       buffer.clear()                                         │   │
│  │       last_flush = time()                                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│       │                                                               │
│       │ calls                                                         │
│       ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ async def flush_batch(messages, metadata):                   │   │
│  │   await batch_store_messages_action(messages, metadata)      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                        │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    CONTAINER LAYER (Business Logic)                    │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Actions (Use Cases)                                                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ batch_store_messages_action.py                               │   │
│  │                                                               │   │
│  │ async def batch_store_messages_action(                       │   │
│  │     raw_messages: List[Dict],                                │   │
│  │     metadata_list: List[Dict]                                │   │
│  │ ) -> int:                                                     │   │
│  │                                                               │   │
│  │   # Validate & transform                                     │   │
│  │   for raw_msg in raw_messages:                               │   │
│  │     try:                                                      │   │
│  │       normalized = MessageService.validate(raw_msg)          │   │
│  │       valid_messages.append(normalized)                      │   │
│  │     except:                                                   │   │
│  │       logger.warning("Skip invalid")                         │   │
│  │                                                               │   │
│  │   # Persist                                                   │   │
│  │   count = await batch_insert_messages_task(valid_messages)   │   │
│  │   return count                                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│       │                                                               │
│       │ uses                                                          │
│       ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Services (Reusable Logic)                                     │   │
│  │ message_service.py                                            │   │
│  │                                                               │   │
│  │ class MessageService:                                         │   │
│  │   @staticmethod                                               │   │
│  │   def validate_and_transform(raw_msg):                       │   │
│  │     # Validation logic                                       │   │
│  │     return normalized                                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  Tasks (Atomic Operations)                                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ batch_insert_messages_task.py                                │   │
│  │                                                               │   │
│  │ async def batch_insert_messages_task(                        │   │
│  │     messages: List[Dict]                                     │   │
│  │ ) -> int:                                                     │   │
│  │                                                               │   │
│  │   # Create model instances                                   │   │
│  │   rows = [Message(**msg) for msg in messages]                │   │
│  │                                                               │   │
│  │   # Batch insert                                             │   │
│  │   await Message.insert(*rows)                                │   │
│  │                                                               │   │
│  │   return len(rows)                                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│       │                                                               │
│       │ uses                                                          │
│       ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Models (Data Access)                                          │   │
│  │ message_model.py                                              │   │
│  │                                                               │   │
│  │ class Message(Table):                                         │   │
│  │   id = Serial()                                               │   │
│  │   message_id = Varchar()                                      │   │
│  │   topic = Varchar()                                           │   │
│  │   payload = JSON()                                            │   │
│  │   ...                                                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                        │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────────────────┐
│                          DATABASE LAYER                                │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  PostgreSQL 18                                                        │
│                                                                        │
│  messages table:                                                      │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ id          SERIAL PRIMARY KEY                          │         │
│  │ message_id  VARCHAR(255)                                │         │
│  │ topic       VARCHAR(255)                                │         │
│  │ partition   INTEGER                                     │         │
│  │ offset      INTEGER                                     │         │
│  │ payload     JSON                                        │         │
│  │ processed   BOOLEAN DEFAULT FALSE                       │         │
│  │ received_at TIMESTAMP DEFAULT NOW()                     │         │
│  └────────────────────────────────────────────────────────┘         │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Sequence

```
1. Producer → Kafka
   ┌─────────┐
   │ Producer│──┐
   └─────────┘  │  msg1, msg2, msg3, ...
                ├─→ [Kafka Topic: messages]
   ┌─────────┐  │
   │ Producer│──┘
   └─────────┘

2. Kafka → Worker Buffer
   [Kafka Topic]
        │
        │ AIOKafkaConsumer
        ▼
   [Buffer: msg1, msg2, msg3, ...]
        │
        │ wait for trigger
        ▼
   Check: len(buffer) >= 100? OR time >= 5s?
        │
        │ YES
        ▼
   flush_batch()

3. Worker → Action
   flush_batch(
     raw_messages=[msg1, msg2, ..., msg100],
     metadata=[meta1, meta2, ..., meta100]
   )
        │
        ▼
   batch_store_messages_action()

4. Action → Validation
   for each message:
     ┌────────────┐
     │ MessageService │
     └────────────┘
          │
          ├─→ Valid? → add to normalized_list
          └─→ Invalid? → log & skip

5. Action → Task
   batch_insert_messages_task(
     normalized_messages=[norm1, norm2, ...]
   )
        │
        ▼
   Create: [Message(...), Message(...), ...]

6. Task → Database
   Message.insert(*rows)
        │
        ▼
   SQL: INSERT INTO messages 
        VALUES 
          (msg1_data),
          (msg2_data),
          ...
          (msg100_data)
        │
        ▼
   PostgreSQL commits transaction
        │
        ▼
   Return: 100 (rows inserted)
```

## Configuration Flow

```
┌─────────────┐
│   .env      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ Settings (Pydantic)     │
│                         │
│ BATCH_SIZE = 100        │
│ BATCH_TIMEOUT = 5.0     │
└──────┬──────────────────┘
       │
       ├─→ kafka_worker.py
       │     batch_size = settings.BATCH_SIZE
       │     batch_timeout = settings.BATCH_TIMEOUT
       │
       └─→ Runtime behavior:
             • Buffer accumulates up to 100 messages
             • Timeout triggers after 5 seconds
```

## Error Handling Flow

```
┌──────────────────────┐
│ Invalid Message      │
└──────┬───────────────┘
       │
       ▼
┌────────────────────────────────┐
│ MessageService.validate()      │
│ raises ValidationError         │
└──────┬─────────────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ Action: catch exception        │
│ logger.warning("Skip invalid") │
│ continue with next message     │
└──────┬─────────────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ Only valid messages sent       │
│ to batch_insert_messages_task  │
└────────────────────────────────┘

┌──────────────────────┐
│ Database Error       │
└──────┬───────────────┘
       │
       ▼
┌────────────────────────────────┐
│ Task: raises exception         │
└──────┬─────────────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ Action: propagates exception   │
└──────┬─────────────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ Worker: logs error             │
│ logger.exception(...)          │
│ Continue consuming             │
└────────────────────────────────┘
```

## Testing Architecture

```
┌──────────────────────────────────────────────────────┐
│                  TEST SUITE                          │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Unit Tests (test_batch_insert_task.py)             │
│  ┌────────────────────────────────────────────┐     │
│  │ • Empty list                                │     │
│  │ • Single message                            │     │
│  │ • 100 messages (typical)                    │     │
│  │ • 500 messages (large)                      │     │
│  │ • NULL fields                               │     │
│  │ • Order preservation                        │     │
│  └────────────────────────────────────────────┘     │
│                                                       │
│  Integration Tests (test_batch_store_action.py)     │
│  ┌────────────────────────────────────────────┐     │
│  │ • Validation + insert                       │     │
│  │ • Without metadata                          │     │
│  │ • Mixed valid/invalid                       │     │
│  │ • All invalid (return 0)                    │     │
│  │ • Metadata mismatch (raises error)          │     │
│  │ • Large batch (100 messages)                │     │
│  └────────────────────────────────────────────┘     │
│                                                       │
│  E2E Tests (manual/benchmark)                        │
│  ┌────────────────────────────────────────────┐     │
│  │ • Kafka → Worker → DB                       │     │
│  │ • Performance benchmarks                    │     │
│  │ • Stress tests                              │     │
│  └────────────────────────────────────────────┘     │
│                                                       │
└──────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│                   PRODUCTION                         │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌───────────┐        ┌───────────┐                │
│  │  Kafka    │        │  Kafka    │                │
│  │  Broker 1 │◄──────►│  Broker 2 │                │
│  └─────┬─────┘        └─────┬─────┘                │
│        │                    │                       │
│        │ Topic: messages    │                       │
│        │ Partitions: 3      │                       │
│        └────────┬───────────┘                       │
│                 │                                    │
│         ┌───────┴───────┐                          │
│         │               │                           │
│    ┌────▼─────┐   ┌────▼─────┐                    │
│    │ Worker 1 │   │ Worker 2 │                    │
│    │ (Pod)    │   │ (Pod)    │                    │
│    └────┬─────┘   └────┬─────┘                    │
│         │               │                           │
│         │  INSERT batch │                           │
│         └───────┬───────┘                          │
│                 │                                    │
│         ┌───────▼───────┐                          │
│         │  PostgreSQL   │                          │
│         │   (Primary)   │                          │
│         │               │                           │
│         │  messages     │                          │
│         │  (partitioned)│                          │
│         └───────────────┘                          │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

**Legend:**
- `┌─┐ └─┘` - Components/Services
- `│ ─ ▼` - Data flow direction
- `◄──►` - Bidirectional communication
- `[...]` - Data structures/buffers

**См. также:**
- [BATCH_PROCESSING.md](./BATCH_PROCESSING.md) - Technical details
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Implementation overview

