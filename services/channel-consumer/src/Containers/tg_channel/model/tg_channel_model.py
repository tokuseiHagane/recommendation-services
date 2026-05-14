from typing import Optional
import logging
import os
import uuid

from piccolo.table import Table, create_db_tables
from piccolo.columns import UUID, Varchar
from piccolo.columns.readable import Readable

logger = logging.getLogger(__name__)

# Set piccolo_conf path for engine discovery
if "PICCOLO_CONF" not in os.environ:
    os.environ["PICCOLO_CONF"] = "piccolo_conf"


class TgChannel(Table, tablename="channels"):
    """
    Table to store Telegram channels information.
    
    Structure matches the database schema:
    - id: channel identifier (primary key, UUID)
    - name: channel name
    - type: channel type
    
    Uses INSERT ON CONFLICT UPDATE (upsert) to handle duplicate id entries.
    UUID can be provided or auto-generated if not provided.
    """
    id = UUID(primary_key=True, default=uuid.uuid4, null=False)  # Channel ID (UUID)
    name = Varchar(null=True)  # Channel name
    type = Varchar(length=255, null=True)  # Channel type

    @classmethod
    def get_readable(cls):
        """Return a readable string representation of the record."""
        return Readable(template="%s", columns=[cls.name])


async def create_tables() -> None:
    """
    Create DB tables for this container (if they don't exist).
    Call this once at startup (e.g. from main.py or a startup hook).
    
    This function ensures the 'channels' table exists in the database.
    Uses Piccolo's create_db_tables with if_not_exists=True to safely
    create the table only if it doesn't already exist.
    """
    try:
        logger.info("Checking and creating 'channels' table if not exists...")
        await create_db_tables(TgChannel, if_not_exists=True)
        logger.info("✅ Channels table ready (created or already exists).")
    except Exception as e:
        logger.error(f"❌ Failed to create channels table: {e}")
        raise

