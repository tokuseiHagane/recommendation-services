from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, ValidationError, Field, field_validator
import logging

logger = logging.getLogger(__name__)


class TgChannelSchema(BaseModel):
    """
    Pydantic schema to validate Telegram channel data from Kafka.
    
    Matches database schema with UUID support:
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",  # optional, auto-generated if missing
        "name": "Channel Name",
        "type": "channel"
    }
    
    If id is not provided, it will be auto-generated as UUID4.
    """
    id: Optional[UUID] = Field(default=None, description="Channel ID (UUID, optional - auto-generated if not provided)")
    name: Optional[str] = Field(default=None, description="Channel name")
    type: Optional[str] = Field(default=None, max_length=255, description="Channel type")
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_and_convert_id(cls, v: Any) -> Optional[UUID]:
        """
        Validate and convert id to UUID.
        
        - If None or missing: will be auto-generated later
        - If string: convert to UUID
        - If UUID: pass through
        - Otherwise: raise error
        """
        if v is None:
            return None
        
        if isinstance(v, UUID):
            return v
        
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError as e:
                raise ValueError(f"Invalid UUID string: {v}") from e
        
        raise ValueError(f"id must be UUID or string, got {type(v).__name__}")


class TgChannelService:
    """
    Domain-level transformations and validations for Telegram channels.
    
    This service handles:
    - Validation of incoming channel data from Kafka
    - Normalization and transformation of channel attributes
    - Business logic for channel data processing
    """

    @staticmethod
    def validate_and_transform(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate raw channel dict and return normalized dict to be stored.
        
        Auto-generates UUID4 if id is not provided in the input.
        
        Args:
            raw: Raw channel data from Kafka
            
        Returns:
            Normalized channel data ready for database storage with UUID
            
        Raises:
            ValidationError: On invalid input
            
        Example with provided UUID:
            >>> raw = {
            ...     "id": "550e8400-e29b-41d4-a716-446655440000",
            ...     "name": "Example Channel",
            ...     "type": "channel"
            ... }
            >>> normalized = TgChannelService.validate_and_transform(raw)
            >>> isinstance(normalized['id'], UUID)
            True
            
        Example without UUID (auto-generated):
            >>> raw = {
            ...     "name": "Example Channel",
            ...     "type": "channel"
            ... }
            >>> normalized = TgChannelService.validate_and_transform(raw)
            >>> isinstance(normalized['id'], UUID)
            True
        """
        try:
            # Parse and validate with Pydantic
            parsed = TgChannelSchema(**raw)
            
            # Auto-generate UUID if not provided
            channel_id = parsed.id if parsed.id is not None else uuid4()
            
            # Convert to normalized dict
            normalized = {
                "id": channel_id,
                "name": parsed.name,
                "type": parsed.type,
            }
            
            return normalized

        except ValidationError as exc:
            logger.warning(f"Incoming channel data failed validation: {exc}")
            raise
    
    @staticmethod
    def extract_channel_ids(channels: list[Dict[str, Any]]) -> list[UUID]:
        """
        Extract channel IDs (UUIDs) from a list of channel dictionaries.
        
        Args:
            channels: List of channel data dictionaries
            
        Returns:
            List of unique channel UUIDs
            
        Example:
            >>> from uuid import UUID
            >>> id1 = UUID("550e8400-e29b-41d4-a716-446655440000")
            >>> id2 = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
            >>> channels = [
            ...     {"id": id1},
            ...     {"id": id2},
            ...     {"id": id1}  # duplicate
            ... ]
            >>> ids = TgChannelService.extract_channel_ids(channels)
            >>> len(ids)
            2
        """
        channel_ids = set()
        for ch in channels:
            if "id" in ch and isinstance(ch["id"], UUID):
                channel_ids.add(ch["id"])
        return list(channel_ids)

