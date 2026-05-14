"""
Single message processing task.

⚠️  NOTE: This task is NOT used by Kafka worker (which uses batch processing).

This is the legacy single-message processing flow. It's kept for:
- HTTP API integration
- Testing purposes
- Backward compatibility

Kafka worker now uses batch_store_messages_action for better performance.
See: docs/BATCH_PROCESSING.md
"""
from typing import Dict, Any, Optional
import logging
from src.Containers.message.services.message_service import MessageService
from src.Containers.message.actions.store_message_action import store_message_action
from src.Containers.message.config.container_settings import container_settings

logger = logging.getLogger(__name__)


async def process_incoming_message(
    raw_message: Dict[str, Any],
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Orchestrator invoked by the Kafka port/worker.
    1. Validate & transform via Service
    2. Persist via Action
    3. Return stored DB row (or raise)
    """
    metadata = metadata or {}
    try:
        normalized = MessageService.validate_and_transform(raw_message)

        # example metadata keys: topic, partition, offset
        stored = await store_message_action(
            normalized["payload"],
            message_id=normalized.get("message_id"),
            topic=metadata.get("topic"),
            partition=metadata.get("partition"),
            offset=metadata.get("offset"),
        )

        logger.info(
            "Message stored (id=%s) topic=%s offset=%s",
            stored.get("id"),
            metadata.get("topic"),
            metadata.get("offset"),
        )

        return stored

    except Exception as exc:
        logger.exception("Failed to process incoming message: %s", exc)
        raise
