"""
Unit tests for batch_insert_messages_task.

These tests verify the atomic operation of batch inserting messages into DB.
"""
import pytest
from typing import List, Dict, Any
from src.Containers.message.tasks.batch_insert_messages_task import batch_insert_messages_task
from src.Containers.message.model.message_model import Message


@pytest.fixture
async def clean_messages_table():
    """Clean messages table before and after each test."""
    await Message.delete(force=True)
    yield
    await Message.delete(force=True)


@pytest.mark.asyncio
async def test_batch_insert_empty_list(clean_messages_table):
    """Test batch insert with empty list returns 0."""
    result = await batch_insert_messages_task([])
    assert result == 0
    
    # Verify no records in DB
    count = await Message.count()
    assert count == 0


@pytest.mark.asyncio
async def test_batch_insert_single_message(clean_messages_table):
    """Test batch insert with single message."""
    messages = [
        {
            "payload": {"test": "data"},
            "message_id": "msg-001",
            "topic": "test-topic",
            "partition": 0,
            "offset": 100,
        }
    ]
    
    result = await batch_insert_messages_task(messages)
    assert result == 1
    
    # Verify in DB
    count = await Message.count()
    assert count == 1
    
    stored = await Message.select().first()
    assert stored["message_id"] == "msg-001"
    assert stored["topic"] == "test-topic"
    assert stored["partition"] == 0
    assert stored["offset"] == 100
    assert stored["payload"] == {"test": "data"}
    assert stored["processed"] is False


@pytest.mark.asyncio
async def test_batch_insert_multiple_messages(clean_messages_table):
    """Test batch insert with multiple messages (typical batch scenario)."""
    messages = [
        {
            "payload": {"index": i, "data": f"message-{i}"},
            "message_id": f"msg-{i:03d}",
            "topic": "test-topic",
            "partition": i % 3,
            "offset": 1000 + i,
        }
        for i in range(100)
    ]
    
    result = await batch_insert_messages_task(messages)
    assert result == 100
    
    # Verify all in DB
    count = await Message.count()
    assert count == 100
    
    # Verify some specific records
    first = await Message.select().where(Message.message_id == "msg-000").first()
    assert first["payload"]["index"] == 0
    
    last = await Message.select().where(Message.message_id == "msg-099").first()
    assert last["payload"]["index"] == 99


@pytest.mark.asyncio
async def test_batch_insert_with_nulls(clean_messages_table):
    """Test batch insert with optional fields as None."""
    messages = [
        {
            "payload": {"minimal": True},
            "message_id": None,
            "topic": None,
            "partition": None,
            "offset": None,
        }
    ]
    
    result = await batch_insert_messages_task(messages)
    assert result == 1
    
    stored = await Message.select().first()
    assert stored["message_id"] is None
    assert stored["topic"] is None
    assert stored["partition"] is None
    assert stored["offset"] is None
    assert stored["payload"] == {"minimal": True}


@pytest.mark.asyncio
async def test_batch_insert_large_batch(clean_messages_table):
    """Test batch insert with larger batch size (performance test)."""
    messages = [
        {
            "payload": {"index": i},
            "message_id": f"large-msg-{i}",
            "topic": "large-topic",
            "partition": 0,
            "offset": i,
        }
        for i in range(500)
    ]
    
    result = await batch_insert_messages_task(messages)
    assert result == 500
    
    count = await Message.count()
    assert count == 500


@pytest.mark.asyncio
async def test_batch_insert_preserves_order(clean_messages_table):
    """Test that batch insert preserves insertion order (by received_at)."""
    messages = [
        {
            "payload": {"order": i},
            "message_id": f"order-{i}",
            "topic": "test",
            "partition": 0,
            "offset": i,
        }
        for i in range(10)
    ]
    
    await batch_insert_messages_task(messages)
    
    # Retrieve in order of insertion (by id or received_at)
    stored = await Message.select().order_by(Message.id)
    
    for i, record in enumerate(stored):
        assert record["payload"]["order"] == i
        assert record["message_id"] == f"order-{i}"

