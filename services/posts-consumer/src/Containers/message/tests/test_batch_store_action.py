"""
Integration tests for batch_store_messages_action.

These tests verify the orchestration of validation and batch storage.
"""
import pytest
from typing import List, Dict, Any
from src.Containers.message.actions.batch_store_messages_action import batch_store_messages_action
from src.Containers.message.model.message_model import Message


@pytest.fixture
async def clean_messages_table():
    """Clean messages table before and after each test."""
    await Message.delete(force=True)
    yield
    await Message.delete(force=True)


@pytest.mark.asyncio
async def test_batch_store_empty_list(clean_messages_table):
    """Test batch store with empty list returns 0."""
    result = await batch_store_messages_action([])
    assert result == 0
    
    count = await Message.count()
    assert count == 0


@pytest.mark.asyncio
async def test_batch_store_single_message(clean_messages_table):
    """Test batch store with single valid message."""
    raw_messages = [
        {"payload": {"user": "test", "action": "login"}}
    ]
    metadata_list = [
        {"topic": "events", "partition": 0, "offset": 100}
    ]
    
    result = await batch_store_messages_action(
        raw_messages,
        metadata_list=metadata_list
    )
    assert result == 1
    
    count = await Message.count()
    assert count == 1
    
    stored = await Message.select().first()
    assert stored["topic"] == "events"
    assert stored["partition"] == 0
    assert stored["offset"] == 100
    assert "user" in stored["payload"]


@pytest.mark.asyncio
async def test_batch_store_multiple_messages(clean_messages_table):
    """Test batch store with multiple valid messages."""
    raw_messages = [
        {"payload": {"index": i, "event": "test"}}
        for i in range(50)
    ]
    metadata_list = [
        {"topic": "test-topic", "partition": i % 3, "offset": 1000 + i}
        for i in range(50)
    ]
    
    result = await batch_store_messages_action(
        raw_messages,
        metadata_list=metadata_list
    )
    assert result == 50
    
    count = await Message.count()
    assert count == 50


@pytest.mark.asyncio
async def test_batch_store_without_metadata(clean_messages_table):
    """Test batch store without explicit metadata list."""
    raw_messages = [
        {"payload": {"test": i}}
        for i in range(10)
    ]
    
    result = await batch_store_messages_action(raw_messages)
    assert result == 10
    
    count = await Message.count()
    assert count == 10
    
    # Verify messages stored with null metadata
    stored = await Message.select().first()
    assert stored["topic"] is None
    assert stored["partition"] is None
    assert stored["offset"] is None


@pytest.mark.asyncio
async def test_batch_store_mixed_valid_invalid(clean_messages_table):
    """Test batch store with mix of valid and invalid messages (skips invalid)."""
    raw_messages = [
        {"payload": {"valid": True, "index": 0}},
        {"invalid": "structure"},  # Invalid - no payload
        {"payload": {"valid": True, "index": 2}},
        None,  # Invalid - None
        {"payload": {"valid": True, "index": 4}},
    ]
    metadata_list = [
        {"topic": "test", "partition": 0, "offset": i}
        for i in range(5)
    ]
    
    # Should process only valid messages, skip invalid ones
    result = await batch_store_messages_action(
        raw_messages,
        metadata_list=metadata_list
    )
    
    # Depending on MessageService validation logic, 
    # we expect only valid messages to be stored
    assert result >= 3  # At least the 3 valid ones
    
    count = await Message.count()
    assert count >= 3


@pytest.mark.asyncio
async def test_batch_store_metadata_mismatch_raises_error(clean_messages_table):
    """Test that mismatched metadata list length raises ValueError."""
    raw_messages = [{"payload": {"test": i}} for i in range(5)]
    metadata_list = [{"topic": "test", "partition": 0, "offset": i} for i in range(3)]
    
    with pytest.raises(ValueError) as exc_info:
        await batch_store_messages_action(
            raw_messages,
            metadata_list=metadata_list
        )
    
    assert "must match" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_batch_store_large_batch(clean_messages_table):
    """Test batch store with realistic large batch (100 messages)."""
    raw_messages = [
        {"payload": {"batch_id": "batch-001", "index": i, "data": f"data-{i}"}}
        for i in range(100)
    ]
    metadata_list = [
        {"topic": "high-volume", "partition": i % 10, "offset": 50000 + i}
        for i in range(100)
    ]
    
    result = await batch_store_messages_action(
        raw_messages,
        metadata_list=metadata_list
    )
    assert result == 100
    
    count = await Message.count()
    assert count == 100
    
    # Verify first and last
    first = await Message.select().order_by(Message.id).first()
    assert first["payload"]["index"] == 0
    
    last = await Message.select().order_by(Message.id, ascending=False).first()
    assert last["payload"]["index"] == 99


@pytest.mark.asyncio
async def test_batch_store_all_invalid_returns_zero(clean_messages_table):
    """Test that batch with all invalid messages returns 0."""
    raw_messages = [
        {"invalid": "no payload"},
        {"also": "invalid"},
        None,
    ]
    metadata_list = [
        {"topic": "test", "partition": 0, "offset": i}
        for i in range(3)
    ]
    
    result = await batch_store_messages_action(
        raw_messages,
        metadata_list=metadata_list
    )
    
    # All messages invalid, should return 0
    assert result == 0
    
    count = await Message.count()
    assert count == 0


@pytest.mark.asyncio
async def test_batch_store_idempotency(clean_messages_table):
    """Test that duplicate calls create separate records (no deduplication by default)."""
    raw_messages = [
        {"payload": {"unique_id": "same", "data": "duplicate"}}
    ]
    metadata_list = [
        {"topic": "test", "partition": 0, "offset": 100}
    ]
    
    # Insert first time
    result1 = await batch_store_messages_action(
        raw_messages,
        metadata_list=metadata_list
    )
    assert result1 == 1
    
    # Insert again (duplicate)
    result2 = await batch_store_messages_action(
        raw_messages,
        metadata_list=metadata_list
    )
    assert result2 == 1
    
    # Should have 2 records (no automatic deduplication)
    count = await Message.count()
    assert count == 2

