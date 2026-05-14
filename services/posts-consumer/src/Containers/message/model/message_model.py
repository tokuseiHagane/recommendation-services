from datetime import datetime
from typing import Any, Dict, Optional
import logging
import os
import uuid

from piccolo.table import Table, create_db_tables
from piccolo.columns import UUID, JSON, Timestamp, Varchar, Integer, Boolean
from piccolo.columns.readable import Readable

logger = logging.getLogger(__name__)

# Set piccolo_conf path for engine discovery
if "PICCOLO_CONF" not in os.environ:
    os.environ["PICCOLO_CONF"] = "piccolo_conf"


class Message(Table, tablename="messages"):
    """
    Table to store consumed Kafka messages and minimal metadata.
    Keep the payload as JSON so we can store arbitrary message shapes.
    """
    id = UUID(primary_key=True, default=uuid.uuid4)
    message_id = Varchar(length=255, null=True)  # optional unique id inside payload
    topic = Varchar(length=255, null=True)
    partition = Integer(null=True)
    offset = Integer(null=True)
    payload = JSON(null=False)
    processed = Boolean(default=False)
    received_at = Timestamp(default=datetime.utcnow)

    @classmethod
    def get_readable(cls):
        """Return a readable string representation of the record."""
        return Readable(template="%s", columns=[cls.message_id])


async def create_tables() -> None:
    """
    Create DB tables for this container (if they don't exist).
    Call this once at startup (e.g. from main.py or a startup hook).
    """
    logger.info("Creating messages table if not exists...")
    await create_db_tables(Message, if_not_exists=True)
    logger.info("Messages table ensured.")
