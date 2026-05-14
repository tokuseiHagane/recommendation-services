import logging

from piccolo.table import Table, create_db_tables
from piccolo.columns import Integer, Text, Timestamptz, Varchar
from piccolo.columns.readable import Readable
from src.Ship.utils.db import get_vk_db_engine

logger = logging.getLogger(__name__)
VK_DB = get_vk_db_engine()


class VkGroup(Table, tablename="groups", db=VK_DB):
    """
    Table to store VK social network groups information.
    
    Structure matches VKParserService groups schema:
    - id: group identifier (primary key, integer - VK uses numeric IDs)
    - name: group name
    - screen_name: group screen name (URL slug)
    - members_count: number of members in the group
    - last_parsed_at: timestamp maintained by VKParserService
    
    Uses INSERT ON CONFLICT UPDATE (upsert) to handle duplicate id entries.
    """
    id = Integer(primary_key=True, null=False)  # VK Group ID (integer)
    name = Varchar(length=255, null=True)  # Group name
    screen_name = Varchar(length=255, null=True, index=True)  # Group screen name (URL slug)
    members_count = Integer(null=True)  # Number of members
    photo_url = Text(null=True)
    cover_url = Text(null=True)
    last_parsed_at = Timestamptz(null=True)  # Managed by VKParserService

    @classmethod
    def get_readable(cls):
        """Return a readable string representation of the record."""
        return Readable(template="%s", columns=[cls.name])


async def create_tables() -> None:
    """
    Create DB tables for VK group container (if they don't exist).
    Call this once at startup (e.g. from main.py or a startup hook).
    
    This function ensures the 'groups' table exists in the VK database.
    Uses Piccolo table metadata bound to the dedicated VK engine.
    """
    try:
        logger.info("Checking and creating VK 'groups' table if not exists...")
        await create_db_tables(VkGroup, if_not_exists=True)
        logger.info("VK Groups table ready (created or already exists).")
    except Exception as e:
        logger.error(f"Failed to create VK groups table: {e}")
        raise
