from typing import List, Dict, Any
import logging
from src.Containers.message.model.message_model import Message

logger = logging.getLogger(__name__)


async def batch_insert_messages_task(messages: List[Dict[str, Any]]) -> int:
    """
    Atomic task: Insert multiple messages into DB in a single batch operation.
    
    Args:
        messages: List of message dictionaries with keys:
            - payload: Dict[str, Any]
            - message_id: Optional[str]
            - topic: Optional[str]
            - partition: Optional[int]
            - offset: Optional[int]
    
    Returns:
        Number of messages successfully inserted
    
    Raises:
        Exception: If batch insert fails
    """
    if not messages:
        logger.warning("Attempted batch insert with empty messages list")
        return 0
    
    try:
        # Create Message instances for batch insert
        message_rows = [
            Message(
                message_id=msg.get("message_id"),
                topic=msg.get("topic"),
                partition=msg.get("partition"),
                offset=msg.get("offset"),
                payload=msg.get("payload", {}),
                processed=False,
            )
            for msg in messages
        ]
        
        # Piccolo supports batch insert by passing multiple row instances
        # This generates a single INSERT statement with multiple VALUES
        await Message.insert(*message_rows)
        
        inserted_count = len(message_rows)
        logger.info(f"Successfully batch inserted {inserted_count} messages")
        
        return inserted_count
        
    except Exception as exc:
        logger.exception(f"Failed to batch insert {len(messages)} messages: {exc}")
        raise

