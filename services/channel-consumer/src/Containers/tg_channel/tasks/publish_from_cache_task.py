import json
import logging
from typing import Dict, Any
from aiokafka import AIOKafkaProducer
from src.Ship.config.settings import settings
from src.Containers.tg_channel.services.channel_objects_cache import get_channel_objects_cache

logger = logging.getLogger(__name__)


async def publish_from_cache_task(
    *,
    topic: str = "tg_channels_diff",
) -> Dict[str, Any]:
    """
    Atomic task: Read channel objects from cache and publish to Kafka.
    
    This task implements the cache-to-Kafka publishing workflow:
    1. Read all channel objects from cache
    2. Publish each channel to Kafka topic
    3. Clear cache after successful publish
    
    Args:
        topic: Kafka topic name (default: 'tg_channels_diff')
        
    Returns:
        Dictionary with publishing results:
        {
            "channels_read_from_cache": 100,
            "channels_published": 98,
            "publish_errors": 2,
            "cache_cleared": True
        }
        
    Raises:
        Exception: If cache operations or Kafka publishing fails critically
    """
    cache = get_channel_objects_cache()
    
    # Step 1: Read channels from cache
    try:
        channels = await cache.get_all_channels()
        
        if not channels:
            logger.info("No channels in cache to publish")
            return {
                "channels_read_from_cache": 0,
                "channels_published": 0,
                "publish_errors": 0,
                "cache_cleared": False
            }
        
        logger.info(f"Read {len(channels)} channels from cache for publishing")
        
    except Exception as exc:
        logger.exception(f"Failed to read channels from cache: {exc}")
        raise
    
    # Step 2: Publish to Kafka
    producer = None
    published_count = 0
    error_count = 0
    
    try:
        # Create Kafka producer
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        )
        
        await producer.start()
        logger.debug(f"Kafka producer started for topic '{topic}'")
        
        # Publish each channel
        for channel in channels:
            try:
                # Convert UUID to string for JSON serialization
                serializable_channel = {}
                for key, value in channel.items():
                    if hasattr(value, '__class__') and value.__class__.__name__ == 'UUID':
                        serializable_channel[key] = str(value)
                    else:
                        serializable_channel[key] = value
                
                # Add metadata
                message = {
                    **serializable_channel,
                    "_diff_type": "upserted_channel",
                    "_published_at": serializable_channel.get("validated_at"),
                    "_published_from": "cache"
                }
                
                # Send to Kafka
                await producer.send(topic, message)
                published_count += 1
                
                logger.debug(
                    f"Published channel {channel.get('id')} from cache to '{topic}'"
                )
                
            except Exception as exc:
                error_count += 1
                logger.error(
                    f"Failed to publish channel {channel.get('id')} from cache: {exc}"
                )
                # Continue with other channels
                continue
        
        # Ensure all messages are sent
        await producer.flush()
        
        logger.info(
            f"Published {published_count}/{len(channels)} channels from cache to '{topic}' "
            f"({error_count} errors)"
        )
        
    except Exception as exc:
        logger.exception(f"Failed to publish channels from cache: {exc}")
        raise
        
    finally:
        if producer:
            await producer.stop()
            logger.debug("Kafka producer stopped")
    
    # Step 3: Clear cache after successful publish
    cache_cleared = False
    if published_count > 0:
        try:
            cleared = await cache.clear()
            cache_cleared = True
            logger.info(f"Cleared {cleared} channels from cache after publishing")
        except Exception as exc:
            logger.error(f"Failed to clear cache after publishing: {exc}")
            # Don't raise - publishing was successful
    
    return {
        "channels_read_from_cache": len(channels),
        "channels_published": published_count,
        "publish_errors": error_count,
        "cache_cleared": cache_cleared
    }

