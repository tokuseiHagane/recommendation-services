from typing import List, Dict, Any
import logging
from src.Containers.vk_group.services.vk_group_service import VkGroupService
from src.Containers.vk_group.tasks.batch_upsert_groups_task import batch_upsert_groups_task
from src.Containers.vk_group.tasks.cache_groups_task import cache_groups_task
from src.Containers.vk_group.tasks.publish_from_cache_task import publish_from_cache_task

logger = logging.getLogger(__name__)


async def batch_process_groups_action(
    raw_groups: List[Dict[str, Any]],
    *,
    metadata_list: List[Dict[str, Any]] | None = None,
    use_cache: bool = True,
    publish_diff: bool = True,
) -> Dict[str, Any]:
    """
    Business use case: Validate, upsert, cache and publish VK groups.
    
    This action orchestrates the complete VK group processing workflow:
    1. Validation and transformation of each group via Service
    2. Batch upsert of groups into groups table (INSERT ON CONFLICT UPDATE)
    3. Put all upserted groups into cache
    4. Read from cache and publish to vk_groups_diff topic
    5. Clear cache after successful publish
    
    CACHE WORKFLOW:
    - After upsert, ALL groups are placed into in-memory object cache
    - Groups are then read from cache and published to Kafka
    - Cache is cleared after successful publish
    - This ensures consistent publishing flow: DB -> Cache -> Kafka
    
    Args:
        raw_groups: List of raw group payloads from Kafka
        metadata_list: Optional list of metadata dicts (topic, partition, offset) 
                      corresponding to each group
        use_cache: Whether to use cache workflow (default: True)
        publish_diff: Whether to publish groups to vk_groups_diff (default: True)
    
    Returns:
        Dictionary with processing results:
        {
            "groups_upserted": 10,
            "groups_cached": 10,
            "groups_published_from_cache": 10,
            "publish_errors": 0,
            "cache_cleared": True,
            "validation_errors": 0,
            "total_received": 10
        }
    
    Raises:
        Exception: If critical processing fails
    """
    if not raw_groups:
        logger.warning("Attempted batch process with empty VK groups list")
        return {
            "groups_upserted": 0,
            "groups_cached": 0,
            "groups_published_from_cache": 0,
            "publish_errors": 0,
            "cache_cleared": False,
            "validation_errors": 0,
            "total_received": 0,
        }
    
    metadata_list = metadata_list or [{} for _ in raw_groups]
    
    # Ensure metadata_list matches raw_groups length
    if len(metadata_list) != len(raw_groups):
        logger.error(
            f"Metadata list length ({len(metadata_list)}) doesn't match "
            f"groups length ({len(raw_groups)})"
        )
        raise ValueError("Metadata list must match groups list length")
    
    try:
        # Step 1: Validate and transform all groups
        normalized_groups = []
        validation_errors = 0
        
        for idx, (raw_group, metadata) in enumerate(zip(raw_groups, metadata_list)):
            try:
                normalized = VkGroupService.validate_and_transform(raw_group)
                normalized_groups.append(normalized)
            except Exception as exc:
                validation_errors += 1
                logger.warning(
                    f"Failed to validate VK group at index {idx}: {exc}. Skipping."
                )
                # Skip invalid groups instead of failing entire batch
                continue
        
        if not normalized_groups:
            logger.error("All VK groups in batch failed validation")
            return {
                "groups_upserted": 0,
                "groups_cached": 0,
                "groups_published_from_cache": 0,
                "publish_errors": 0,
                "cache_cleared": False,
                "validation_errors": validation_errors,
                "total_received": len(raw_groups),
            }
        
        # Step 2: Batch upsert all validated groups
        upserted_count = await batch_upsert_groups_task(normalized_groups)
        
        logger.info(
            f"Batch upserted {upserted_count} VK groups "
            f"(validated: {len(normalized_groups)}, total: {len(raw_groups)})"
        )
        
        # Step 3: Put upserted groups into cache (if enabled)
        groups_cached = 0
        if use_cache and publish_diff:
            try:
                groups_cached = await cache_groups_task(normalized_groups)
                logger.info(f"Cached {groups_cached} VK groups after upsert")
            except Exception as exc:
                logger.error(f"Failed to cache VK groups: {exc}")
                # Continue processing even if caching fails
        
        # Step 4: Read from cache and publish to Kafka (if enabled)
        publish_result = {
            "groups_read_from_cache": 0,
            "groups_published": 0,
            "publish_errors": 0,
            "cache_cleared": False
        }
        
        if use_cache and publish_diff and groups_cached > 0:
            try:
                publish_result = await publish_from_cache_task()
                logger.info(
                    f"Published {publish_result['groups_published']} VK groups from cache "
                    f"(errors: {publish_result['publish_errors']})"
                )
            except Exception as exc:
                logger.error(f"Failed to publish VK groups from cache: {exc}")
                # Continue processing even if publish fails
        
        result = {
            "groups_upserted": upserted_count,
            "groups_cached": groups_cached,
            "groups_published_from_cache": publish_result["groups_published"],
            "publish_errors": publish_result["publish_errors"],
            "cache_cleared": publish_result["cache_cleared"],
            "validation_errors": validation_errors,
            "total_received": len(raw_groups),
        }
        
        logger.info(f"VK groups batch processing complete: {result}")
        
        return result
        
    except Exception as exc:
        logger.exception(f"Failed to batch process VK groups: {exc}")
        raise
