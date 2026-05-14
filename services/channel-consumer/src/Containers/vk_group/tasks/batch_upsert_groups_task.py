from typing import List, Dict, Any
import logging
from src.Containers.vk_group.model.vk_group_model import VkGroup

logger = logging.getLogger(__name__)


async def batch_upsert_groups_task(groups: List[Dict[str, Any]]) -> int:
    """
    Atomic task: Upsert multiple VK groups into DB using INSERT ON CONFLICT UPDATE.
    
    This task implements the upsert pattern:
    - If id exists: UPDATE the record with new data
    - If id doesn't exist: INSERT new record
    
    IMPORTANT: Uses VK database engine, not the default Telegram one.
    
    Args:
        groups: List of group dictionaries with keys:
            - id: int (required, primary key)
            - name: str (optional)
            - screen_name: str (optional)
            - members_count: int (optional)
    
    Returns:
        Number of groups successfully upserted
    
    Raises:
        Exception: If batch upsert fails
    """
    if not groups:
        logger.warning("Attempted batch upsert with empty VK groups list")
        return 0
    
    try:
        # Deduplicate groups by ID (keep last occurrence)
        unique_groups = {}
        for group in groups:
            group_id = group.get("id")
            if group_id is not None:
                unique_groups[group_id] = group
        
        if len(unique_groups) < len(groups):
            logger.warning(
                f"Removed {len(groups) - len(unique_groups)} duplicate VK group IDs from batch"
            )
        
        if not unique_groups:
            return 0

        group_rows = [
            VkGroup(
                id=group.get("id"),
                name=group.get("name"),
                screen_name=group.get("screen_name"),
                members_count=group.get("members_count"),
                photo_url=group.get("photo_url"),
                cover_url=group.get("cover_url"),
            )
            for group in unique_groups.values()
        ]

        await VkGroup.insert(*group_rows).on_conflict(
            action="DO UPDATE",
            target=VkGroup.id,
            values=[
                VkGroup.name,
                VkGroup.screen_name,
                VkGroup.members_count,
                VkGroup.photo_url,
                VkGroup.cover_url,
            ],
        )

        upserted_count = len(group_rows)
        logger.info(f"Successfully batch upserted {upserted_count} VK groups")
        
        return upserted_count
        
    except Exception as exc:
        logger.exception(f"Failed to batch upsert {len(groups)} VK groups: {exc}")
        raise
