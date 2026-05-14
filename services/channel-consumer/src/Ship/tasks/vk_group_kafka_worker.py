import asyncio
import json
import logging
from typing import Any, List, Dict
from aiokafka import AIOKafkaConsumer

from src.Ship.config.settings import settings
from src.Ship.config.kafka_config import KafkaConfig
from src.Containers.vk_group.actions.batch_process_groups_action import batch_process_groups_action

logger = logging.getLogger(__name__)


async def flush_group_batch(
    batch_groups: List[Dict[str, Any]],
    batch_metadata: List[Dict[str, Any]]
) -> None:
    """
    Flush accumulated batch of VK groups to database.
    
    This function:
    1. Validates and upserts groups
    2. Caches and publishes to Kafka
    
    Args:
        batch_groups: List of raw group payloads
        batch_metadata: List of corresponding metadata dicts
    """
    if not batch_groups:
        return
    
    try:
        result = await batch_process_groups_action(
            batch_groups,
            metadata_list=batch_metadata,
            use_cache=True,  # Enable cache workflow
            publish_diff=True,  # Publish from cache to Kafka
        )
        logger.info(
            f"Flushed VK group batch: {result['groups_upserted']} upserted, "
            f"{result['groups_cached']} cached, "
            f"{result['groups_published_from_cache']} published from cache, "
            f"{result['publish_errors']} publish errors, "
            f"{result['validation_errors']} validation errors "
            f"(out of {result['total_received']} received)"
        )
    except Exception as exc:
        logger.exception(f"Failed to flush batch of {len(batch_groups)} VK groups: {exc}")
        # In production, you might want to implement retry logic or dead letter queue


async def consume_vk_groups(di: Any | None = None, initialize_cache: bool = True) -> None:
    """
    Continuously consume VK groups from Kafka with batch processing.
    
    Groups are accumulated in a buffer and processed in batches when either:
    - Batch size reaches BATCH_SIZE (default 100)
    - Timeout of BATCH_TIMEOUT seconds elapses (default 5s)
    
    For each batch:
    1. Validate group data
    2. Upsert groups to groups table (INSERT ON CONFLICT UPDATE)
    3. Cache upserted groups in memory
    4. Publish all groups from cache to vk_groups_diff topic
    5. Clear cache after successful publish
    
    Args:
        di: optional DI container (Dishka), reserved for future use
        initialize_cache: deprecated parameter, kept for compatibility
    """
    kafka_conf = KafkaConfig()
    batch_size = settings.BATCH_SIZE
    batch_timeout = settings.BATCH_TIMEOUT
    
    # Use VK-specific topic and group_id
    topic = settings.VK_KAFKA_TOPIC
    group_id = settings.VK_KAFKA_GROUP_ID

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=kafka_conf.bootstrap_servers,
        group_id=group_id,
        enable_auto_commit=kafka_conf.enable_auto_commit,
        auto_offset_reset=kafka_conf.auto_offset_reset,
        consumer_timeout_ms=kafka_conf.consumer_timeout_ms,
    )

    await consumer.start()
    logger.info(
        f"VK Kafka consumer started for topic: {topic} "
        f"(batch_size={batch_size}, batch_timeout={batch_timeout}s)"
    )

    # Batch buffers
    batch_groups: List[Dict[str, Any]] = []
    batch_metadata: List[Dict[str, Any]] = []
    last_flush_time = asyncio.get_event_loop().time()

    try:
        async for msg in consumer:
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                logger.debug(f"Received VK group: {payload.get('id', 'unknown')}")

                # Add to batch
                batch_groups.append(payload)
                batch_metadata.append({
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                })

                current_time = asyncio.get_event_loop().time()
                time_since_last_flush = current_time - last_flush_time

                # Flush if batch is full or timeout elapsed
                should_flush = (
                    len(batch_groups) >= batch_size or
                    time_since_last_flush >= batch_timeout
                )

                if should_flush:
                    await flush_group_batch(batch_groups, batch_metadata)
                    # Clear buffers
                    batch_groups.clear()
                    batch_metadata.clear()
                    last_flush_time = asyncio.get_event_loop().time()

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode Kafka message: {e}")
            except Exception as e:
                logger.exception(f"Error while processing VK group: {e}")

    except asyncio.CancelledError:
        logger.info("VK Kafka consumer loop cancelled, shutting down...")
        # Flush remaining groups before shutdown
        if batch_groups:
            logger.info(f"Flushing {len(batch_groups)} remaining VK groups before shutdown...")
            await flush_group_batch(batch_groups, batch_metadata)
    finally:
        await consumer.stop()
        logger.info("VK Kafka consumer stopped.")


def start_vk_group_kafka_worker() -> None:
    """Entry point to start the Kafka consumer worker for vk_groups topic."""
    try:
        asyncio.run(consume_vk_groups())
    except KeyboardInterrupt:
        logger.info("VK Kafka worker interrupted by user.")
    except Exception as e:
        logger.exception(f"VK Kafka worker encountered a fatal error: {e}")
