from typing import Any, Dict, Optional
from pydantic import BaseModel, ValidationError, Field, field_validator
import logging

logger = logging.getLogger(__name__)


class VkGroupSchema(BaseModel):
    """
    Pydantic schema to validate VK group data from Kafka.
    
    Matches VK database schema:
    {
        "id": 12345678,          # required, integer (VK group ID)
        "name": "Group Name",
        "screen_name": "group_slug",
        "members_count": 1000
    }
    
    VK uses integer IDs for groups (unlike Telegram which uses UUIDs).
    """
    id: int = Field(..., description="VK Group ID (integer, required)")
    name: Optional[str] = Field(default=None, description="Group name")
    screen_name: Optional[str] = Field(default=None, description="Group screen name (URL slug)")
    members_count: Optional[int] = Field(default=None, ge=0, description="Number of members")
    photo_url: Optional[str] = Field(default=None, description="Group photo URL")
    cover_url: Optional[str] = Field(default=None, description="Group cover image URL")
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_and_convert_id(cls, v: Any) -> int:
        """
        Validate and convert id to integer.
        
        - If int: pass through
        - If string: convert to int
        - Otherwise: raise error
        """
        if isinstance(v, int):
            return v
        
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError as e:
                raise ValueError(f"Invalid integer string for id: {v}") from e
        
        raise ValueError(f"id must be integer or string, got {type(v).__name__}")
    
    @field_validator('members_count', mode='before')
    @classmethod
    def validate_members_count(cls, v: Any) -> Optional[int]:
        """
        Validate and convert members_count to integer.
        """
        if v is None:
            return None
        
        if isinstance(v, int):
            return v
        
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                return None
        
        return None


class VkGroupService:
    """
    Domain-level transformations and validations for VK groups.
    
    This service handles:
    - Validation of incoming group data from Kafka
    - Normalization and transformation of group attributes
    - Business logic for group data processing
    """

    @staticmethod
    def validate_and_transform(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate raw group dict and return normalized dict to be stored.
        
        Args:
            raw: Raw group data from Kafka
            
        Returns:
            Normalized group data ready for database storage
            
        Raises:
            ValidationError: On invalid input (missing required id)
            
        Example:
            >>> raw = {
            ...     "id": 12345678,
            ...     "name": "Example Group",
            ...     "screen_name": "example_group",
            ...     "members_count": 1000
            ... }
            >>> normalized = VkGroupService.validate_and_transform(raw)
            >>> normalized['id']
            12345678
        """
        try:
            # Parse and validate with Pydantic
            parsed = VkGroupSchema(**raw)
            
            # Convert to normalized dict
            normalized = {
                "id": parsed.id,
                "name": parsed.name,
                "screen_name": parsed.screen_name,
                "members_count": parsed.members_count,
                "photo_url": parsed.photo_url,
                "cover_url": parsed.cover_url,
            }
            
            return normalized

        except ValidationError as exc:
            logger.warning(f"Incoming VK group data failed validation: {exc}")
            raise
    
    @staticmethod
    def extract_group_ids(groups: list[Dict[str, Any]]) -> list[int]:
        """
        Extract group IDs from a list of group dictionaries.
        
        Args:
            groups: List of group data dictionaries
            
        Returns:
            List of unique group IDs (integers)
            
        Example:
            >>> groups = [
            ...     {"id": 123},
            ...     {"id": 456},
            ...     {"id": 123}  # duplicate
            ... ]
            >>> ids = VkGroupService.extract_group_ids(groups)
            >>> len(ids)
            2
        """
        group_ids = set()
        for group in groups:
            if "id" in group and isinstance(group["id"], int):
                group_ids.add(group["id"])
        return list(group_ids)
