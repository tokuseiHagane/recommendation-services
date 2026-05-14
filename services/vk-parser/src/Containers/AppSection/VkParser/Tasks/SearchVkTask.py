"""SearchVkTask — delegate VK search to the internal runtime service."""

from dataclasses import dataclass
from typing import Any

import logfire
from aiovk.exceptions import VkAPIError

from src.Containers.AppSection.VkParser.Exceptions import (
    VkApiError,
    VkAuthenticationError,
    VkRateLimitError,
)
from src.Ship.Parents.Task import Task

# Коды VK, сгруппированные по тому, что с ними делать на HTTP-уровне.
# Источник: https://dev.vk.com/reference/errors
# 5  — User authorization failed (пустой/просроченный access_token).
# 4  — Incorrect signature.
# 27 — Group authorization failed.
# 28 — Application authorization failed.
_VK_AUTH_CODES: frozenset[int] = frozenset({4, 5, 27, 28})

# 7  — Permission to perform this action is denied (чаще всего scope).
# 15 — Access denied (приватность / scope / забаненный юзер).
# 17 — Validation required (redirect-флоу).
_VK_SCOPE_CODES: frozenset[int] = frozenset({7, 15, 17})

# 29 — Rate limit reached (per-token).
# Код 6 (too many requests/sec) ретраится глубже, в CustomTokenSession.
_VK_RATE_CODES: frozenset[int] = frozenset({29})


@dataclass(frozen=True)
class SearchVkInput:
    vk_token: str
    query: str


class SearchVkTask(Task[SearchVkInput, dict[str, Any]]):
    """Execute VK search as an atomic Porto Task."""

    async def run(self, data: SearchVkInput) -> dict[str, Any]:
        from src.VkParser.service import search_vk

        try:
            result = await search_vk(token=data.vk_token, q=data.query)
        except VkAPIError as exc:
            # Сырой VkAPIError таскает ``request_params`` с ``access_token`` —
            # любой ``str(exc)`` / логгер родителя скрабится Logfire как
            # "[Scrubbed due to 'auth']" и диагностировать нельзя. Вытаскиваем
            # чистые поля и перебрасываем доменное исключение — дальше
            # ``exception_handler`` вернёт корректный HTTP-ответ, а фронт
            # покажет пользователю вменяемую причину.
            vk_code = getattr(exc, "error_code", None)
            vk_msg = getattr(exc, "error_msg", None) or "VK API error"

            logfire.error(
                "VK API rejected search.getHints",
                vk_method="search.getHints",
                vk_error_code=vk_code,
                vk_error_msg=vk_msg,
                query=data.query,
            )

            details = {
                "vk_error_code": vk_code,
                "vk_error_msg": vk_msg,
                "vk_method": "search.getHints",
            }

            if vk_code in _VK_AUTH_CODES:
                raise VkAuthenticationError(
                    message=(
                        "VK отклонил access_token. Нужно перевыпустить токен "
                        f"(VK error {vk_code}: {vk_msg})."
                    ),
                    details=details,
                ) from exc

            if vk_code in _VK_SCOPE_CODES:
                raise VkAuthenticationError(
                    message=(
                        "У VK-токена недостаточно прав для search.getHints. "
                        f"Перевыпустите токен с нужным scope (VK error {vk_code}: {vk_msg})."
                    ),
                    status_code=403,
                    details=details,
                ) from exc

            if vk_code in _VK_RATE_CODES:
                raise VkRateLimitError(
                    message=f"VK rate limit (code={vk_code}): {vk_msg}.",
                    details=details,
                ) from exc

            raise VkApiError(
                message=f"VK API error (code={vk_code}): {vk_msg}.",
                vk_error_code=vk_code,
                details={"vk_error_msg": vk_msg, "vk_method": "search.getHints"},
            ) from exc

        return result or {}
