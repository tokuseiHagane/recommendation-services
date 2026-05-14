#!/usr/bin/env python
"""
Benchmark script for batch processing performance testing.

This script sends a configurable number of test messages to Kafka
and measures throughput and latency metrics.

Usage:
    python scripts/benchmark_batch_processing.py --messages 1000 --batch-size 100
    python scripts/benchmark_batch_processing.py --help
"""
import asyncio
import json
import time
import argparse
from typing import Dict, Any, List
from aiokafka import AIOKafkaProducer
from src.Ship.config.settings import settings


async def send_test_messages(
    num_messages: int,
    topic: str,
    bootstrap_servers: str,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """
    Send test messages to Kafka and measure performance.
    
    Args:
        num_messages: Total number of messages to send
        topic: Kafka topic name
        bootstrap_servers: Kafka bootstrap servers
        batch_size: Messages per producer batch
    
    Returns:
        Dictionary with performance metrics
    """
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        compression_type='gzip',
        linger_ms=10,  # Wait up to 10ms to batch messages
    )
    
    await producer.start()
    print(f"📤 Producer started. Sending {num_messages} messages to '{topic}'...")
    
    start_time = time.time()
    send_times: List[float] = []
    
    try:
        for i in range(num_messages):
            message = {
                "payload": {
                    "benchmark_id": f"bench-{int(start_time)}",
                    "message_index": i,
                    "timestamp": time.time(),
                    "data": f"test-message-{i}",
                    "batch_num": i // batch_size,
                }
            }
            
            msg_start = time.time()
            await producer.send(topic, message)
            msg_end = time.time()
            send_times.append((msg_end - msg_start) * 1000)  # Convert to ms
            
            # Progress indicator
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                throughput = (i + 1) / elapsed
                print(f"  Sent {i + 1}/{num_messages} messages "
                      f"({throughput:.0f} msg/sec)")
        
        # Wait for all messages to be delivered
        await producer.flush()
        
    finally:
        await producer.stop()
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Calculate metrics
    metrics = {
        "total_messages": num_messages,
        "total_duration_sec": round(total_duration, 2),
        "throughput_msg_per_sec": round(num_messages / total_duration, 2),
        "avg_send_latency_ms": round(sum(send_times) / len(send_times), 2),
        "p95_send_latency_ms": round(sorted(send_times)[int(len(send_times) * 0.95)], 2),
        "p99_send_latency_ms": round(sorted(send_times)[int(len(send_times) * 0.99)], 2),
        "min_send_latency_ms": round(min(send_times), 2),
        "max_send_latency_ms": round(max(send_times), 2),
    }
    
    return metrics


async def verify_database_inserts(
    expected_count: int,
    benchmark_id: str,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Verify that messages were inserted into database.
    
    Args:
        expected_count: Expected number of messages
        benchmark_id: Benchmark ID to filter messages
        timeout: Max seconds to wait for inserts
    
    Returns:
        Dictionary with verification results
    """
    from src.Containers.message.model.message_model import Message
    
    print(f"\n⏳ Waiting up to {timeout}s for messages to be inserted into DB...")
    
    start_time = time.time()
    last_count = 0
    
    while (time.time() - start_time) < timeout:
        # Query messages with our benchmark_id
        count = await Message.count().where(
            Message.payload.contains({"benchmark_id": benchmark_id})
        )
        
        if count != last_count:
            print(f"  DB count: {count}/{expected_count}")
            last_count = count
        
        if count >= expected_count:
            elapsed = time.time() - start_time
            return {
                "success": True,
                "inserted_count": count,
                "expected_count": expected_count,
                "time_to_insert_sec": round(elapsed, 2),
                "db_throughput_msg_per_sec": round(count / elapsed, 2),
            }
        
        await asyncio.sleep(1)
    
    # Timeout reached
    return {
        "success": False,
        "inserted_count": last_count,
        "expected_count": expected_count,
        "time_to_insert_sec": timeout,
        "error": "Timeout: Not all messages inserted",
    }


def print_results(send_metrics: Dict[str, Any], db_metrics: Dict[str, Any]) -> None:
    """Print formatted benchmark results."""
    print("\n" + "="*60)
    print("📊 BENCHMARK RESULTS")
    print("="*60)
    
    print("\n🚀 KAFKA PRODUCER PERFORMANCE:")
    print(f"  Total Messages:       {send_metrics['total_messages']}")
    print(f"  Duration:             {send_metrics['total_duration_sec']}s")
    print(f"  Throughput:           {send_metrics['throughput_msg_per_sec']} msg/sec")
    print(f"\n  Send Latency:")
    print(f"    Average:            {send_metrics['avg_send_latency_ms']} ms")
    print(f"    P95:                {send_metrics['p95_send_latency_ms']} ms")
    print(f"    P99:                {send_metrics['p99_send_latency_ms']} ms")
    print(f"    Min/Max:            {send_metrics['min_send_latency_ms']} / "
          f"{send_metrics['max_send_latency_ms']} ms")
    
    print("\n💾 DATABASE INSERT PERFORMANCE:")
    if db_metrics['success']:
        print(f"  ✅ Status:             SUCCESS")
        print(f"  Inserted:             {db_metrics['inserted_count']}/{db_metrics['expected_count']}")
        print(f"  Time to Insert:       {db_metrics['time_to_insert_sec']}s")
        print(f"  DB Throughput:        {db_metrics['db_throughput_msg_per_sec']} msg/sec")
        
        # Calculate end-to-end latency
        e2e_latency = db_metrics['time_to_insert_sec']
        print(f"\n  End-to-End Latency:   {e2e_latency}s")
    else:
        print(f"  ❌ Status:             FAILED")
        print(f"  Inserted:             {db_metrics['inserted_count']}/{db_metrics['expected_count']}")
        print(f"  Error:                {db_metrics.get('error', 'Unknown')}")
    
    print("\n" + "="*60)


async def main():
    """Main benchmark function."""
    parser = argparse.ArgumentParser(
        description="Benchmark batch processing performance"
    )
    parser.add_argument(
        "--messages",
        type=int,
        default=1000,
        help="Number of messages to send (default: 1000)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Producer batch size (default: 100)"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=settings.KAFKA_TOPIC,
        help=f"Kafka topic (default: {settings.KAFKA_TOPIC})"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip database verification"
    )
    parser.add_argument(
        "--verify-timeout",
        type=int,
        default=30,
        help="DB verification timeout in seconds (default: 30)"
    )
    
    args = parser.parse_args()
    
    print("🔧 BENCHMARK CONFIGURATION:")
    print(f"  Messages:             {args.messages}")
    print(f"  Producer Batch Size:  {args.batch_size}")
    print(f"  Topic:                {args.topic}")
    print(f"  Bootstrap Servers:    {settings.KAFKA_BOOTSTRAP_SERVERS}")
    print(f"  Consumer Batch Size:  {settings.BATCH_SIZE}")
    print(f"  Consumer Batch Timeout: {settings.BATCH_TIMEOUT}s")
    print()
    
    # Send messages
    send_metrics = await send_test_messages(
        num_messages=args.messages,
        topic=args.topic,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        batch_size=args.batch_size,
    )
    
    print(f"\n✅ Sent {send_metrics['total_messages']} messages in "
          f"{send_metrics['total_duration_sec']}s "
          f"({send_metrics['throughput_msg_per_sec']} msg/sec)")
    
    # Verify database inserts
    if not args.no_verify:
        benchmark_id = f"bench-{int(send_metrics.get('start_time', time.time()))}"
        db_metrics = await verify_database_inserts(
            expected_count=args.messages,
            benchmark_id=benchmark_id,
            timeout=args.verify_timeout,
        )
    else:
        print("\n⚠️  Database verification skipped (--no-verify)")
        db_metrics = {"success": None, "message": "Skipped"}
    
    # Print results
    print_results(send_metrics, db_metrics)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Benchmark failed: {e}")
        raise

