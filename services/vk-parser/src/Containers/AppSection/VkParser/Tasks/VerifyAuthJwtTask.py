"""Verify AuthService JWT and extract authenticated user context."""

from dataclasses import dataclass
from typing import Any

import jwt

from src.Containers.AppSection.VkParser.Exceptions import VkAuthenticationError
from src.Ship.Core.JwtVerifier import JwtVerifier
from src.Ship.Parents.Task import Task


@dataclass(slots=True)
class VerifiedAuthContext:
    """Verified parser auth context extracted from JWT claims."""

    auth_user_id: str
    payload: dict[str, Any]


class VerifyAuthJwtTask(Task[str, VerifiedAuthContext]):
    """Verify JWT via JWKS and return account identity."""

    def __init__(self, jwt_verifier: JwtVerifier) -> None:
        self._jwt_verifier = jwt_verifier

    async def run(self, data: str) -> VerifiedAuthContext:
        try:
            payload = self._jwt_verifier.verify_token(data)
        except jwt.ExpiredSignatureError as exc:
            raise VkAuthenticationError(
                message="Session expired. Please login again.",
                details={"error": "token_expired"},
            ) from exc
        except jwt.InvalidIssuerError as exc:
            raise VkAuthenticationError(
                message="Invalid token issuer.",
                details={"error": "invalid_issuer"},
            ) from exc
        except jwt.InvalidAudienceError as exc:
            raise VkAuthenticationError(
                message="Invalid token audience.",
                details={"error": "invalid_audience"},
            ) from exc
        except jwt.PyJWKClientError as exc:
            raise VkAuthenticationError(
                message="Failed to verify authentication token via JWKS.",
                details={"error": "jwks_unavailable"},
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise VkAuthenticationError(
                message="Invalid authentication token.",
                details={"error": str(exc)},
            ) from exc

        auth_user_id = payload.get("sub")
        if not auth_user_id:
            raise VkAuthenticationError(
                message="Invalid token: missing auth user id.",
                details={"error": "missing_sub"},
            )
        if not isinstance(auth_user_id, str):
            raise VkAuthenticationError(
                message="Invalid token: auth user id must be a string.",
                details={"error": "invalid_sub_type"},
            )

        return VerifiedAuthContext(auth_user_id=auth_user_id, payload=payload)
