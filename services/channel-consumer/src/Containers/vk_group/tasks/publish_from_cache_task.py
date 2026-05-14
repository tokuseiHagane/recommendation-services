import json
import logging
from typing import Dict, Any
from aiokafka import AIOKafkaProducer
from src.Ship.config.settings import settings
from src.Containers.vk_group.services.group_objects_cache import get_group_objects_cache

logger = logging.getLogger(__name__)


async def publish_from_cache_task(
    *,
    topic: str = "vk_groups_diff",
) -> Dict[str, Any]:
    """
    Atomic task: Read VK group objects from cache and publish to Kafka.
    
    This task implements the cache-to-Kafka publishing workflow:
    1. Read all group objects from cache
    2. Publish each group to Kafka topic
    3. Clear cache after successful publish
    
    Args:
        topic: Kafka topic name (default: 'vk_groups_diff')
        
    Returns:
        Dictionary with publishing results:
        {
            "groups_read_from_cache": 100,
            "groups_published": 98,
            "publish_errors": 2,
            "cache_cleared": True
        }
        
    Raises:
        Exception: If cache operations or Kafka publishing fails critically
    """
    cache = get_group_objects_cache()
    
    # Step 1: Read groups from cache
    try:
        groups = await cache.get_all_groups()
        
        if not groups:
            logger.info("No VK groups in cache to publish")
            return {
                "groups_read_from_cache": 0,
                "groups_published": 0,
                "publish_errors": 0,
                "cache_cleared": False
            }
        
        logger.info(f"Read {len(groups)} VK groups from cache for publishing")
        
    except Exception as exc:
        logger.exception(f"Failed to read VK groups from cache: {exc}")
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
        
        # Publish each group
        for group in groups:
            try:
                # Prepare serializable message
                message = {
                    **group,
                    "_diff_type": "upserted_group",
                    "_published_from": "cache"
                }
                
                # Send to Kafka
                await producer.send(topic, message)
                published_count += 1
                
                logger.debug(
                    f"Published VK group {group.get('id')} from cache to '{topic}'"
                )
                
            except Exception as exc:
                error_count += 1
                logger.error(
                    f"Failed to publish VK group {group.get('id')} from cache: {exc}"
                )
                # Continue with other groups
                continue
        
        # Ensure all messages are sent
        await producer.flush()
        
        logger.info(
            f"Published {published_count}/{len(groups)} VK groups from cache to '{topic}' "
            f"({error_count} errors)"
        )
        
    except Exception as exc:
        logger.exception(f"Failed to publish VK groups from cache: {exc}")
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
            logger.info(f"Cleared {cleared} VK groups from cache after publishing")
        except Exception as exc:
            logger.error(f"Failed to clear VK groups cache after publishing: {exc}")
            # Don't raise - publishing was successful
    
    return {
        "groups_read_from_cache": len(groups),
        "groups_published": published_count,
        "publish_errors": error_count,
        "cache_cleared": cache_cleared
    }
