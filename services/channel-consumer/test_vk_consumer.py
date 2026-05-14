#!/usr/bin/env python3
"""Quick VK groups consumer."""
import asyncio
import json
import logging
import psycopg2
from aiokafka import AIOKafkaConsumer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    logger.info("Processing VK groups...")
    
    conn = psycopg2.connect(
        host="localhost", port=5434,
        user="app_user", password="app_password", database="vk"
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    consumer = AIOKafkaConsumer(
        "vk_groups",
        bootstrap_servers="localhost:9092",
        auto_offset_reset="earliest",
        group_id="test-vk-consumer-v3",
        consumer_timeout_ms=10000,
    )
    await consumer.start()
    
    count = 0
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode())
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
        logger.info(f"Consumer finished: {e}")
    finally:
        await consumer.stop()
        cur.close()
        conn.close()
    
    logger.info(f"Total VK groups processed: {count}")


if __name__ == "__main__":
    asyncio.run(main())
