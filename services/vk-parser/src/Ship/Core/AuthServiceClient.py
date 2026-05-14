"""Client for internal AuthService requests."""

from datetime import UTC, datetime
from typing import Any

import httpx
import logfire

from src.Ship.Configs.App import AppSettings


class AuthServiceClientError(RuntimeError):
    """AuthService request failed."""


class AuthServiceUnauthorizedError(AuthServiceClientError):
    """AuthService rejected the forwarded bearer token."""


class AuthServiceForbiddenError(AuthServiceClientError):
    """AuthService rejected the backend shared secret."""


class AuthServiceVkAccountNotLinkedError(AuthServiceClientError):
    """Authenticated user has no linked VK account in AuthService."""


class AuthServiceVkTokenExpiredError(AuthServiceClientError):
    """VK refresh_token rejected by VK ID — user must re-link VK account."""


class AuthServiceVkTokenRefreshUnavailableError(AuthServiceClientError):
    """AuthService can't refresh VK token (missing device_id/refresh_token)."""


class AuthServiceVkTokenRefreshFailedError(AuthServiceClientError):
    """AuthService refresh attempt failed transiently (network/5xx/VK ID)."""


class AuthServiceClient:
    """Fetch VK access tokens from the internal AuthService API."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    async def get_vk_token(self, jwt_token: str) -> str | None:
        """Fetch current VK access token from AuthService.

        AuthService (`GET /api/internal/auth/vk-account`) прозрачно рефрешит
        токен, если `accessTokenExpiresAt` близок к истечению, поэтому здесь
        мы получаем уже актуальный access_token и можем спокойно передавать
        его в VK API.
        """
        url = self._settings.resolved_auth_vk_token_url
        payload = await self._perform_request(
            method="GET",
            url=url,
            jwt_token=jwt_token,
        )
        return self._resolve_access_token(payload, url)

    async def force_refresh_vk_token(self, jwt_token: str) -> str | None:
        """Принудительный refresh VK access_token.

        Используется, когда VK API вернул `error_code=5 "User authorization
        failed"` — это признак того, что закэшированный нами access_token
        либо вот-вот истечёт, либо уже инвалидирован VK (например, юзер
        сменил пароль). В этой ситуации повторная попытка с тем же токеном
        бесполезна — нужен свежий, выданный прямо сейчас.

        Обращается к `POST /api/internal/auth/vk-account/refresh`, который
        делает запрос `grant_type=refresh_token` к id.vk.com и возвращает
        свежий access_token.
        """
        url = self._settings.resolved_auth_vk_refresh_url
        payload = await self._perform_request(
            method="POST",
            url=url,
            jwt_token=jwt_token,
        )
        return self._resolve_access_token(payload, url)

    async def _perform_request(
        self,
        *,
        method: str,
        url: str,
        jwt_token: str,
    ) -> dict[str, Any]:
        request_headers = {"Authorization": f"Bearer {jwt_token}"}
        if self._settings.auth_backend_shared_secret:
            request_headers["X-Auth-Backend-Secret"] = self._settings.auth_backend_shared_secret

        try:
            async with httpx.AsyncClient(timeout=self._settings.auth_http_timeout_seconds) as client:
                response = await client.request(method, url, headers=request_headers)
        except httpx.HTTPError as exc:
            raise AuthServiceClientError("AuthService request failed") from exc

        return self._parse_response(response, url)

    def _parse_response(self, response: httpx.Response, url: str) -> dict[str, Any]:
        status = response.status_code

        if status == 401:
            raise AuthServiceUnauthorizedError("AuthService rejected bearer token")
        if status == 403:
            raise AuthServiceForbiddenError("AuthService rejected backend secret")

        try:
            payload = response.json() if response.content else {}
        except ValueError as exc:
            raise AuthServiceClientError(
                f"AuthService returned invalid JSON (status={status})"
            ) from exc

        if status == 404:
            if isinstance(payload, dict) and payload.get("error") == "VK_ACCOUNT_NOT_LINKED":
                raise AuthServiceVkAccountNotLinkedError(
                    "VK account is not linked in AuthService"
                )
            raise AuthServiceClientError("AuthService returned unexpected 404 response")

        # 409 — набор семантических ошибок auth-сервиса, связанных с VK-токеном:
        # VK_TOKEN_EXPIRED  → VK отклонил refresh_token (invalid_grant),
        #                     юзер должен переподключить VK-аккаунт.
        # VK_TOKEN_REFRESH_UNAVAILABLE → нет device_id/refresh_token — тоже
        #                     требуется переподключение VK.
        # VK_TOKEN_REFRESH_FAILED      → преходящая ошибка (сеть/5xx от VK ID).
        if status == 409 and isinstance(payload, dict):
            error_code = payload.get("error")
            message = payload.get("message") or "AuthService returned 409"
            if error_code == "VK_TOKEN_EXPIRED":
                raise AuthServiceVkTokenExpiredError(message)
            if error_code == "VK_TOKEN_REFRESH_UNAVAILABLE":
                raise AuthServiceVkTokenRefreshUnavailableError(message)
            if error_code == "VK_TOKEN_REFRESH_FAILED":
                raise AuthServiceVkTokenRefreshFailedError(message)
            raise AuthServiceClientError(f"AuthService 409: {error_code or 'unknown'}")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AuthServiceClientError(
                f"AuthService returned status {status}"
            ) from exc

        if not isinstance(payload, dict):
            raise AuthServiceClientError("AuthService response is not a JSON object")

        return payload

    def _resolve_access_token(self, payload: dict[str, Any], url: str) -> str | None:
        vk_token = self._extract_vk_token(payload)
        if not vk_token:
            raise AuthServiceClientError("AuthService response does not contain VK token")

        # AuthService теперь сам рефрешит токен при истечении. Оставляем
        # защитную проверку accessTokenExpiresAt как belt-and-suspenders:
        # если auth старой версии (без auto-refresh) отдаст истёкший токен,
        # мы не будем его слепо использовать.
        expires_at = self._extract_expires_at(payload)
        if expires_at is not None and expires_at <= datetime.now(UTC):
            logfire.warning(
                "AuthService returned expired VK access token — consider upgrading auth service",
                url=url,
                expires_at=expires_at.isoformat(),
            )
            raise AuthServiceVkTokenExpiredError(
                "VK access token expired; user must re-link VK account"
            )

        logfire.debug(
            "VK token received from AuthService",
            url=url,
            refreshed=payload.get("refreshed"),
        )
        return vk_token

    def _extract_vk_token(self, payload: Any) -> str | None:
        """Extract VK token from a few compatible response shapes."""
        if isinstance(payload, str) and payload:
            return payload

        if not isinstance(payload, dict):
            return None

        value = payload.get("accessToken")
        if isinstance(value, str) and value:
            return value

        return None

    def _extract_expires_at(self, payload: Any) -> datetime | None:
        """Parse accessTokenExpiresAt ISO8601 timestamp from the response payload."""
        if not isinstance(payload, dict):
            return None

        raw = payload.get("accessTokenExpiresAt")
        if not isinstance(raw, str) or not raw:
            return None

        try:
            # datetime.fromisoformat в 3.11+ принимает `Z` через trailing suffix,
            # но явно меняем на +00:00 ради совместимости со старыми 3.10.
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            logfire.warning("Failed to parse accessTokenExpiresAt", raw=raw)
            return None
