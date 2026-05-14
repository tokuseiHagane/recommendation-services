from __future__ import annotations

from piccolo.columns import Integer, Varchar
from piccolo.columns.column_types import Serial
from piccolo.table import Table

from shared.db import DB


class VkGroup(Table, tablename="groups", db=DB):
    """VK group from ETL pipeline (read-only)."""

    id: Serial
    name = Varchar(length=255, default="")
    screen_name = Varchar(length=255, default="")
    members_count = Integer(default=0)


class VkPost(Table, tablename="posts", db=DB):
    """VK post from ETL pipeline (read-only)."""

    id: Serial
    id_groups = Integer()
    len_message = Integer(default=0)
    view_count = Integer(default=0)
    reactions_count = Integer(default=0)


class TgChannel(Table, tablename="tg_channels", db=DB):
    """Telegram channel from ETL pipeline (read-only)."""

    id: Serial
    title = Varchar(length=255, default="")
    username = Varchar(length=255, default="")
    members_count = Integer(default=0)


class TgPost(Table, tablename="tg_posts", db=DB):
    """Telegram post from ETL pipeline (read-only)."""

    id: Serial
    channel_id = Integer()
    view_count = Integer(default=0)
    reactions_count = Integer(default=0)
