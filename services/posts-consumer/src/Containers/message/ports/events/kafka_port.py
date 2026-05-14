"""
Kafka Port - Single message handler.

⚠️  NOTE: This port is NOT used by the current Kafka worker implementation.

The Kafka worker (src/Ship/tasks/kafka_worker.py) now uses batch processing
directly via batch_store_messages_action for better performance.

This port is kept for:
- Potential HTTP API integration
- Alternative processing flows
- Testing purposes
- Backward compatibility

See: docs/BATCH_PROCESSING.md for current implementation details.
"""
import logging
from typing import Any, Dict
from src.Containers.message.tasks.consume_messages_task import process_incoming_message

logger = logging.getLogger(__name__)


async def handle_kafka_message(record: Dict[str, Any], *, di: Any | None = None) -> None:
    """
    Handle an incoming Kafka record (LEGACY - single message processing).

    ⚠️  Not used by Kafka worker. See batch processing implementation instead.

    The record dict is expected to have:
      - value: parsed message payload (dict)
      - metadata: {topic, partition, offset}
    """
    try:
        payload = record.get("value") if "value" in record else record
        metadata = record.get("metadata", {})

        logger.debug(f"Dispatching message to Messages container: {metadata}")
        # For now we don't use DI inside task; reserved for future needs
        await process_incoming_message(payload, metadata=metadata)

    except Exception as exc:
        logger.exception(f"KafkaPort failed to process message: {exc}")
        raise
