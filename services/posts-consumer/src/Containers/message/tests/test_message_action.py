# app/containers/messages/tests/test_message_action.py
import pytest
from src.Containers.message.actions.store_message_action import store_message_action
from src.Containers.message.model.message_model import create_tables


@pytest.mark.asyncio
async def test_store_message_action(tmp_path):
    await create_tables()
    payload = {"hello": "world"}
    result = await store_message_action(payload)
    assert result
    assert "id" in result
