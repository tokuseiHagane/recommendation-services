#!/usr/bin/env python3
"""
Simple consumer test for Telegram and VK modules.
Consumes messages from Kafka and inserts into PostgreSQL using psycopg2.
"""
import asyncio
import json
import logging

import psycopg2
from aiokafka import AIOKafkaConsumer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = "localhost:9092"


async def process_tg_channels():
    """Consume TG channels and insert into database."""
    logger.info("Processing TG channels...")
    
    # Connect to DB using psycopg2
    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        user="app_user",
        password="app_password",
        database="telegram",
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Create consumer
    consumer = AIOKafkaConsumer(
        "tg_channels",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="earliest",
        group_id="test-tg-consumer-v2",
        consumer_timeout_ms=10000,
    )
    await consumer.start()
    
    count = 0
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode())
            
            # Upsert into DB
            cur.execute("""
                INSERT INTO channels (id, name, type)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    type = EXCLUDED.type
            """, (data.get("id"), data.get("name"), data.get("type")))
            
            count += 1
            logger.info(f"  Inserted TG channel: {data.get('name')}")
            
    except Exception as e:
        logger.info(f"TG Consumer finished: {e}")
    finally:
        await consumer.stop()
        cur.close()
        conn.close()
    
    logger.info(f"Total TG channels processed: {count}")
    return count


async def process_vk_groups():
    """Consume VK groups and insert into database."""
    logger.info("Processing VK groups...")
    
    # Connect to DB using psycopg2
    conn = psycopg2.connect(
        host="localhost",
        port=5434,
        user="app_user",
        password="app_password",
        database="vk",
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Create consumer
    consumer = AIOKafkaConsumer(
        "vk_groups",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="earliest",
        group_id="test-vk-consumer-v2",
        consumer_timeout_ms=10000,
    )
    await consumer.start()
    
    count = 0
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode())
            
            # Upsert into DB
            cur.execute("""
                INSERT INTO groups (id, name, screen_name, members_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    screen_name = EXCLUDED.screen_name,
                    members_count = EXCLUDED.members_count
            """, (data.get("id"), data.get("name"), data.get("screen_name"), data.get("members_count")))
            
            count += 1
            logger.info(f"  Inserted VK group: {data.get('name')} (id={data.get('id')})")
            
    except Exception as e:
        logger.info(f"VK Consumer finished: {e}")
    finally:
        await consumer.stop()
        cur.close()
        conn.close()
    
    logger.info(f"Total VK groups processed: {count}")
    return count


def verify_databases():
    """Verify data in databases using psycopg2."""
    logger.info("\n" + "=" * 60)
    logger.info("Database Verification")
    logger.info("=" * 60)
    
    # Check TG
    conn = psycopg2.connect(
        host="localhost", port=5433,
        user="app_user", password="app_password", database="telegram"
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM channels")
    count = cur.fetchone()[0]
    logger.info(f"TG channels in database: {count}")
    
    if count > 0:
        cur.execute("SELECT id, name, type FROM channels LIMIT 3")
        for row in cur.fetchall():
            logger.info(f"  - {row[1]} ({row[2]})")
    cur.close()
    conn.close()
    
    # Check VK
    conn = psycopg2.connect(
        host="localhost", port=5434,
        user="app_user", password="app_password", database="vk"
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM groups")
    count = cur.fetchone()[0]
    logger.info(f"VK groups in database: {count}")
    
    if count > 0:
        cur.execute("SELECT id, name, screen_name, members_count FROM groups LIMIT 3")
        for row in cur.fetchall():
            logger.info(f"  - {row[1]} (@{row[2]}, {row[3]} members)")
    cur.close()
    conn.close()
    
    logger.info("=" * 60)


async def main():
    logger.info("=" * 60)
    logger.info("Consumer Test: Telegram & VK Modules")
    logger.info("=" * 60)
    
    # Process messages
    await process_tg_channels()
    await process_vk_groups()
    
    # Verify results (sync function)
    verify_databases()


if __name__ == "__main__":
    asyncio.run(main())
