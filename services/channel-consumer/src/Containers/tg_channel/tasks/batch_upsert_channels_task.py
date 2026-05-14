from typing import List, Dict, Any
import logging
from src.Containers.tg_channel.model.tg_channel_model import TgChannel

logger = logging.getLogger(__name__)


async def batch_upsert_channels_task(channels: List[Dict[str, Any]]) -> int:
    """
    Atomic task: Upsert multiple channels into DB using INSERT ON CONFLICT UPDATE.
    
    This task implements the upsert pattern:
    - If id exists: UPDATE the record with new data
    - If id doesn't exist: INSERT new record
    
    Args:
        channels: List of channel dictionaries with keys:
            - id: int (required, primary key)
            - name: str (optional)
            - type: str (optional)
    
    Returns:
        Number of channels successfully upserted
    
    Raises:
        Exception: If batch upsert fails
    """
    if not channels:
        logger.warning("Attempted batch upsert with empty channels list")
        return 0
    
    try:
        # Deduplicate channels by ID (keep last occurrence)
        unique_channels = {}
        for ch in channels:
            channel_id = ch.get("id")
            if channel_id:
                unique_channels[channel_id] = ch
        
        if len(unique_channels) < len(channels):
            logger.warning(
                f"Removed {len(channels) - len(unique_channels)} duplicate channel IDs from batch"
            )
        
        # Create TgChannel instances for batch insert
        channel_rows = [
            TgChannel(
                id=ch.get("id"),
                name=ch.get("name"),
                type=ch.get("type"),
            )
            for ch in unique_channels.values()
        ]
        
        # Piccolo batch insert with ON CONFLICT UPDATE
        # When id conflicts, update name and type
        await TgChannel.insert(*channel_rows).on_conflict(
            action="DO UPDATE",
            target=TgChannel.id,  # Conflict detection on id (primary key)
            values=[
                TgChannel.name,
                TgChannel.type,
            ]
        )
        
        upserted_count = len(channel_rows)
        logger.info(f"Successfully batch upserted {upserted_count} channels")
        
        return upserted_count
        
    except Exception as exc:
        logger.exception(f"Failed to batch upsert {len(channels)} channels: {exc}")
        raise

