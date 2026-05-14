"""AccountTokens model for accessing VK tokens from shared database.

This model mirrors the AccountTokens table from AuthorizationService.
Used read-only to get VK access tokens by account_id.
"""

from piccolo.columns import UUID, Integer, Timestamptz, Varchar
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table


class AccountTokens(Table, tablename="account_tokens"):
    """OAuth tokens table (shared with AuthorizationService).

    This is a read-only mirror of the AccountTokens table.
    VK Parser only reads VK tokens by account_id.
    """

    id = Integer(primary_key=True)
    account_id = UUID()
    user_id = Varchar(length=73)
    access_token = Varchar(length=256)
    refresh_token = Varchar(length=256, null=True)
    auth_provider = Varchar(length=16, default="vk")
    username = Varchar(length=64, null=True)
    photo_url = Varchar(length=512, null=True)
    auth_date = Timestamptz(null=True)
    created_timestamp = Timestamptz(default=TimestamptzNow())
    updated_timestamp = Timestamptz(default=TimestamptzNow())
    deleted_timestamp = Timestamptz(null=True)
    expiration_timestamp = Timestamptz(null=True)
