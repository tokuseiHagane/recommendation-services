"""End-to-end tests for the VK Search WebSocket controller.

We run the WS through Litestar's ``TestClient.websocket_connect`` so the
full middleware stack (auth, rate-limit, Dishka injection) is exercised.
Heavy dependencies (JWT verifier, VK token fetch, VK API call, Redis) are
monkey-patched to keep the test hermetic.
"""

from __future__ import annotations

import json
import time
from types import SimpleNamespace
from typing import Any

import pytest
from litestar.testing import TestClient

from src.Ship.Configs.App import get_settings

from src.Containers.AppSection.VkParser.Actions.CheckGroupsExistAction import CheckGroupsExistAction
from src.Containers.AppSection.VkParser.Actions.SearchVkAction import SearchVkAction
from src.Containers.AppSection.VkParser.Exceptions import VkAuthenticationError
from src.Containers.AppSection.VkParser.Tasks.GetVkTokenTask import GetVkTokenTask
from src.Containers.AppSection.VkParser.Tasks.VerifyAuthJwtTask import VerifyAuthJwtTask
from src.Containers.AppSection.VkParser.UI.API.Controllers import VkSearchWsController


class _FakeRedisStore:
    """Minimal in-memory drop-in for ``litestar.stores.redis.RedisStore``.

    The controller only calls ``get``/``set``; that's all we need.
    """

    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}
        self.set_calls: list[tuple[str, Any, int | None]] = []

    async def get(self, key: str) -> bytes | None:
        return self._data.get(key)

    async def set(self, key: str, value: bytes, expires_in: int | None = None) -> None:
        self.set_calls.append((key, value, expires_in))
        self._data[key] = value


@pytest.fixture()
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedisStore:
    fake = _FakeRedisStore()

    async def _fake_get_cached(_store, norm_q: str):
        raw = await fake.get(f"{VkSearchWsController.CACHE_KEY_PREFIX}{norm_q}")
        return json.loads(raw) if raw else None

    async def _fake_set_cached(_store, norm_q: str, payload):
        key = f"{VkSearchWsController.CACHE_KEY_PREFIX}{norm_q}"
        await fake.set(key, json.dumps(payload).encode("utf-8"), expires_in=120)

    # The controller imports these helpers at module top-level, so
    # patching here also patches the reference inside the module.
    monkeypatch.setattr(VkSearchWsController, "_get_cached_payload", _fake_get_cached)
    monkeypatch.setattr(VkSearchWsController, "_set_cached_payload", _fake_set_cached)
    return fake


def _patch_auth_ok(monkeypatch: pytest.MonkeyPatch, *, auth_user_id: str = "u1") -> None:
    async def fake_verify(self, raw_token: str):  # noqa: ANN001
        return SimpleNamespace(auth_user_id=auth_user_id, payload={"sub": auth_user_id})

    async def fake_vk_token(self, data):  # noqa: ANN001
        return "vk-token"

    monkeypatch.setattr(VerifyAuthJwtTask, "run", fake_verify)
    monkeypatch.setattr(GetVkTokenTask, "run", fake_vk_token)


class TestWsAuth:
    def test_missing_token_closes_with_4401(self, client: TestClient):
        with client.websocket_connect("/api/v1/search/vk/ws") as ws:
            msg = ws.receive_json()
            assert msg["error"] == "invalid"
            # Litestar's TestClient surfaces the close code via the next
            # ``receive`` — make sure the connection does get closed.

    def test_invalid_jwt_is_rejected(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def fake_verify(self, raw_token: str):  # noqa: ANN001
            raise VkAuthenticationError(message="nope", details={"error": "bad"})

        monkeypatch.setattr(VerifyAuthJwtTask, "run", fake_verify)

        with client.websocket_connect("/api/v1/search/vk/ws?token=xxx") as ws:
            msg = ws.receive_json()
            assert msg["error"] == "vk_auth"


class TestWsSearchFlow:
    def test_cache_miss_then_hit(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        fake_redis: _FakeRedisStore,
    ) -> None:
        _patch_auth_ok(monkeypatch)

        call_counter = {"vk": 0}

        async def fake_search(self, data):  # noqa: ANN001
            call_counter["vk"] += 1
            return {"items": [{"id": 10, "type": "group", "screen_name": "lentach"}]}

        async def fake_exist(self, ids):  # noqa: ANN001
            return {int(gid): False for gid in ids}

        monkeypatch.setattr(SearchVkAction, "run", fake_search)
        monkeypatch.setattr(CheckGroupsExistAction, "run", fake_exist)

        min_interval_s = get_settings().rate_limit_ws_min_interval_ms / 1000.0

        with client.websocket_connect("/api/v1/search/vk/ws?token=x") as ws:
            ws.send_json({"q": "lentach"})
            first = ws.receive_json()
            assert first["count"] == 1
            assert first["cached"] is False
            assert first["items"][0]["in_db"] is False

            # Respect the per-connection throttle so the second message
            # isn't rejected as ``rate_limit`` before it reaches the cache.
            time.sleep(min_interval_s + 0.05)

            ws.send_json({"q": "lentach"})
            second = ws.receive_json()
            # Second call for the same normalized query must hit the
            # Redis cache instead of VK.
            assert second["cached"] is True
            assert call_counter["vk"] == 1

    def test_invalid_payload_is_rejected(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        fake_redis: _FakeRedisStore,
    ) -> None:
        _patch_auth_ok(monkeypatch)

        with client.websocket_connect("/api/v1/search/vk/ws?token=x") as ws:
            ws.send_json({"q": ""})
            msg = ws.receive_json()
            assert msg["error"] == "invalid"
