"""VkPost model — individual VK wall post cached locally."""

from piccolo.columns import Integer, Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table


class VkPost(Table, tablename="posts"):
    """Cached VK wall post.

    Schema aligned with Telegram-Posts-Consumers ``VkPostDTO``
    and ``parser-flow.md`` spec.
    """

    id = Integer(primary_key=True, help_text="VK post id")
    id_groups = Integer(null=True, index=True, help_text="FK to groups.id")
    message_timestamp = Timestamptz(null=True, index=True)
    edit_date = Timestamptz(null=True)
    view_count = Integer(default=0)
    reactions_count = Integer(default=0)
    comments_count = Integer(default=0)
    repost_count = Integer(default=0)
    len_message = Integer(default=0)
    cached_at = Timestamptz(default=TimestamptzNow(), help_text="When this post was cached")
