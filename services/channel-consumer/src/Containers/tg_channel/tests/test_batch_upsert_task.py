import pytest
import asyncio
from src.Containers.tg_channel.model.tg_channel_model import TgChannel, create_tables
from src.Containers.tg_channel.tasks.batch_upsert_channels_task import (
    batch_upsert_channels_task,
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
class TestBatchUpsertChannelsTask:
    """Test batch upsert channels task."""
    
    async def test_batch_upsert_new_channels(self):
        """Test inserting new channels."""
        channels = [
            {
                "channel_id": 111111111,
                "channel_username": "channel1",
                "channel_title": "Channel 1",
                "members_count": 100,
            },
            {
                "channel_id": 222222222,
                "channel_username": "channel2",
                "channel_title": "Channel 2",
                "members_count": 200,
            },
        ]
        
        count = await batch_upsert_channels_task(channels)
        
        assert count == 2
        
        # Verify channels were inserted
        ch1 = await TgChannel.select().where(
            TgChannel.channel_id == 111111111
        ).first()
        assert ch1["channel_username"] == "channel1"
        assert ch1["members_count"] == 100
        
        ch2 = await TgChannel.select().where(
            TgChannel.channel_id == 222222222
        ).first()
        assert ch2["channel_username"] == "channel2"
        assert ch2["members_count"] == 200
    
    async def test_batch_upsert_update_existing(self):
        """Test updating existing channels (upsert)."""
        # Insert initial channel
        await TgChannel.insert(
            TgChannel(
                channel_id=333333333,
                channel_username="old_username",
                channel_title="Old Title",
                members_count=500,
            )
        )
        
        # Upsert with updated data
        channels = [
            {
                "channel_id": 333333333,
                "channel_username": "new_username",
                "channel_title": "New Title",
                "members_count": 1000,
            }
        ]
        
        count = await batch_upsert_channels_task(channels)
        
        assert count == 1
        
        # Verify channel was updated
        ch = await TgChannel.select().where(
            TgChannel.channel_id == 333333333
        ).first()
        assert ch["channel_username"] == "new_username"
        assert ch["channel_title"] == "New Title"
        assert ch["members_count"] == 1000
    
    async def test_batch_upsert_mixed(self):
        """Test upserting mix of new and existing channels."""
        # Insert one existing channel
        await TgChannel.insert(
            TgChannel(
                channel_id=444444444,
                channel_username="existing",
                members_count=100,
            )
        )
        
        # Upsert with one existing and one new
        channels = [
            {
                "channel_id": 444444444,
                "channel_username": "updated_existing",
                "members_count": 200,
            },
            {
                "channel_id": 555555555,
                "channel_username": "new_channel",
                "members_count": 300,
            },
        ]
        
        count = await batch_upsert_channels_task(channels)
        
        assert count == 2
        
        # Verify both channels
        ch1 = await TgChannel.select().where(
            TgChannel.channel_id == 444444444
        ).first()
        assert ch1["channel_username"] == "updated_existing"
        assert ch1["members_count"] == 200
        
        ch2 = await TgChannel.select().where(
            TgChannel.channel_id == 555555555
        ).first()
        assert ch2["channel_username"] == "new_channel"
        assert ch2["members_count"] == 300
    
    async def test_batch_upsert_empty_list(self):
        """Test upserting empty list."""
        count = await batch_upsert_channels_task([])
        assert count == 0
    
    async def test_batch_upsert_minimal_data(self):
        """Test upserting with minimal required data."""
        channels = [
            {"channel_id": 666666666},
        ]
        
        count = await batch_upsert_channels_task(channels)
        
        assert count == 1
        
        # Verify channel was inserted with defaults
        ch = await TgChannel.select().where(
            TgChannel.channel_id == 666666666
        ).first()
        assert ch["channel_id"] == 666666666
        assert ch["channel_username"] is None
        assert ch["is_active"] is True
    
    async def test_batch_upsert_preserves_created_at(self):
        """Test that upsert preserves created_at timestamp."""
        # Insert initial channel
        await TgChannel.insert(
            TgChannel(
                channel_id=777777777,
                channel_username="test",
            )
        )
        
        # Get original created_at
        original = await TgChannel.select().where(
            TgChannel.channel_id == 777777777
        ).first()
        original_created_at = original["created_at"]
        
        # Wait a bit and upsert
        await asyncio.sleep(0.1)
        
        channels = [
            {
                "channel_id": 777777777,
                "channel_username": "updated",
            }
        ]
        
        await batch_upsert_channels_task(channels)
        
        # Verify created_at is unchanged
        updated = await TgChannel.select().where(
            TgChannel.channel_id == 777777777
        ).first()
        assert updated["created_at"] == original_created_at
        assert updated["channel_username"] == "updated"

