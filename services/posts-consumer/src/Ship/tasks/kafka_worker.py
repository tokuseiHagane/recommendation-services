import asyncio
import json
import logging
from typing import Any, List, Dict
from aiokafka import AIOKafkaConsumer

from src.Ship.config.settings import settings
from src.Ship.config.kafka_config import KafkaConfig
from src.Containers.message.actions.batch_store_messages_action import batch_store_messages_action

logger = logging.getLogger(__name__)


async def flush_batch(
    batch_messages: List[Dict[str, Any]],
    batch_metadata: List[Dict[str, Any]]
) -> None:
    """
    Flush accumulated batch to database.
    
    Args:
        batch_messages: List of raw message payloads
        batch_metadata: List of corresponding metadata dicts
    """
    if not batch_messages:
        return
    
    try:
        inserted_count = await batch_store_messages_action(
            batch_messages,
            metadata_list=batch_metadata
        )
        logger.info(
            f"Flushed batch: {inserted_count} messages inserted "
            f"(out of {len(batch_messages)} received)"
        )
    except Exception as exc:
        logger.exception(f"Failed to flush batch of {len(batch_messages)} messages: {exc}")
        # In production, you might want to implement retry logic or dead letter queue


async def consume_messages(di: Any | None = None) -> None:
    """
    Continuously consume messages from Kafka with batch processing.
    
    Messages are accumulated in a buffer and inserted into DB in batches
    when either:
    - Batch size reaches BATCH_SIZE (default 100)
    - Timeout of BATCH_TIMEOUT seconds elapses (default 5s)
    
    Args:
        di: optional DI container (Dishka), reserved for future use
    """
    kafka_conf = KafkaConfig()
    batch_size = settings.BATCH_SIZE
    batch_timeout = settings.BATCH_TIMEOUT

    consumer = AIOKafkaConsumer(
        kafka_conf.topic,
        bootstrap_servers=kafka_conf.bootstrap_servers,
        group_id=kafka_conf.group_id,
        enable_auto_commit=kafka_conf.enable_auto_commit,
        auto_offset_reset=kafka_conf.auto_offset_reset,
        consumer_timeout_ms=kafka_conf.consumer_timeout_ms,
    )

    await consumer.start()
    logger.info(
        f"Kafka consumer started for topic: {kafka_conf.topic} "
        f"(batch_size={batch_size}, batch_timeout={batch_timeout}s)"
    )

    # Batch buffers
    batch_messages: List[Dict[str, Any]] = []
    batch_metadata: List[Dict[str, Any]] = []
    last_flush_time = asyncio.get_event_loop().time()

    try:
        async for msg in consumer:
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                logger.debug(f"Received message: {payload}")

                # Add to batch
                batch_messages.append(payload)
                batch_metadata.append({
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                })

                current_time = asyncio.get_event_loop().time()
                time_since_last_flush = current_time - last_flush_time

                # Flush if batch is full or timeout elapsed
                should_flush = (
                    len(batch_messages) >= batch_size or
                    time_since_last_flush >= batch_timeout
                )

                if should_flush:
                    await flush_batch(batch_messages, batch_metadata)
                    # Clear buffers
                    batch_messages.clear()
                    batch_metadata.clear()
                    last_flush_time = asyncio.get_event_loop().time()

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode Kafka message: {e}")
            except Exception as e:
                logger.exception(f"Error while processing message: {e}")

    except asyncio.CancelledError:
        logger.info("Kafka consumer loop cancelled, shutting down...")
        # Flush remaining messages before shutdown
        if batch_messages:
            logger.info(f"Flushing {len(batch_messages)} remaining messages before shutdown...")
            await flush_batch(batch_messages, batch_metadata)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped.")


def start_kafka_worker() -> None:
    """Entry point to start the Kafka consumer worker in an async loop."""
    try:
        asyncio.run(consume_messages())
    except KeyboardInterrupt:
        logger.info("Kafka worker interrupted by user.")
    except Exception as e:
        logger.exception(f"Kafka worker encountered a fatal error: {e}")
