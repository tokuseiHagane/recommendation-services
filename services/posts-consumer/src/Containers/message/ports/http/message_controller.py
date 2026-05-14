# app/containers/messages/ports/http/message_controller.py
from litestar import get, Controller
from piccolo.table import Select
from src.Containers.message.model.message_model import Message


class MessageController(Controller):
    path = "/messages"

    @get("/")
    async def list_messages(self) -> list[dict]:
        """Return recent messages (limit 20)."""
        rows = await Message.select().order_by("-received_at").limit(20)
        return [row.to_dict() for row in rows]
