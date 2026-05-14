#!/usr/bin/env python
"""
Simple script to send test messages to Kafka.

Usage:
    python scripts/send_test_messages.py
    python scripts/send_test_messages.py --count 500 --delay 0.1
"""
import asyncio
import json
import time
import argparse
from aiokafka import AIOKafkaProducer
from src.Ship.config.settings import settings


async def send_messages(count: int, delay: float = 0.0):
    """
    Send test messages to Kafka.
    
    Args:
        count: Number of messages to send
        delay: Delay between messages in seconds (0 = no delay)
    """
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    await producer.start()
    print(f"📤 Sending {count} messages to '{settings.KAFKA_TOPIC}'...")
    
    if delay > 0:
        print(f"⏱️  Delay between messages: {delay}s")
    
    try:
        for i in range(count):
            message = {
                "payload": {
                    "test_id": f"test-{int(time.time())}",
                    "index": i,
                    "timestamp": time.time(),
                    "message": f"Test message #{i}",
                    "data": {
                        "user": f"user-{i % 10}",
                        "action": "test_action",
                        "value": i * 1.5,
                    }
                }
            }
            
            await producer.send(settings.KAFKA_TOPIC, message)
            
            if (i + 1) % 10 == 0:
                print(f"  Sent {i + 1}/{count} messages")
            
            if delay > 0:
                await asyncio.sleep(delay)
        
        await producer.flush()
        print(f"\n✅ Successfully sent {count} messages")
        
    finally:
        await producer.stop()


def main():
    parser = argparse.ArgumentParser(
        description="Send test messages to Kafka"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of messages to send (default: 100)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay between messages in seconds (default: 0 - no delay)"
    )
    
    args = parser.parse_args()
    
    print(f"🔧 Configuration:")
    print(f"  Topic: {settings.KAFKA_TOPIC}")
    print(f"  Bootstrap Servers: {settings.KAFKA_BOOTSTRAP_SERVERS}")
    print(f"  Messages: {args.count}")
    print()
    
    asyncio.run(send_messages(args.count, args.delay))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

