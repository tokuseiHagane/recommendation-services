from typing import List, Dict, Any
import logging
from src.Containers.tg_channel.services.tg_channel_service import TgChannelService
from src.Containers.tg_channel.tasks.batch_upsert_channels_task import batch_upsert_channels_task
from src.Containers.tg_channel.tasks.cache_channels_task import cache_channels_task
from src.Containers.tg_channel.tasks.publish_from_cache_task import publish_from_cache_task

logger = logging.getLogger(__name__)


async def batch_process_channels_action(
    raw_channels: List[Dict[str, Any]],
    *,
    metadata_list: List[Dict[str, Any]] | None = None,
    use_cache: bool = True,
    publish_diff: bool = True,
) -> Dict[str, Any]:
    """
    Business use case: Validate, upsert, cache and publish channels.
    
    This action orchestrates the complete channel processing workflow:
    1. Validation and transformation of each channel via Service
    2. Batch upsert of channels into channels table (INSERT ON CONFLICT UPDATE)
    3. Put all upserted channels into cache
    4. Read from cache and publish to tg_channels_diff topic
    5. Clear cache after successful publish
    
    NEW CACHE WORKFLOW:
    - After upsert, ALL channels are placed into in-memory object cache
    - Channels are then read from cache and published to Kafka
    - Cache is cleared after successful publish
    - This ensures consistent publishing flow: DB → Cache → Kafka
    
    Args:
        raw_channels: List of raw channel payloads from Kafka
        metadata_list: Optional list of metadata dicts (topic, partition, offset) 
                      corresponding to each channel
        use_cache: Whether to use cache workflow (default: True)
        publish_diff: Whether to publish channels to tg_channels_diff (default: True)
    
    Returns:
        Dictionary with processing results:
        {
            "channels_upserted": 10,
            "channels_cached": 10,
            "channels_published_from_cache": 10,
            "publish_errors": 0,
            "cache_cleared": True,
            "validation_errors": 0,
            "total_received": 10
        }
    
    Raises:
        Exception: If critical processing fails
    """
    if not raw_channels:
        logger.warning("Attempted batch process with empty channels list")
        return {
            "channels_upserted": 0,
            "channels_cached": 0,
            "channels_published_from_cache": 0,
            "publish_errors": 0,
            "cache_cleared": False,
            "validation_errors": 0,
            "total_received": 0,
        }
    
    metadata_list = metadata_list or [{} for _ in raw_channels]
    
    # Ensure metadata_list matches raw_channels length
    if len(metadata_list) != len(raw_channels):
        logger.error(
            f"Metadata list length ({len(metadata_list)}) doesn't match "
            f"channels length ({len(raw_channels)})"
        )
        raise ValueError("Metadata list must match channels list length")
    
    try:
        # Step 1: Validate and transform all channels
        normalized_channels = []
        validation_errors = 0
        
        for idx, (raw_ch, metadata) in enumerate(zip(raw_channels, metadata_list)):
            try:
                normalized = TgChannelService.validate_and_transform(raw_ch)
                normalized_channels.append(normalized)
            except Exception as exc:
                validation_errors += 1
                logger.warning(
                    f"Failed to validate channel at index {idx}: {exc}. Skipping."
                )
                # Skip invalid channels instead of failing entire batch
                continue
        
        if not normalized_channels:
            logger.error("All channels in batch failed validation")
            return {
                "channels_upserted": 0,
                "channels_cached": 0,
                "channels_published_from_cache": 0,
                "publish_errors": 0,
                "cache_cleared": False,
                "validation_errors": validation_errors,
                "total_received": len(raw_channels),
            }
        
        # Step 2: Batch upsert all validated channels
        upserted_count = await batch_upsert_channels_task(normalized_channels)
        
        logger.info(
            f"Batch upserted {upserted_count} channels "
            f"(validated: {len(normalized_channels)}, total: {len(raw_channels)})"
        )
        
        # Step 3: Put upserted channels into cache (if enabled)
        channels_cached = 0
        if use_cache and publish_diff:
            try:
                channels_cached = await cache_channels_task(normalized_channels)
                logger.info(f"Cached {channels_cached} channels after upsert")
            except Exception as exc:
                logger.error(f"Failed to cache channels: {exc}")
                # Continue processing even if caching fails
        
        # Step 4: Read from cache and publish to Kafka (if enabled)
        publish_result = {
            "channels_read_from_cache": 0,
            "channels_published": 0,
            "publish_errors": 0,
            "cache_cleared": False
        }
        
        if use_cache and publish_diff and channels_cached > 0:
            try:
                publish_result = await publish_from_cache_task()
                logger.info(
                    f"Published {publish_result['channels_published']} channels from cache "
                    f"(errors: {publish_result['publish_errors']})"
                )
            except Exception as exc:
                logger.error(f"Failed to publish from cache: {exc}")
                # Continue processing even if publish fails
        
        result = {
            "channels_upserted": upserted_count,
            "channels_cached": channels_cached,
            "channels_published_from_cache": publish_result["channels_published"],
            "publish_errors": publish_result["publish_errors"],
            "cache_cleared": publish_result["cache_cleared"],
            "validation_errors": validation_errors,
            "total_received": len(raw_channels),
        }
        
        logger.info(f"Batch processing complete: {result}")
        
        return result
        
    except Exception as exc:
        logger.exception(f"Failed to batch process channels: {exc}")
        raise
