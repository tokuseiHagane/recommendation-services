import pytest
from pydantic import ValidationError
from src.Containers.tg_channel.services.tg_channel_service import (
    TgChannelService,
    TgChannelSchema,
)


class TestTgChannelSchema:
    """Test Pydantic schema validation."""
    
    def test_valid_channel_data(self):
        """Test validation with valid channel data."""
        data = {
            "channel_id": 123456789,
            "channel_username": "test_channel",
            "channel_title": "Test Channel",
            "channel_type": "channel",
            "members_count": 1000,
            "is_active": True,
        }
        
        schema = TgChannelSchema(**data)
        assert schema.channel_id == 123456789
        assert schema.channel_username == "test_channel"
        assert schema.channel_title == "Test Channel"
        assert schema.members_count == 1000
        assert schema.is_active is True
    
    def test_minimal_channel_data(self):
        """Test validation with only required fields."""
        data = {"channel_id": 123456789}
        
        schema = TgChannelSchema(**data)
        assert schema.channel_id == 123456789
        assert schema.channel_username is None
        assert schema.is_active is True  # default value
    
    def test_username_cleanup(self):
        """Test that @ is removed from username."""
        data = {
            "channel_id": 123456789,
            "channel_username": "@test_channel",
        }
        
        schema = TgChannelSchema(**data)
        assert schema.channel_username == "test_channel"
    
    def test_invalid_channel_id(self):
        """Test validation fails with invalid channel_id."""
        data = {"channel_id": -123}
        
        with pytest.raises(ValidationError) as exc_info:
            TgChannelSchema(**data)
        
        assert "channel_id must be positive" in str(exc_info.value)
    
    def test_missing_channel_id(self):
        """Test validation fails without channel_id."""
        data = {"channel_username": "test"}
        
        with pytest.raises(ValidationError):
            TgChannelSchema(**data)
    
    def test_negative_members_count(self):
        """Test validation fails with negative members_count."""
        data = {
            "channel_id": 123456789,
            "members_count": -100,
        }
        
        with pytest.raises(ValidationError):
            TgChannelSchema(**data)


class TestTgChannelService:
    """Test TgChannelService business logic."""
    
    def test_validate_and_transform_success(self):
        """Test successful validation and transformation."""
        raw = {
            "channel_id": 123456789,
            "channel_username": "@test_channel",
            "channel_title": "Test Channel",
            "members_count": 1000,
        }
        
        normalized = TgChannelService.validate_and_transform(raw)
        
        assert normalized["channel_id"] == 123456789
        assert normalized["channel_username"] == "test_channel"  # @ removed
        assert normalized["channel_title"] == "Test Channel"
        assert normalized["members_count"] == 1000
        assert "validated_at" in normalized
    
    def test_validate_and_transform_minimal(self):
        """Test transformation with minimal data."""
        raw = {"channel_id": 123456789}
        
        normalized = TgChannelService.validate_and_transform(raw)
        
        assert normalized["channel_id"] == 123456789
        assert normalized["channel_username"] is None
        assert normalized["is_active"] is True
    
    def test_validate_and_transform_invalid(self):
        """Test validation fails with invalid data."""
        raw = {"channel_id": -123}
        
        with pytest.raises(ValidationError):
            TgChannelService.validate_and_transform(raw)
    
    def test_extract_channel_ids(self):
        """Test extracting unique channel IDs from list."""
        channels = [
            {"channel_id": 123},
            {"channel_id": 456},
            {"channel_id": 123},  # duplicate
            {"channel_id": 789},
            {"other_field": "value"},  # no channel_id
        ]
        
        ids = TgChannelService.extract_channel_ids(channels)
        
        assert len(ids) == 3
        assert 123 in ids
        assert 456 in ids
        assert 789 in ids
    
    def test_extract_channel_ids_empty(self):
        """Test extracting from empty list."""
        ids = TgChannelService.extract_channel_ids([])
        assert ids == []
    
    def test_extract_channel_ids_no_valid(self):
        """Test extracting when no valid channel_ids."""
        channels = [
            {"other_field": "value"},
            {"channel_id": "not_an_int"},
        ]
        
        ids = TgChannelService.extract_channel_ids(channels)
        assert ids == []

