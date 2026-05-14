"""GetVkTokenTask — resolve VK access token for a given account."""

from uuid import UUID

import logfire

from src.Containers.AppSection.VkParser.Exceptions import VkAuthenticationError
from src.Ship.Configs.App import AppSettings
from src.Ship.Core.AuthServiceClient import (
    AuthServiceClient,
    AuthServiceClientError,
    AuthServiceForbiddenError,
    AuthServiceUnauthorizedError,
    AuthServiceVkAccountNotLinkedError,
    AuthServiceVkTokenExpiredError,
    AuthServiceVkTokenRefreshFailedError,
    AuthServiceVkTokenRefreshUnavailableError,
)
from src.Ship.Core.TokenStorage import TokenStorage
from src.Ship.Parents.Task import Task


class GetVkTokenInput:
    __slots__ = ("auth_user_id", "jwt_token")

    def __init__(self, auth_user_id: str, jwt_token: str) -> None:
        self.auth_user_id = auth_user_id
        self.jwt_token = jwt_token


class GetVkTokenTask(Task[GetVkTokenInput, str]):
    """Resolve VK access token from AuthService or documented fallbacks."""

    def __init__(
        self,
        settings: AppSettings,
        auth_service_client: AuthServiceClient,
        token_storage: TokenStorage,
    ) -> None:
        self._settings = settings
        self._auth_service_client = auth_service_client
        self._token_storage = token_storage

    async def run(self, data: GetVkTokenInput) -> str:
        try:
            vk_token = await self._auth_service_client.get_vk_token(data.jwt_token)
            if vk_token:
                return vk_token
        except AuthServiceVkAccountNotLinkedError as exc:
            raise VkAuthenticationError(
                message="VK token not found. Please link your VK account via AuthorizationService.",
                details={"error": "no_vk_token", "auth_user_id": data.auth_user_id},
            ) from exc
        except AuthServiceVkTokenExpiredError as exc:
            # AuthService уже попробовал рефреш и получил invalid_grant от VK ID
            # — единственный выход: юзер должен переподключить VK.
            raise VkAuthenticationError(
                message=(
                    "VK access token expired. Please reconnect your VK account "
                    "(Profile → Linked accounts → VK → reconnect)."
                ),
                details={
                    "error": "vk_token_expired",
                    "auth_user_id": data.auth_user_id,
                },
            ) from exc
        except AuthServiceVkTokenRefreshUnavailableError as exc:
            # У аккаунта нет device_id (например, связался до появления auto-refresh)
            # или отсутствует refresh_token. Одноразовое переподключение VK решает.
            raise VkAuthenticationError(
                message=(
                    "VK access token can't be refreshed automatically. "
                    "Please reconnect your VK account once so we can capture a refresh token."
                ),
                details={
                    "error": "vk_token_refresh_unavailable",
                    "auth_user_id": data.auth_user_id,
                },
            ) from exc
        except AuthServiceVkTokenRefreshFailedError as exc:
            # Преходящая ошибка — сеть или VK ID 5xx. Без юзерских действий.
            raise VkAuthenticationError(
                message="VK token refresh failed due to upstream error. Please retry later.",
                status_code=502,
                details={
                    "error": "vk_token_refresh_failed",
                    "auth_user_id": data.auth_user_id,
                    "reason": str(exc),
                },
            ) from exc
        except AuthServiceUnauthorizedError as exc:
            raise VkAuthenticationError(
                message="AuthService rejected authenticated request.",
                details={"error": "auth_service_unauthorized"},
            ) from exc
        except AuthServiceForbiddenError as exc:
            raise VkAuthenticationError(
                message="AuthService rejected backend secret.",
                status_code=403,
                details={"error": "auth_service_forbidden"},
            ) from exc
        except AuthServiceClientError as exc:
            if not self._settings.auth_enable_legacy_db_fallback and not self._settings.vk_access_token:
                raise VkAuthenticationError(
                    message="Failed to retrieve VK token from AuthService.",
                    details={"error": "auth_service_unavailable"},
                ) from exc
            logfire.warning(
                "AuthService VK token fetch failed, trying compatibility fallback",
                auth_user_id=data.auth_user_id,
                error=str(exc),
            )

        if self._settings.auth_enable_legacy_db_fallback:
            try:
                legacy_account_id = UUID(data.auth_user_id)
            except ValueError:
                legacy_account_id = None

            if legacy_account_id is not None:
                vk_token = await self._token_storage.get_vk_token_by_account_id(legacy_account_id)
                if vk_token:
                    logfire.warning(
                        "Using legacy AccountTokens fallback for VK token",
                        auth_user_id=data.auth_user_id,
                    )
                    return vk_token

        fallback = self._settings.vk_access_token
        if fallback:
            logfire.warning("Using fallback VK token from settings", auth_user_id=data.auth_user_id)
            return fallback

        raise VkAuthenticationError(
            message="VK token not found. Please link your VK account via AuthorizationService.",
            details={"error": "no_vk_token", "auth_user_id": data.auth_user_id},
        )
