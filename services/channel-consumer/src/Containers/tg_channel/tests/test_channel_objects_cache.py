import pytest
import asyncio
from datetime import datetime, timedelta
from src.Containers.tg_channel.services.channel_objects_cache import (
    ChannelObjectsCache,
    get_channel_objects_cache,
    close_channel_objects_cache
)


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
class TestChannelObjectsCache:
    """Test channel objects cache."""
    
    async def test_put_and_get_channels(self):
        """Test putting channels into cache and retrieving them."""
        cache = ChannelObjectsCache()
        
        channels = [
            {"id": "uuid1", "name": "Channel 1", "type": "channel"},
            {"id": "uuid2", "name": "Channel 2", "type": "group"},
        ]
        
        # Put channels
        count = await cache.put_channels(channels)
        assert count == 2
        
        # Get all channels
        cached = await cache.get_all_channels()
        assert len(cached) == 2
        assert cached[0]["name"] in ["Channel 1", "Channel 2"]
    
    async def test_put_empty_list(self):
        """Test putting empty list returns 0."""
        cache = ChannelObjectsCache()
        
        count = await cache.put_channels([])
        assert count == 0
    
    async def test_get_single_channel(self):
        """Test getting a single channel by ID."""
        cache = ChannelObjectsCache()
        
        channels = [
            {"id": "uuid3", "name": "Test", "type": "channel"},
        ]
        
        await cache.put_channels(channels)
        
        # Get by ID
        channel = await cache.get_channel("uuid3")
        assert channel is not None
        assert channel["name"] == "Test"
        
        # Non-existent ID
        none_channel = await cache.get_channel("nonexistent")
        assert none_channel is None
    
    async def test_clear_cache(self):
        """Test clearing cache."""
        cache = ChannelObjectsCache()
        
        channels = [{"id": "uuid4", "name": "Test"}]
        await cache.put_channels(channels)
        
        # Verify cached
        assert await cache.size() == 1
        
        # Clear
        cleared = await cache.clear()
        assert cleared == 1
        assert await cache.size() == 0
    
    async def test_cache_overwrites_duplicate_ids(self):
        """Test that putting same ID overwrites previous value."""
        cache = ChannelObjectsCache()
        
        # First put
        channels1 = [{"id": "uuid5", "name": "Old Name"}]
        await cache.put_channels(channels1)
        
        # Second put with same ID
        channels2 = [{"id": "uuid5", "name": "New Name"}]
        await cache.put_channels(channels2)
        
        # Should have new value
        channel = await cache.get_channel("uuid5")
        assert channel["name"] == "New Name"
        
        # Still only 1 item
        assert await cache.size() == 1
    
    async def test_cache_ttl_expiration(self):
        """Test that cache expires after TTL."""
        # Create cache with 1 second TTL
        cache = ChannelObjectsCache(ttl_seconds=1)
        
        channels = [{"id": "uuid6", "name": "Test"}]
        await cache.put_channels(channels)
        
        # Immediately - should work
        cached = await cache.get_all_channels()
        assert len(cached) == 1
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired and cleared
        cached = await cache.get_all_channels()
        assert len(cached) == 0
    
    async def test_cache_stats(self):
        """Test getting cache statistics."""
        cache = ChannelObjectsCache()
        
        channels = [{"id": "uuid7", "name": "Test"}]
        await cache.put_channels(channels)
        
        stats = await cache.get_stats()
        
        assert stats["total_channels"] == 1
        assert stats["backend"] == "in-memory-objects"
        assert stats["last_update"] is not None
        assert isinstance(stats["is_expired"], bool)
    
    async def test_put_channel_without_id(self):
        """Test that channels without ID are skipped."""
        cache = ChannelObjectsCache()
        
        channels = [
            {"name": "No ID"},  # Missing id
            {"id": "uuid8", "name": "Has ID"},
        ]
        
        count = await cache.put_channels(channels)
        
        # Only 1 should be cached
        assert count == 1
        assert await cache.size() == 1
    
    async def test_singleton_instance(self):
        """Test that get_channel_objects_cache returns singleton."""
        cache1 = get_channel_objects_cache()
        cache2 = get_channel_objects_cache()
        
        assert cache1 is cache2
        
        # Put in cache1
        await cache1.put_channels([{"id": "uuid9", "name": "Test"}])
        
        # Should be visible in cache2
        assert await cache2.size() == 1
        
        # Cleanup
        await close_channel_objects_cache()
    
    async def test_close_cache(self):
        """Test closing/cleaning up cache."""
        cache = get_channel_objects_cache()
        await cache.put_channels([{"id": "uuid10", "name": "Test"}])
        
        # Close
        await close_channel_objects_cache()
        
        # New instance should be empty
        new_cache = get_channel_objects_cache()
        assert await new_cache.size() == 0
        
        # Cleanup
        await close_channel_objects_cache()

