"""Token storage - get VK tokens from database using Piccolo ORM."""

from uuid import UUID

import logfire

from src.Containers.AppSection.VkParser.Models.AccountTokens import AccountTokens


class TokenStorage:
    """Storage for retrieving VK tokens from database via Piccolo.

    VK tokens are stored in AccountTokens table (shared with AuthorizationService).
    JWT contains account_id, which is used to look up the VK token.
    """

    async def get_vk_token_by_account_id(self, account_id: UUID) -> str | None:
        """Get VK access token by account ID using Piccolo ORM."""
        try:
            token_record = (
                await AccountTokens.select(AccountTokens.access_token)
                .where(
                    (AccountTokens.account_id == account_id)
                    & (AccountTokens.auth_provider == "vk")
                    & (AccountTokens.deleted_timestamp.is_null())
                )
                .order_by(AccountTokens.updated_timestamp, ascending=False)
                .first()
            )

            if token_record:
                access_token = token_record.get("access_token")
                logfire.debug(
                    "VK token retrieved via Piccolo",
                    account_id=str(account_id),
                    has_token=bool(access_token),
                )
                return access_token

            logfire.warning("VK token not found", account_id=str(account_id))
            return None

        except Exception as e:
            logfire.error(
                "Failed to get VK token via Piccolo",
                account_id=str(account_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def get_token_info(self, account_id: UUID) -> dict | None:
        """Get full VK token info by account ID."""
        try:
            token_record = (
                await AccountTokens.select(
                    AccountTokens.access_token,
                    AccountTokens.user_id,
                    AccountTokens.updated_timestamp,
                    AccountTokens.expiration_timestamp,
                )
                .where(
                    (AccountTokens.account_id == account_id)
                    & (AccountTokens.auth_provider == "vk")
                    & (AccountTokens.deleted_timestamp.is_null())
                )
                .order_by(AccountTokens.updated_timestamp, ascending=False)
                .first()
            )

            if token_record:
                return {
                    "access_token": token_record.get("access_token"),
                    "vk_user_id": token_record.get("user_id"),
                    "updated_at": token_record.get("updated_timestamp"),
                    "expires_at": token_record.get("expiration_timestamp"),
                }

            return None

        except Exception as e:
            logfire.error(
                "Failed to get token info via Piccolo",
                account_id=str(account_id),
                error=str(e),
            )
            return None


def create_token_storage() -> TokenStorage:
    """Factory for Dishka DI provider."""
    return TokenStorage()
