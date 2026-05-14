"""VK Search WebSocket controller — streaming search-as-you-type over WS.

Design §5.2: the target UX for group search is a WebSocket channel that
sends incremental suggestion updates while the user types.  This handler
implements the MVP:

- JWT auth via ``?token=...`` query param.
- Server-side debounce: a new incoming query cancels the previous
  in-flight VK API call for the same connection.
- Redis cache of normalized queries (TTL 120s) shared across connections.
- Enrichment: every returned item is tagged with ``in_db``/``db_group_id``
  so the UI can render the "already in DB / new" marker.
- Fallback: the REST ``GET /search/vk`` endpoint is not changed.

Protocol (JSON in both directions):

- client -> server:  ``{"q": "<query>"}``
- server -> client:  ``{"q": "...", "items": [...], "count": N, "cached": bool}``
- server -> client error: ``{"error": "vk_auth"|"rate_limit"|"invalid"|"upstream", ...}``
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import logfire
from dishka import AsyncContainer
from litestar import WebSocket, websocket
from litestar.exceptions import WebSocketDisconnect
from litestar.stores.redis import RedisStore

from src.Containers.AppSection.VkParser.Actions.CheckGroupsExistAction import CheckGroupsExistAction
from src.Containers.AppSection.VkParser.Actions.SearchVkAction import SearchVkAction
from src.Containers.AppSection.VkParser.Exceptions import VkAuthenticationError, VkParserException
from src.Containers.AppSection.VkParser.Tasks.GetVkTokenTask import GetVkTokenInput, GetVkTokenTask
from src.Containers.AppSection.VkParser.Tasks.VerifyAuthJwtTask import VerifyAuthJwtTask
from src.Ship.Configs.App import AppSettings

CACHE_TTL_SECONDS = 120
CACHE_KEY_PREFIX = "vk:search:hints:"
MAX_NORMALIZED_Q_LEN = 64

# Application close codes (4000-4999 is the user-defined range per RFC 6455).
CLOSE_UNAUTHORIZED = 4401
CLOSE_POLICY_VIOLATION = 4000


def _normalize_q(q: str) -> str:
    return q.strip().lower()[:MAX_NORMALIZED_Q_LEN]


async def _get_cached_payload(redis_store: RedisStore, norm_q: str) -> dict[str, Any] | None:
    raw = await redis_store.get(f"{CACHE_KEY_PREFIX}{norm_q}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


async def _set_cached_payload(redis_store: RedisStore, norm_q: str, payload: dict[str, Any]) -> None:
    try:
        serialized = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await redis_store.set(f"{CACHE_KEY_PREFIX}{norm_q}", serialized, expires_in=CACHE_TTL_SECONDS)
    except Exception:  # pragma: no cover - cache is best-effort
        logfire.warning("Failed to write VK search cache", norm_q=norm_q, exc_info=True)


def _extract_group_ids(items: list[dict[str, Any]]) -> list[int]:
    ids: list[int] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        # ``search.getHints`` returns group objects with positive ``id``.  It
        # may also return user/page hits — we mark those as not in DB.
        if item.get("type") in {"group", "page", "event"} or "screen_name" in item:
            raw_id = item.get("id")
            if isinstance(raw_id, int) and raw_id > 0:
                ids.append(raw_id)
    return ids


def _annotate_items_with_in_db(items: list[dict[str, Any]], presence: dict[int, bool]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            annotated.append(item)
            continue
        enriched = dict(item)
        raw_id = item.get("id")
        if isinstance(raw_id, int) and raw_id in presence:
            enriched["in_db"] = bool(presence[raw_id])
            enriched["db_group_id"] = raw_id if presence[raw_id] else None
        else:
            enriched["in_db"] = False
            enriched["db_group_id"] = None
        annotated.append(enriched)
    return annotated


async def _perform_search(
    *,
    session_container: AsyncContainer,
    vk_token: str,
    q: str,
    redis_store: RedisStore,
) -> tuple[dict[str, Any], bool]:
    """Run VK search with Redis cache + DB enrich. Returns (payload, cached)."""
    norm_q = _normalize_q(q)

    cached = await _get_cached_payload(redis_store, norm_q)
    if cached is not None:
        return cached, True

    async with session_container() as req:
        search_action = await req.get(SearchVkAction)
        check_exist_action = await req.get(CheckGroupsExistAction)

        raw_result = await search_action.execute((vk_token, q))
        items = raw_result.get("items", []) if isinstance(raw_result, dict) else []

        group_ids = _extract_group_ids(items)
        presence = await check_exist_action.execute(group_ids) if group_ids else {}
        annotated = _annotate_items_with_in_db(items, presence)

        payload = {
            "items": annotated,
            "count": len(annotated),
        }

    await _set_cached_payload(redis_store, norm_q, payload)
    return payload, False


@websocket(path="/search/vk/ws")
async def vk_search_ws(socket: WebSocket) -> None:
    """WebSocket streaming search for VK groups (MVP)."""
    token = socket.query_params.get("token")
    session_container: AsyncContainer = socket.state.dishka_container

    settings = await session_container.get(AppSettings)
    redis_store = await session_container.get(RedisStore)
    min_interval_s = max(0.0, settings.rate_limit_ws_min_interval_ms / 1000.0)

    if not token:
        await socket.accept()
        await socket.send_json({"error": "invalid", "message": "missing token query param"})
        await socket.close(code=CLOSE_UNAUTHORIZED)
        return

    # One-time auth handshake: verify JWT and resolve VK token. Both
    # VerifyAuthJwtTask and GetVkTokenTask live at Scope.REQUEST, so we open
    # a short-lived REQUEST sub-container for this.
    try:
        async with session_container() as req:
            verify_task = await req.get(VerifyAuthJwtTask)
            get_vk_token_task = await req.get(GetVkTokenTask)
            verified = await verify_task.execute(token)
            vk_token = await get_vk_token_task.execute(
                GetVkTokenInput(auth_user_id=verified.auth_user_id, jwt_token=token)
            )
    except VkAuthenticationError as exc:
        await socket.accept()
        await socket.send_json(
            {"error": "vk_auth", "message": exc.message, "details": exc.details}
        )
        await socket.close(code=CLOSE_UNAUTHORIZED)
        return

    await socket.accept()
    logfire.info("VK search WS connected", auth_user_id=verified.auth_user_id)

    inflight: asyncio.Task[None] | None = None
    last_request_at_monotonic = 0.0

    async def _handle_and_send(q: str) -> None:
        try:
            payload, cached = await _perform_search(
                session_container=session_container,
                vk_token=vk_token,
                q=q,
                redis_store=redis_store,
            )
            await socket.send_json(
                {
                    "q": q,
                    "items": payload["items"],
                    "count": payload["count"],
                    "cached": cached,
                }
            )
        except asyncio.CancelledError:
            raise
        except VkAuthenticationError as exc:
            await socket.send_json(
                {"error": "vk_auth", "q": q, "message": exc.message, "details": exc.details}
            )
            await socket.close(code=CLOSE_UNAUTHORIZED)
        except VkParserException as exc:
            await socket.send_json(
                {"error": "upstream", "q": q, "code": exc.code, "message": exc.message}
            )
        except Exception:
            logfire.warning("VK search WS query failed", q=q, exc_info=True)
            await socket.send_json({"error": "upstream", "q": q, "message": "search failed"})

    try:
        while True:
            try:
                data = await socket.receive_json()
            except WebSocketDisconnect:
                break
            except (ValueError, TypeError):
                await socket.send_json({"error": "invalid", "message": "expected JSON object"})
                continue

            if not isinstance(data, dict):
                await socket.send_json({"error": "invalid", "message": "expected JSON object"})
                continue

            q_raw = data.get("q")
            if not isinstance(q_raw, str) or not q_raw.strip():
                await socket.send_json({"error": "invalid", "message": "field 'q' must be a non-empty string"})
                continue

            now_monotonic = time.monotonic()
            if min_interval_s > 0 and now_monotonic - last_request_at_monotonic < min_interval_s:
                await socket.send_json(
                    {
                        "error": "rate_limit",
                        "q": q_raw,
                        "min_interval_ms": settings.rate_limit_ws_min_interval_ms,
                    }
                )
                continue
            last_request_at_monotonic = now_monotonic

            # Server-side debounce: supersede the previous pending query.
            if inflight is not None and not inflight.done():
                inflight.cancel()
                try:
                    await inflight
                except (asyncio.CancelledError, Exception):
                    pass

            inflight = asyncio.create_task(_handle_and_send(q_raw))
    finally:
        if inflight is not None and not inflight.done():
            inflight.cancel()
            try:
                await inflight
            except (asyncio.CancelledError, Exception):
                pass
