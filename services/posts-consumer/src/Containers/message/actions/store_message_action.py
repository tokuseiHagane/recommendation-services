"""
Single message insert action.

⚠️  NOTE: This action is NOT used by Kafka worker (which uses batch processing).

Current use cases:
- HTTP API for manual message insertion
- Priority/critical messages that bypass batch
- Testing and development
- Backward compatibility

For high-throughput Kafka processing, use batch_store_messages_action instead.
See: docs/BATCH_PROCESSING.md for details on batch processing.
"""
from typing import Any, Dict, Optional
import logging
from src.Containers.message.model.message_model import Message
from piccolo.columns import JSON
from piccolo.table import Insert
from src.Ship.config.settings import settings

logger = logging.getLogger(__name__)


async def store_message_action(
    payload: Dict[str, Any],
    *,
    message_id: Optional[str] = None,
    topic: Optional[str] = None,
    partition: Optional[int] = None,
    offset: Optional[int] = None,
) -> dict:
    """
    Persist a message to the DB.

    Returns the inserted row (as a dict) using `returning` to fetch values such as id.
    """
    # Build the Table instance to insert
    message_row = Message(
        message_id=message_id,
        topic=topic,
        partition=partition,
        offset=offset,
        payload=payload,
        processed=False,
    )

    try:
        # Use Piccolo's insert API. The `insert` returns a query object that can be awaited.
        # Using returning to fetch inserted id and stored values (supported by Piccolo/Postgres).
        query = Message.insert(message_row).returning(
            Message.id,
            Message.message_id,
            Message.topic,
            Message.partition,
            Message.offset,
            Message.payload,
            Message.processed,
        )

        result = await query  # this returns a list of inserted rows as dicts
        if isinstance(result, list) and result:
            return result[0]
        return {}

    except Exception as exc:
        logger.exception("Failed to store message: %s", exc)
        raise
