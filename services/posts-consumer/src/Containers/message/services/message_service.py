from typing import Any, Dict, Optional
from pydantic import BaseModel, ValidationError, Field
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class IncomingMessageSchema(BaseModel):
    """
    Pydantic schema to validate the expected structure from Kafka.
    Adapt fields to match your real message shape.
    """
    message_id: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default=None)
    payload: dict


class MessageService:
    """
    Domain-level transformations and validations for messages.
    """

    @staticmethod
    def validate_and_transform(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate raw message dict and return normalized dict to be stored.
        Raises ValidationError on invalid input.
        """
        try:
            # The schema expects top-level 'payload' key containing the real payload.
            # If your messages already are the actual payload, adapt accordingly.
            # For flexibility, accept both: payload in raw['payload'] or raw itself.
            if "payload" not in raw:
                candidate = {"payload": raw}
            else:
                candidate = raw

            parsed = IncomingMessageSchema(**candidate)

            normalized = {
                "message_id": parsed.message_id,
                "payload": parsed.payload,
                "created_at": parsed.created_at,
                "validated_at": datetime.utcnow(),
            }
            return normalized

        except ValidationError as exc:
            logger.warning("Incoming message failed validation: %s", exc)
            raise
