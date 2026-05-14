# app/containers/messages/tests/test_integration.py
import pytest
from src.Containers.message.tasks.consume_messages_task import process_incoming_message
from src.Containers.message.model.message_model import create_tables


@pytest.mark.asyncio
async def test_process_incoming_message():
    await create_tables()

    raw_message = {"payload": {"key": "value"}, "message_id": "test-123"}
    result = await process_incoming_message(raw_message)
    assert result
    assert result["payload"]["key"] == "value"
