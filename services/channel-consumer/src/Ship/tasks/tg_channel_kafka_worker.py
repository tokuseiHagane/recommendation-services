import asyncio
import json
import logging
from typing import Any, List, Dict
from aiokafka import AIOKafkaConsumer

from src.Ship.config.settings import settings
from src.Ship.config.kafka_config import KafkaConfig
from src.Containers.tg_channel.actions.batch_process_channels_action import batch_process_channels_action

logger = logging.getLogger(__name__)


async def flush_channel_batch(
    batch_channels: List[Dict[str, Any]],
    batch_metadata: List[Dict[str, Any]]
) -> None:
    """
    Flush accumulated batch of channels to database.
    
    This function:
    1. Validates and upserts channels
    2. Creates message tables for each channel
    
    Args:
        batch_channels: List of raw channel payloads
        batch_metadata: List of corresponding metadata dicts
    """
    if not batch_channels:
        return
    
    try:
        result = await batch_process_channels_action(
            batch_channels,
            metadata_list=batch_metadata,
            use_cache=True,  # Enable cache workflow
            publish_diff=True,  # Publish from cache to Kafka
        )
        logger.info(
            f"Flushed channel batch: {result['channels_upserted']} upserted, "
            f"{result['channels_cached']} cached, "
            f"{result['channels_published_from_cache']} published from cache, "
            f"{result['publish_errors']} publish errors, "
            f"{result['validation_errors']} validation errors "
            f"(out of {result['total_received']} received)"
        )
    except Exception as exc:
        logger.exception(f"Failed to flush batch of {len(batch_channels)} channels: {exc}")
        # In production, you might want to implement retry logic or dead letter queue


async def consume_tg_channels(di: Any | None = None, initialize_cache: bool = True) -> None:
    """
    Continuously consume Telegram channels from Kafka with batch processing.
    
    Channels are accumulated in a buffer and processed in batches when either:
    - Batch size reaches BATCH_SIZE (default 100)
    - Timeout of BATCH_TIMEOUT seconds elapses (default 5s)
    
    For each batch:
    1. Validate channel data
    2. Upsert channels to channels table (INSERT ON CONFLICT UPDATE)
    3. Cache upserted channels in memory
    4. Publish all channels from cache to tg_channels_diff topic
    5. Clear cache after successful publish
    
    Args:
        di: optional DI container (Dishka), reserved for future use
        initialize_cache: deprecated parameter, kept for compatibility
    """
    kafka_conf = KafkaConfig()
    batch_size = settings.BATCH_SIZE
    batch_timeout = settings.BATCH_TIMEOUT
    
    # Override topic to tg_channels
    topic = "tg_channels"

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=kafka_conf.bootstrap_servers,
        group_id=kafka_conf.group_id,
        enable_auto_commit=kafka_conf.enable_auto_commit,
        auto_offset_reset=kafka_conf.auto_offset_reset,
        consumer_timeout_ms=kafka_conf.consumer_timeout_ms,
    )

    await consumer.start()
    logger.info(
        f"Kafka consumer started for topic: {topic} "
        f"(batch_size={batch_size}, batch_timeout={batch_timeout}s)"
    )

    # Batch buffers
    batch_channels: List[Dict[str, Any]] = []
    batch_metadata: List[Dict[str, Any]] = []
    last_flush_time = asyncio.get_event_loop().time()

    try:
        async for msg in consumer:
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                logger.debug(f"Received channel: {payload.get('channel_id', 'unknown')}")

                # Add to batch
                batch_channels.append(payload)
                batch_metadata.append({
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                })

                current_time = asyncio.get_event_loop().time()
                time_since_last_flush = current_time - last_flush_time

                # Flush if batch is full or timeout elapsed
                should_flush = (
                    len(batch_channels) >= batch_size or
                    time_since_last_flush >= batch_timeout
                )

                if should_flush:
                    await flush_channel_batch(batch_channels, batch_metadata)
                    # Clear buffers
                    batch_channels.clear()
                    batch_metadata.clear()
                    last_flush_time = asyncio.get_event_loop().time()

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode Kafka message: {e}")
            except Exception as e:
                logger.exception(f"Error while processing channel: {e}")

    except asyncio.CancelledError:
        logger.info("Kafka consumer loop cancelled, shutting down...")
        # Flush remaining channels before shutdown
        if batch_channels:
            logger.info(f"Flushing {len(batch_channels)} remaining channels before shutdown...")
            await flush_channel_batch(batch_channels, batch_metadata)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped.")


def start_tg_channel_kafka_worker() -> None:
    """Entry point to start the Kafka consumer worker for tg_channels topic."""
    try:
        asyncio.run(consume_tg_channels())
    except KeyboardInterrupt:
        logger.info("Kafka worker interrupted by user.")
    except Exception as e:
        logger.exception(f"Kafka worker encountered a fatal error: {e}")

