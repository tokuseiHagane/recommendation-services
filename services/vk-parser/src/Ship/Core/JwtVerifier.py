"""JWT verification utilities backed by JWKS."""

from typing import Any

import jwt
import logfire
from jwt import PyJWKClient

from src.Ship.Configs.App import AppSettings


class JwtVerifier:
    """Verify JWT tokens against the AuthService JWKS endpoint."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._jwks_client = PyJWKClient(
            settings.resolved_auth_jwks_url,
            cache_keys=True,
            lifespan=settings.auth_jwks_cache_ttl_seconds,
        )

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify token signature and required claims."""
        signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        # `audience` передаём только если он настроен. В PyJWT 2.10+ при наличии `aud` в токене
        # и `audience=None` проверка падает с InvalidAudienceError, поэтому отсутствие
        # настройки равносильно отключённой проверке audience (`verify_aud=False`).
        decode_kwargs: dict[str, Any] = {
            "algorithms": self._settings.auth_jwt_algorithms,
            "issuer": self._settings.auth_jwt_issuer,
            "leeway": self._settings.auth_jwt_leeway_seconds,
            "options": {"require": ["exp", "iat", "iss", "sub"]},
        }
        if self._settings.auth_jwt_audience:
            decode_kwargs["audience"] = self._settings.auth_jwt_audience
        else:
            decode_kwargs["options"] = {**decode_kwargs["options"], "verify_aud": False}

        payload = jwt.decode(token, signing_key.key, **decode_kwargs)
        logfire.debug(
            "JWT verified via JWKS",
            issuer=payload.get("iss"),
            subject=payload.get("sub"),
        )
        return payload
