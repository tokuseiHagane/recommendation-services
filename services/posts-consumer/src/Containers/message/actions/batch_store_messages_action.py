from typing import List, Dict, Any
import logging
from src.Containers.message.services.message_service import MessageService
from src.Containers.message.tasks.batch_insert_messages_task import batch_insert_messages_task

logger = logging.getLogger(__name__)


async def batch_store_messages_action(
    raw_messages: List[Dict[str, Any]],
    *,
    metadata_list: List[Dict[str, Any]] | None = None,
) -> int:
    """
    Business use case: Validate and store multiple messages in a single batch.
    
    This action orchestrates:
    1. Validation and transformation of each message via Service
    2. Batch persistence via Task
    
    Args:
        raw_messages: List of raw message payloads from Kafka
        metadata_list: Optional list of metadata dicts (topic, partition, offset) 
                      corresponding to each message
    
    Returns:
        Number of messages successfully stored
    
    Raises:
        Exception: If validation or storage fails
    """
    if not raw_messages:
        logger.warning("Attempted batch store with empty messages list")
        return 0
    
    metadata_list = metadata_list or [{} for _ in raw_messages]
    
    # Ensure metadata_list matches raw_messages length
    if len(metadata_list) != len(raw_messages):
        logger.error(
            f"Metadata list length ({len(metadata_list)}) doesn't match "
            f"messages length ({len(raw_messages)})"
        )
        raise ValueError("Metadata list must match messages list length")
    
    try:
        # Validate and transform all messages
        normalized_messages = []
        for idx, (raw_msg, metadata) in enumerate(zip(raw_messages, metadata_list)):
            try:
                normalized = MessageService.validate_and_transform(raw_msg)
                normalized_messages.append({
                    "payload": normalized["payload"],
                    "message_id": normalized.get("message_id"),
                    "topic": metadata.get("topic"),
                    "partition": metadata.get("partition"),
                    "offset": metadata.get("offset"),
                })
            except Exception as exc:
                logger.warning(
                    f"Failed to validate message at index {idx}: {exc}. Skipping."
                )
                # Skip invalid messages instead of failing entire batch
                continue
        
        if not normalized_messages:
            logger.error("All messages in batch failed validation")
            return 0
        
        # Batch insert all validated messages
        inserted_count = await batch_insert_messages_task(normalized_messages)
        
        logger.info(
            f"Batch stored {inserted_count} messages "
            f"(validated: {len(normalized_messages)}, total: {len(raw_messages)})"
        )
        
        return inserted_count
        
    except Exception as exc:
        logger.exception(f"Failed to batch store messages: {exc}")
        raise

