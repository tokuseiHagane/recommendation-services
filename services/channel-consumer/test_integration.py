#!/usr/bin/env python3
"""
Integration test for Telegram and VK modules.
Uses only aiokafka and asyncpg which are installed.
"""
import asyncio
import json
import logging
import random
import uuid
from datetime import datetime

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = "localhost:9092"


async def send_tg_channels(count: int = 10):
    """Send test Telegram channels to Kafka."""
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    )
    await producer.start()
    
    try:
        logger.info(f"Sending {count} Telegram channels to 'tg_channels'...")
        
        for i in range(count):
            channel = {
                "id": str(uuid.uuid4()),
                "name": f"Test TG Channel {i+1} - {datetime.now().strftime('%H%M%S')}",
                "type": random.choice(["channel", "supergroup", "group"]),
            }
            await producer.send("tg_channels", channel)
            logger.info(f"  Sent TG channel: {channel['name']}")
        
        await producer.flush()
        logger.info(f"Successfully sent {count} TG channels")
        
    finally:
        await producer.stop()


async def send_vk_groups(count: int = 10):
    """Send test VK groups to Kafka."""
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    )
    await producer.start()
    
    try:
        logger.info(f"Sending {count} VK groups to 'vk_groups'...")
        
        for i in range(count):
            group = {
                "id": random.randint(1000000, 999999999),
                "name": f"Test VK Group {i+1} - {datetime.now().strftime('%H%M%S')}",
                "screen_name": f"test_vk_group_{i+1}_{random.randint(1000, 9999)}",
                "members_count": random.randint(100, 1000000),
            }
            await producer.send("vk_groups", group)
            logger.info(f"  Sent VK group: {group['name']} (id={group['id']})")
        
        await producer.flush()
        logger.info(f"Successfully sent {count} VK groups")
        
    finally:
        await producer.stop()


async def verify_kafka_topics():
    """Verify that messages are in Kafka topics."""
    logger.info("Verifying Kafka topics...")
    
    # Check tg_channels
    consumer = AIOKafkaConsumer(
        "tg_channels",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
    )
    await consumer.start()
    
    tg_count = 0
    try:
        async for msg in consumer:
            tg_count += 1
            if tg_count <= 3:
                data = json.loads(msg.value.decode())
                logger.info(f"  TG sample: {data.get('name', 'unknown')}")
    except:
        pass
    finally:
        await consumer.stop()
    
    logger.info(f"Found {tg_count} messages in 'tg_channels'")
    
    # Check vk_groups
    consumer = AIOKafkaConsumer(
        "vk_groups",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
    )
    await consumer.start()
    
    vk_count = 0
    try:
        async for msg in consumer:
            vk_count += 1
            if vk_count <= 3:
                data = json.loads(msg.value.decode())
                logger.info(f"  VK sample: {data.get('name', 'unknown')} (members: {data.get('members_count', 0)})")
    except:
        pass
    finally:
        await consumer.stop()
    
    logger.info(f"Found {vk_count} messages in 'vk_groups'")
    
    return tg_count, vk_count


async def check_databases():
    """Check if data is in databases (requires asyncpg)."""
    try:
        import asyncpg
        
        # Check TG database
        logger.info("Checking Telegram database...")
        try:
            conn = await asyncpg.connect(
                host="localhost",
                port=5433,
                user="app_user",
                password="app_password",
                database="telegram",
            )
            
            # Check if table exists
            result = await conn.fetch(
                "SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_name = 'channels'"
            )
            if result[0]['cnt'] > 0:
                count = await conn.fetchval("SELECT COUNT(*) FROM channels")
                logger.info(f"  TG channels in DB: {count}")
                
                if count > 0:
                    sample = await conn.fetch("SELECT id, name, type FROM channels LIMIT 3")
                    for row in sample:
                        logger.info(f"    - {row['name']} ({row['type']})")
            else:
                logger.info("  TG channels table not created yet (consumer not running)")
            
            await conn.close()
        except Exception as e:
            logger.error(f"  TG DB error: {e}")
        
        # Check VK database
        logger.info("Checking VK database...")
        try:
            conn = await asyncpg.connect(
                host="localhost",
                port=5434,
                user="app_user",
                password="app_password",
                database="vk",
            )
            
            # Check if table exists
            result = await conn.fetch(
                "SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_name = 'groups'"
            )
            if result[0]['cnt'] > 0:
                count = await conn.fetchval("SELECT COUNT(*) FROM groups")
                logger.info(f"  VK groups in DB: {count}")
                
                if count > 0:
                    sample = await conn.fetch("SELECT id, name, screen_name, members_count FROM groups LIMIT 3")
                    for row in sample:
                        logger.info(f"    - {row['name']} (@{row['screen_name']}, {row['members_count']} members)")
            else:
                logger.info("  VK groups table not created yet (consumer not running)")
            
            await conn.close()
        except Exception as e:
            logger.error(f"  VK DB error: {e}")
            
    except ImportError:
        logger.warning("asyncpg not installed, skipping DB check")


async def main():
    logger.info("=" * 60)
    logger.info("Integration Test: Telegram & VK Modules")
    logger.info("=" * 60)
    
    # Step 1: Send test messages
    logger.info("\n[Step 1] Sending test messages to Kafka...")
    await send_tg_channels(5)
    await send_vk_groups(5)
    
    # Step 2: Verify messages in Kafka
    logger.info("\n[Step 2] Verifying messages in Kafka topics...")
    tg_count, vk_count = await verify_kafka_topics()
    
    # Step 3: Check databases
    logger.info("\n[Step 3] Checking databases...")
    await check_databases()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"TG channels in Kafka: {tg_count}")
    logger.info(f"VK groups in Kafka: {vk_count}")
    logger.info("\nNote: To see data in DB, run the consumer application:")
    logger.info("  uv run uvicorn app:app --port 8000")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
