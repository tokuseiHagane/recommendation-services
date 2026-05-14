import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from src.Containers.tg_channel.model.tg_channel_model import TgChannel, create_tables
from src.Containers.tg_channel.actions.batch_process_channels_action import (
    batch_process_channels_action,
)


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def setup_database():
    """Setup database tables before tests."""
    await create_tables()
    yield
    # Cleanup after tests
    await TgChannel.delete(force=True)


@pytest.mark.asyncio
class TestBatchProcessChannelsActionWithCache:
    """Test batch process channels action with new cache workflow."""
    
    async def test_batch_process_with_cache_workflow(self):
        """Test complete workflow: upsert → cache → publish from cache."""
        raw_channels = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440010",
                "name": "Test Channel 1",
                "type": "channel",
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440011",
                "name": "Test Channel 2",
                "type": "group",
            },
        ]
        
        # Mock Kafka producer
        with patch('src.Containers.tg_channel.tasks.publish_from_cache_task.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            # Process channels
            result = await batch_process_channels_action(
                raw_channels,
                use_cache=True,
                publish_diff=True,
            )
            
            # Verify workflow
            assert result["channels_upserted"] == 2
            assert result["channels_cached"] == 2
            assert result["channels_published_from_cache"] == 2
            assert result["publish_errors"] == 0
            assert result["cache_cleared"] is True
            assert result["validation_errors"] == 0
            
            # Verify Kafka was used
            assert mock_producer.start.called
            assert mock_producer.send.call_count == 2
            assert mock_producer.flush.called
            assert mock_producer.stop.called
            
            # Verify message metadata
            first_call = mock_producer.send.call_args_list[0]
            message = first_call[0][1]
            assert message["_diff_type"] == "upserted_channel"
            assert message["_published_from"] == "cache"
    
    async def test_batch_process_with_cache_disabled(self):
        """Test that cache is not used when use_cache=False."""
        raw_channels = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440012",
                "name": "No Cache",
            },
        ]
        
        with patch('src.Containers.tg_channel.tasks.publish_from_cache_task.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            # Process without cache
            result = await batch_process_channels_action(
                raw_channels,
                use_cache=False,
                publish_diff=True,
            )
            
            # Verify channels upserted but not cached
            assert result["channels_upserted"] == 1
            assert result["channels_cached"] == 0
            assert result["channels_published_from_cache"] == 0
            
            # Kafka should NOT be called
            assert not mock_producer.start.called
    
    async def test_batch_process_with_publish_disabled(self):
        """Test that publishing is skipped when publish_diff=False."""
        raw_channels = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440013",
                "name": "No Publish",
            },
        ]
        
        with patch('src.Containers.tg_channel.tasks.publish_from_cache_task.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            # Process without publishing
            result = await batch_process_channels_action(
                raw_channels,
                use_cache=True,
                publish_diff=False,
            )
            
            # Verify upserted but not cached/published
            assert result["channels_upserted"] == 1
            assert result["channels_cached"] == 0
            assert result["channels_published_from_cache"] == 0
    
    async def test_batch_process_continues_on_cache_failure(self):
        """Test that processing continues even if caching fails."""
        raw_channels = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440014",
                "name": "Test",
            },
        ]
        
        # Mock cache to fail
        with patch('src.Containers.tg_channel.tasks.cache_channels_task.get_channel_objects_cache') as mock_cache:
            mock_cache.return_value.put_channels.side_effect = Exception("Cache failed")
            
            # Process should succeed despite cache failure
            result = await batch_process_channels_action(
                raw_channels,
                use_cache=True,
                publish_diff=True,
            )
            
            # Verify upserted but not cached
            assert result["channels_upserted"] == 1
            assert result["channels_cached"] == 0
    
    async def test_batch_process_continues_on_publish_failure(self):
        """Test that processing continues even if publishing fails."""
        raw_channels = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440015",
                "name": "Test",
            },
        ]
        
        # Mock Kafka to fail
        with patch('src.Containers.tg_channel.tasks.publish_from_cache_task.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer.start.side_effect = Exception("Kafka unavailable")
            mock_producer_class.return_value = mock_producer
            
            # Process should succeed despite Kafka failure
            result = await batch_process_channels_action(
                raw_channels,
                use_cache=True,
                publish_diff=True,
            )
            
            # Verify upserted and cached but not published
            assert result["channels_upserted"] == 1
            assert result["channels_cached"] == 1
            assert result["channels_published_from_cache"] == 0
    
    async def test_batch_process_only_valid_channels(self):
        """Test that only valid channels go through workflow."""
        raw_channels = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440016",
                "name": "Valid",
            },
            {
                # Invalid: missing id
                "name": "Invalid - No ID",
            },
        ]
        
        with patch('src.Containers.tg_channel.tasks.publish_from_cache_task.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            result = await batch_process_channels_action(
                raw_channels,
                use_cache=True,
                publish_diff=True,
            )
            
            # Only valid channel processed
            assert result["channels_upserted"] == 1
            assert result["channels_cached"] == 1
            assert result["channels_published_from_cache"] == 1
            assert result["validation_errors"] == 1
            
            # Only 1 message sent
            assert mock_producer.send.call_count == 1
    
    async def test_batch_process_empty_channels(self):
        """Test empty channel list."""
        result = await batch_process_channels_action(
            [],
            use_cache=True,
            publish_diff=True,
        )
        
        assert result["channels_upserted"] == 0
        assert result["channels_cached"] == 0
        assert result["channels_published_from_cache"] == 0
        assert result["cache_cleared"] is False
    
    async def test_batch_process_all_invalid_channels(self):
        """Test batch with all invalid channels."""
        raw_channels = [
            {"name": "No ID 1"},
            {"name": "No ID 2"},
        ]
        
        result = await batch_process_channels_action(
            raw_channels,
            use_cache=True,
            publish_diff=True,
        )
        
        assert result["channels_upserted"] == 0
        assert result["channels_cached"] == 0
        assert result["channels_published_from_cache"] == 0
        assert result["validation_errors"] == 2
        assert result["total_received"] == 2

