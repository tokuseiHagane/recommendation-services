"""
VkGroup Model: Представляет VK группу.

Схема соответствует SQL определению из vk_db.sql (таблица groups).
"""

from piccolo.table import Table
from piccolo.columns import (
    Integer,
    Timestamptz,
    Varchar,
)


class VkGroup(Table, tablename="groups"):
    """
    Porto Model: VK group entity.
    
    Schema aligned with VKParserService `groups` table.
    
    Attributes:
        id: Unique group identifier (primary key)
        name: Group display name
        screen_name: Group screen name (URL slug)
        members_count: Number of group members
        last_parsed_at: Timestamp maintained by VKParserService
    
    Indexes:
        - PRIMARY KEY on id
    
    Relationships:
        - Referenced by VkPost.id_groups
    
    Example usage:
        # Single insert
        group = VkGroup(id=123, name="Test Group", screen_name="test_group")
        await group.save()
        
        # Batch insert
        groups = [
            VkGroup(id=1, name="Group 1", screen_name="group1"),
            VkGroup(id=2, name="Group 2", screen_name="group2")
        ]
        await VkGroup.insert(*groups)
    """
    
    id = Integer(
        primary_key=True,
        help_text="Unique group identifier"
    )
    
    name = Varchar(
        length=255,
        null=True,
        help_text="Group display name"
    )
    
    screen_name = Varchar(
        length=255,
        null=True,
        index=True,
        help_text="Group screen name (URL slug)"
    )
    
    members_count = Integer(
        null=True,
        help_text="Number of group members"
    )

    last_parsed_at = Timestamptz(
        null=True,
        help_text="When this group was last parsed"
    )
