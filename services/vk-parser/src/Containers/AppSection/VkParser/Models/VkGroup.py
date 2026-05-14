"""VkGroup model — VK group/community metadata cached locally."""

from piccolo.columns import Integer, Text, Timestamptz, Varchar
from piccolo.table import Table


class VkGroup(Table, tablename="groups"):
    """Cached VK group metadata.

    Schema aligned with Telegram-Channel-Consumer ``VkGroupSchema``
    and ``parser-flow.md`` spec.
    """

    id = Integer(primary_key=True, help_text="VK group numeric id")
    name = Varchar(length=255, null=True)
    screen_name = Varchar(length=255, null=True, index=True)
    members_count = Integer(null=True)
    last_parsed_at = Timestamptz(null=True, help_text="When this group was last parsed")
    photo_url = Text(null=True, help_text="VK group avatar (usually photo_200)")
    cover_url = Text(null=True, help_text="VK group cover (best-resolution URL)")
