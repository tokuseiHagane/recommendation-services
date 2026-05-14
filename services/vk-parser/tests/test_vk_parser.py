"""Tests for VK Parser Service."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from litestar.testing import TestClient

from src.Containers.AppSection.VkParser.Actions.ParseVkDataAction import ParseVkDataAction
from src.Containers.AppSection.VkParser.Data.Dto import SortParamConfig, SortParams, VkParseRequest
from src.Containers.AppSection.VkParser.Exceptions import VkAuthenticationError
from src.Containers.AppSection.VkParser.Models.CachedPeriod import CachedPeriod
from src.Containers.AppSection.VkParser.Models.VkGroup import VkGroup
from src.Containers.AppSection.VkParser.Models.VkPost import VkPost
from src.Containers.AppSection.VkParser.Tasks.CacheCheckTask import (
    CacheCheckResult,
    Period,
    calculate_missing_periods,
)
from src.Containers.AppSection.VkParser.Tasks.FetchVkWallTask import FetchVkWallInput, FetchVkWallTask
from src.Containers.AppSection.VkParser.Tasks.GetVkTokenTask import GetVkTokenInput, GetVkTokenTask
from src.Containers.AppSection.VkParser.Tasks.PublishToKafkaTask import PublishToKafkaInput, PublishToKafkaTask
from src.Containers.AppSection.VkParser.Tasks.SaveParsedDataTask import SaveParsedDataInput, SaveParsedDataTask
from src.Containers.AppSection.VkParser.Tasks.SearchVkTask import SearchVkInput, SearchVkTask
from src.Containers.AppSection.VkParser.Tasks.VerifyAuthJwtTask import VerifyAuthJwtTask
from src.Ship.Core.AuthServiceClient import (
    AuthServiceClientError,
    AuthServiceForbiddenError,
    AuthServiceUnauthorizedError,
    AuthServiceVkAccountNotLinkedError,
)
from src.Ship.Core.JwtVerifier import JwtVerifier
from src.VkParser import service as vk_service


class TestVkParserAPI:
    """Tests for VK Parser API endpoints — auth validation layer."""

    def test_search_requires_auth(self, client: TestClient):
        """Search without bearer token must return 401."""
        response = client.get("/api/v1/search/vk", params={"q": "test"})
        assert response.status_code == 401

    def test_parse_requires_auth(self, client: TestClient):
        """Parse without bearer token must return 401."""
        response = client.post(
            "/api/v1/parse/vk",
            json={
                "links": ["https://vk.com/test"],
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-31T23:59:59",
                "top_n": 10,
            },
        )
        assert response.status_code == 401

    def test_health_without_auth(self, client: TestClient):
        """Health endpoint works without auth, reports unauthenticated."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["authenticated"] is False


class TestJWTAuthentication:
    """Tests for Bearer JWT auth and temporary compatibility mode."""

    def test_invalid_bearer_rejected(self, client: TestClient):
        """Malformed Authorization header must return 401."""
        response = client.get(
            "/api/v1/search/vk",
            params={"q": "test"},
            headers={"Authorization": "Token invalid"},
        )
        assert response.status_code == 401

    def test_bearer_token_drives_search_flow(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        bearer_token_value: str,
        test_account_id: str,
    ) -> None:
        """Bearer token is the primary auth path for parser API."""
        captured: dict[str, Any] = {}

        async def fake_verify_run(self: VerifyAuthJwtTask, raw_token: str) -> Any:
            captured["verified_token"] = raw_token
            return SimpleNamespace(auth_user_id=test_account_id, payload={"sub": test_account_id})

        async def fake_get_vk_token_run(self: GetVkTokenTask, data: GetVkTokenInput) -> str:
            captured["jwt_token"] = data.jwt_token
            captured["auth_user_id"] = data.auth_user_id
            return "vk-token-from-auth-service"

        async def fake_search_vk(*, token: str, q: str) -> dict[str, Any]:
            captured["vk_token"] = token
            captured["query"] = q
            return {"items": [{"description": "Lentach"}]}

        monkeypatch.setattr(VerifyAuthJwtTask, "run", fake_verify_run)
        monkeypatch.setattr(GetVkTokenTask, "run", fake_get_vk_token_run)
        monkeypatch.setattr(vk_service, "search_vk", fake_search_vk)

        response = client.get(
            "/api/v1/search/vk",
            params={"q": "lentach"},
            headers={"Authorization": f"Bearer {bearer_token_value}"},
        )

        assert response.status_code == 200
        assert captured == {
            "verified_token": bearer_token_value,
            "jwt_token": bearer_token_value,
            "auth_user_id": test_account_id,
            "vk_token": "vk-token-from-auth-service",
            "query": "lentach",
        }

    def test_cookie_fallback_is_secondary_to_bearer(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        bearer_token_value: str,
        legacy_cookie_token_value: str,
        test_account_id: str,
    ) -> None:
        """Bearer token must win even when legacy cookie is present."""
        captured: dict[str, Any] = {}

        async def fake_verify_run(self: VerifyAuthJwtTask, raw_token: str) -> Any:
            captured["verified_token"] = raw_token
            return SimpleNamespace(auth_user_id=test_account_id, payload={"sub": test_account_id})

        async def fake_get_vk_token_run(self: GetVkTokenTask, data: GetVkTokenInput) -> str:
            return "vk-token"

        async def fake_search_vk(*, token: str, q: str) -> dict[str, Any]:
            return {"items": [{"description": q, "token": token}]}

        monkeypatch.setattr(VerifyAuthJwtTask, "run", fake_verify_run)
        monkeypatch.setattr(GetVkTokenTask, "run", fake_get_vk_token_run)
        monkeypatch.setattr(vk_service, "search_vk", fake_search_vk)

        response = client.get(
            "/api/v1/search/vk",
            params={"q": "lentach"},
            headers={"Authorization": f"Bearer {bearer_token_value}"},
            cookies={"auth_token": legacy_cookie_token_value},
        )

        assert response.status_code == 200
        assert captured["verified_token"] == bearer_token_value


class FakeJwtVerifier(JwtVerifier):
    """Tiny verifier stub used in auth task tests."""

    def __init__(self, payload: dict[str, Any] | None = None, error: Exception | None = None) -> None:
        self.payload = payload or {}
        self.error = error

    def verify_token(self, token: str) -> dict[str, Any]:
        if self.error is not None:
            raise self.error
        return self.payload


class FakeAuthServiceClient:
    """Small AuthService client stub for token task tests."""

    def __init__(self, result: str | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    async def get_vk_token(self, jwt_token: str) -> str | None:
        if self.error is not None:
            raise self.error
        return self.result


class FakeTokenStorage:
    """Small token storage stub for compatibility tests."""

    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.account_ids: list[UUID] = []

    async def get_vk_token_by_account_id(self, account_id: UUID) -> str | None:
        self.account_ids.append(account_id)
        return self.token


class TestVerifyAuthJwtTask:
    """Focused tests for JWKS-backed JWT verification task."""

    @pytest.mark.asyncio
    async def test_extracts_auth_user_id_from_verified_payload(self, test_account_id: str) -> None:
        task = VerifyAuthJwtTask(
            jwt_verifier=FakeJwtVerifier(payload={"sub": test_account_id, "iss": "fdauth-service"})
        )

        result = await task.execute("opaque-token")

        assert result.auth_user_id == test_account_id
        assert result.payload["sub"] == test_account_id

    @pytest.mark.asyncio
    async def test_rejects_missing_sub_claim(self) -> None:
        task = VerifyAuthJwtTask(jwt_verifier=FakeJwtVerifier(payload={"iss": "fdauth-service"}))

        with pytest.raises(VkAuthenticationError) as exc_info:
            await task.execute("opaque-token")

        assert exc_info.value.details["error"] == "missing_sub"

    @pytest.mark.asyncio
    async def test_maps_expired_token_to_vk_auth_error(self) -> None:
        task = VerifyAuthJwtTask(jwt_verifier=FakeJwtVerifier(error=jwt.ExpiredSignatureError("expired")))

        with pytest.raises(VkAuthenticationError) as exc_info:
            await task.execute("opaque-token")

        assert exc_info.value.details["error"] == "token_expired"


class TestGetVkTokenTask:
    """Focused tests for AuthService-first VK token resolution."""

    @pytest.mark.asyncio
    async def test_prefers_auth_service_token(self) -> None:
        task = GetVkTokenTask(
            settings=SimpleNamespace(
                auth_enable_legacy_db_fallback=True,
                vk_access_token=None,
            ),
            auth_service_client=FakeAuthServiceClient(result="auth-service-token"),
            token_storage=FakeTokenStorage(token="legacy-token"),
        )

        result = await task.execute(GetVkTokenInput(auth_user_id="clauthuser123", jwt_token="jwt-token"))

        assert result == "auth-service-token"

    @pytest.mark.asyncio
    async def test_falls_back_to_legacy_storage_when_enabled(self) -> None:
        account_id = uuid4()
        token_storage = FakeTokenStorage(token="legacy-token")
        task = GetVkTokenTask(
            settings=SimpleNamespace(
                auth_enable_legacy_db_fallback=True,
                vk_access_token=None,
            ),
            auth_service_client=FakeAuthServiceClient(result=None),
            token_storage=token_storage,
        )

        result = await task.execute(GetVkTokenInput(auth_user_id=str(account_id), jwt_token="jwt-token"))

        assert result == "legacy-token"
        assert token_storage.account_ids == [account_id]

    @pytest.mark.asyncio
    async def test_raises_when_auth_service_rejects_without_fallback(self) -> None:
        task = GetVkTokenTask(
            settings=SimpleNamespace(
                auth_enable_legacy_db_fallback=False,
                vk_access_token=None,
            ),
            auth_service_client=FakeAuthServiceClient(
                error=AuthServiceUnauthorizedError("unauthorized"),
            ),
            token_storage=FakeTokenStorage(token=None),
        )

        with pytest.raises(VkAuthenticationError) as exc_info:
            await task.execute(GetVkTokenInput(auth_user_id="clauthuser123", jwt_token="jwt-token"))

        assert exc_info.value.details["error"] == "auth_service_unauthorized"

    @pytest.mark.asyncio
    async def test_raises_when_backend_secret_is_rejected(self) -> None:
        task = GetVkTokenTask(
            settings=SimpleNamespace(
                auth_enable_legacy_db_fallback=False,
                vk_access_token=None,
            ),
            auth_service_client=FakeAuthServiceClient(
                error=AuthServiceForbiddenError("forbidden"),
            ),
            token_storage=FakeTokenStorage(token=None),
        )

        with pytest.raises(VkAuthenticationError) as exc_info:
            await task.execute(GetVkTokenInput(auth_user_id="clauthuser123", jwt_token="jwt-token"))

        assert exc_info.value.details["error"] == "auth_service_forbidden"
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_does_not_fallback_when_vk_account_is_not_linked(self) -> None:
        token_storage = FakeTokenStorage(token="legacy-token")
        task = GetVkTokenTask(
            settings=SimpleNamespace(
                auth_enable_legacy_db_fallback=True,
                vk_access_token="global-fallback-token",
            ),
            auth_service_client=FakeAuthServiceClient(
                error=AuthServiceVkAccountNotLinkedError("not linked"),
            ),
            token_storage=token_storage,
        )

        with pytest.raises(VkAuthenticationError) as exc_info:
            await task.execute(GetVkTokenInput(auth_user_id=str(uuid4()), jwt_token="jwt-token"))

        assert exc_info.value.details["error"] == "no_vk_token"
        assert token_storage.account_ids == []

    @pytest.mark.asyncio
    async def test_raises_when_auth_service_is_down_and_no_fallback_exists(self) -> None:
        task = GetVkTokenTask(
            settings=SimpleNamespace(
                auth_enable_legacy_db_fallback=False,
                vk_access_token=None,
            ),
            auth_service_client=FakeAuthServiceClient(
                error=AuthServiceClientError("network error"),
            ),
            token_storage=FakeTokenStorage(token=None),
        )

        with pytest.raises(VkAuthenticationError) as exc_info:
            await task.execute(GetVkTokenInput(auth_user_id="clauthuser123", jwt_token="jwt-token"))

        assert exc_info.value.details["error"] == "auth_service_unavailable"


class StubTask:
    """Simple async task stub for orchestration tests."""

    def __init__(self, result: Any = None) -> None:
        self._result = result
        self.calls: list[Any] = []

    async def execute(self, data: Any) -> Any:
        self.calls.append(data)
        if callable(self._result):
            return self._result(data)
        return self._result


class FakeProducer:
    """In-memory Kafka producer for task tests."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []
        self.stopped = False

    async def send_and_wait(self, topic: str, payload: dict[str, Any]) -> None:
        self.sent.append((topic, payload))

    async def stop(self) -> None:
        self.stopped = True


class AwaitableWhere:
    """Minimal awaitable query stub with a where-chain."""

    def __init__(self, value: Any) -> None:
        self.value = value

    def where(self, *_args: Any, **_kwargs: Any) -> "AwaitableWhere":
        return self

    def __await__(self):  # type: ignore[override]
        async def _inner() -> Any:
            return self.value

        return _inner().__await__()


class AwaitableUpdate(AwaitableWhere):
    """Awaitable update stub which records payloads."""

    def __init__(self, sink: list[dict[Any, Any]], payload: dict[Any, Any]) -> None:
        super().__init__(value=None)
        self._sink = sink
        self._payload = payload

    def where(self, *_args: Any, **_kwargs: Any) -> "AwaitableUpdate":
        self._sink.append(self._payload)
        return self


def _build_request(*, top_n: int = 10) -> VkParseRequest:
    return VkParseRequest(
        links=["https://vk.com/lentach"],
        start_date=datetime(2024, 1, 1, tzinfo=UTC),
        end_date=datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC),
        top_n=top_n,
        sort_params=SortParams(
            date=SortParamConfig(priority=0, reverse=False),
            engagement_rate=SortParamConfig(priority=0, reverse=False),
            views=SortParamConfig(priority=10, reverse=False),
            comments=SortParamConfig(priority=0, reverse=False),
            reposts=SortParamConfig(priority=0, reverse=False),
        ),
    )


def _build_action(
    *,
    cache_result: CacheCheckResult,
    posts_result: list[dict[str, Any]],
    groups_result: list[dict[str, Any]] | None = None,
    fetch_result: dict[str, Any] | None = None,
) -> tuple[ParseVkDataAction, StubTask, StubTask, StubTask, StubTask, StubTask, StubTask]:
    fetch_task = StubTask(fetch_result or {})
    cache_task = StubTask(cache_result)
    publish_task = StubTask(1)
    save_task = StubTask(0)
    find_groups_task = StubTask(groups_result or [{"id": 123, "name": "Lentach", "screen_name": "lentach", "members_count": 100}])
    find_posts_task = StubTask(posts_result)

    action = ParseVkDataAction(
        fetch_vk_wall_task=fetch_task,
        cache_check_task=cache_task,
        publish_to_kafka_task=publish_task,
        save_parsed_data_task=save_task,
        find_groups_task=find_groups_task,
        find_posts_task=find_posts_task,
        settings=SimpleNamespace(
            kafka_bootstrap_servers="localhost:9092",
            kafka_groups_topic="vk_groups",
            kafka_posts_topic_prefix="vk_posts_",
        ),
    )
    return action, fetch_task, cache_task, publish_task, save_task, find_groups_task, find_posts_task


class TestParseVkDataFlow:
    """Focused tests for cache-aware parse orchestration."""

    @pytest.mark.asyncio
    async def test_full_cache_hit_returns_rebuilt_cached_response(self) -> None:
        request = _build_request(top_n=2)
        cache_result = CacheCheckResult(
            cached_periods={
                "lentach": [
                    Period(
                        start=datetime(2024, 1, 1, tzinfo=UTC),
                        end=datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC),
                    )
                ]
            },
            missing_periods={"lentach": []},
            group_ids={"lentach": 123},
            force_full_parse={"lentach": False},
        )
        posts_result = [
            {
                "id": 1,
                "id_groups": 123,
                "message_timestamp": datetime(2024, 1, 10, tzinfo=UTC),
                "edit_date": None,
                "view_count": 100,
                "reactions_count": 5,
                "comments_count": 3,
                "repost_count": 1,
                "len_message": 50,
            },
            {
                "id": 2,
                "id_groups": 123,
                "message_timestamp": datetime(2024, 1, 11, tzinfo=UTC),
                "edit_date": None,
                "view_count": 300,
                "reactions_count": 7,
                "comments_count": 4,
                "repost_count": 2,
                "len_message": 80,
            },
        ]
        action, fetch_task, _cache_task, publish_task, save_task, _find_groups, _find_posts = _build_action(
            cache_result=cache_result,
            posts_result=posts_result,
        )

        result = await action.execute(("vk-token", request))

        assert fetch_task.calls == []
        assert publish_task.calls == []
        assert save_task.calls == []
        assert result["lentach"]["posts_count"] == 2
        assert result["lentach"]["top_posts"][0]["id"] == 2
        assert result["lentach"]["period_posts_metrics"]["period_posts_count"] == 2

    @pytest.mark.asyncio
    async def test_partial_cache_hit_fetches_each_missing_period_and_rebuilds_from_db(self) -> None:
        request = _build_request(top_n=3)
        first_gap = Period(
            start=datetime(2024, 1, 10, tzinfo=UTC),
            end=datetime(2024, 1, 12, 23, 59, 59, tzinfo=UTC),
        )
        second_gap = Period(
            start=datetime(2024, 1, 20, tzinfo=UTC),
            end=datetime(2024, 1, 22, 23, 59, 59, tzinfo=UTC),
        )
        cache_result = CacheCheckResult(
            cached_periods={},
            missing_periods={"lentach": [first_gap, second_gap]},
            group_ids={"lentach": 123},
            force_full_parse={"lentach": False},
        )
        final_posts = [
            {
                "id": 1,
                "id_groups": 123,
                "message_timestamp": datetime(2024, 1, 5, tzinfo=UTC),
                "edit_date": None,
                "view_count": 10,
                "reactions_count": 1,
                "comments_count": 1,
                "repost_count": 0,
                "len_message": 20,
            },
            {
                "id": 2,
                "id_groups": 123,
                "message_timestamp": datetime(2024, 1, 11, tzinfo=UTC),
                "edit_date": None,
                "view_count": 50,
                "reactions_count": 3,
                "comments_count": 2,
                "repost_count": 1,
                "len_message": 40,
            },
            {
                "id": 3,
                "id_groups": 123,
                "message_timestamp": datetime(2024, 1, 21, tzinfo=UTC),
                "edit_date": None,
                "view_count": 90,
                "reactions_count": 5,
                "comments_count": 3,
                "repost_count": 2,
                "len_message": 60,
            },
        ]
        fetch_result = {
            "lentach": {
                "id": 123,
                "name": "Lentach",
                "screen_name": "lentach",
                "members_count": 100,
                "posts_count": 2,
                "top_posts": [
                    {
                        "id": 3,
                        "date": int(datetime(2024, 1, 21, tzinfo=UTC).timestamp()),
                        "edit_date": None,
                        "views": 90,
                        "likes": 5,
                        "comments": 3,
                        "reposts": 2,
                        "text_len": 60,
                    },
                    {
                        "id": 2,
                        "date": int(datetime(2024, 1, 11, tzinfo=UTC).timestamp()),
                        "edit_date": None,
                        "views": 50,
                        "likes": 3,
                        "comments": 2,
                        "reposts": 1,
                        "text_len": 40,
                    }
                ],
                "down_posts": [
                    {
                        "id": 2,
                        "date": int(datetime(2024, 1, 11, tzinfo=UTC).timestamp()),
                        "edit_date": None,
                        "views": 50,
                        "likes": 3,
                        "comments": 2,
                        "reposts": 1,
                        "text_len": 40,
                    },
                    {
                        "id": 3,
                        "date": int(datetime(2024, 1, 21, tzinfo=UTC).timestamp()),
                        "edit_date": None,
                        "views": 90,
                        "likes": 5,
                        "comments": 3,
                        "reposts": 2,
                        "text_len": 60,
                    }
                ],
                "graph_data": [
                    {
                        "date": int(datetime(2024, 1, 11, tzinfo=UTC).timestamp()),
                        "edit_date": None,
                        "views": 50,
                        "likes": 3,
                        "comments": 2,
                        "reposts": 1,
                        "text_len": 40,
                    },
                    {
                        "date": int(datetime(2024, 1, 21, tzinfo=UTC).timestamp()),
                        "edit_date": None,
                        "views": 90,
                        "likes": 5,
                        "comments": 3,
                        "reposts": 2,
                        "text_len": 60,
                    },
                ],
            }
        }
        action, fetch_task, _cache_task, publish_task, save_task, _find_groups, _find_posts = _build_action(
            cache_result=cache_result,
            posts_result=[final_posts[0]],
            fetch_result=fetch_result,
        )

        result = await action.execute(("vk-token", request))

        assert len(fetch_task.calls) == 2
        assert [call.start_date for call in fetch_task.calls] == [first_gap.start, second_gap.start]
        assert [call.end_date for call in fetch_task.calls] == [first_gap.end, second_gap.end]
        assert len(publish_task.calls) == 2
        assert all(call.kafka_bootstrap_servers == "localhost:9092" for call in publish_task.calls)
        assert len(save_task.calls) == 2
        assert [call.period_start for call in save_task.calls] == [first_gap.start, second_gap.start]
        assert [call.period_end for call in save_task.calls] == [first_gap.end, second_gap.end]
        assert result["lentach"]["posts_count"] == 3
        assert result["lentach"]["top_posts"][0]["id"] == 3

    @pytest.mark.asyncio
    async def test_raw_posts_from_fetch_are_forwarded_to_save_and_publish_and_stripped_from_response(
        self,
    ) -> None:
        """Regression: get_vk_data returns raw PostRow dumps under ``posts``.

        The action must forward them to SaveParsedDataTask and
        PublishToKafkaTask (so posts actually land in PG + Kafka topic
        ``vk_posts_{group_id}``) and strip ``posts`` from the per-domain
        payload before returning to the client.
        """

        request = _build_request(top_n=2)
        gap = Period(
            start=datetime(2024, 1, 10, tzinfo=UTC),
            end=datetime(2024, 1, 20, 23, 59, 59, tzinfo=UTC),
        )
        cache_result = CacheCheckResult(
            cached_periods={},
            missing_periods={"lentach": [gap]},
            group_ids={"lentach": 123},
            force_full_parse={"lentach": False},
        )
        raw_posts = [
            {
                "id": 101,
                "id_groups": 123,
                # Mirrors PostRow.model_dump() (Python mode) — datetime stays datetime.
                # Regression: using model_dump(mode="json") here serializes to str,
                # which breaks VkPost.insert (asyncpg rejects str for timestamptz)
                # and in turn prevents cached_periods from being written.
                "message_timestamp": datetime(2024, 1, 11, tzinfo=UTC),
                "edit_date": None,
                "view_count": 50,
                "reactions_count": 3,
                "comments_count": 2,
                "repost_count": 1,
                "len_message": 40,
            },
            {
                "id": 102,
                "id_groups": 123,
                "message_timestamp": datetime(2024, 1, 15, tzinfo=UTC),
                "edit_date": None,
                "view_count": 90,
                "reactions_count": 5,
                "comments_count": 3,
                "repost_count": 2,
                "len_message": 60,
            },
        ]
        fetch_result = {
            "lentach": {
                "id": 123,
                "name": "Lentach",
                "screen_name": "lentach",
                "members_count": 100,
                "posts_count": 2,
                "top_posts": [],
                "down_posts": [],
                "graph_data": [],
                "posts": raw_posts,
            }
        }
        action, _fetch_task, _cache_task, publish_task, save_task, _find_groups, _find_posts = _build_action(
            cache_result=cache_result,
            posts_result=[],
            fetch_result=fetch_result,
        )

        result = await action.execute(("vk-token", request))

        assert len(save_task.calls) == 1
        assert [p["id"] for p in save_task.calls[0].posts] == [101, 102]
        assert all(p["id_groups"] == 123 for p in save_task.calls[0].posts)
        # Regression: message_timestamp must reach SaveParsedDataTask as
        # datetime, not ISO str — Piccolo/asyncpg INSERT into VkPost
        # (timestamptz) fails otherwise and takes the whole task down,
        # including the subsequent cached_periods upsert.
        assert all(isinstance(p["message_timestamp"], datetime) for p in save_task.calls[0].posts)

        assert len(publish_task.calls) == 1
        assert [p["id"] for p in publish_task.calls[0].posts] == [101, 102]

        assert "posts" not in result["lentach"]


class TestPublishToKafkaTask:
    """Tests for Kafka producer lifecycle and routing."""

    @pytest.mark.asyncio
    async def test_publish_initializes_and_uses_producer(self) -> None:
        producer = FakeProducer()
        task = PublishToKafkaTask(producer=producer)

        published = await task.execute(
            PublishToKafkaInput(
                groups=[{"id": 123, "name": "Lentach", "screen_name": "lentach", "members_count": 100}],
                posts=[
                    {
                        "id": 555,
                        "id_groups": 123,
                        "message_timestamp": datetime(2024, 1, 1, tzinfo=UTC),
                        "edit_date": None,
                        "view_count": 42,
                        "reactions_count": 5,
                        "comments_count": 3,
                        "repost_count": 1,
                        "len_message": 99,
                    }
                ],
                kafka_bootstrap_servers="localhost:9092",
                kafka_groups_topic="vk_groups",
                kafka_posts_topic_prefix="vk_posts_",
            )
        )

        assert published == 2
        assert producer.sent[0][0] == "vk_groups"
        assert producer.sent[1][0] == "vk_posts_123"


class TestVkParseRequestDto:
    """Input normalization lives on the DTO, not on downstream tasks."""

    def test_naive_iso_dates_are_coerced_to_utc_aware(self) -> None:
        request = VkParseRequest(
            links=["https://vk.com/lentach"],
            start_date="2026-04-15",  # type: ignore[arg-type]
            end_date="2026-04-22T00:00:00",  # type: ignore[arg-type]
            top_n=5,
        )

        assert request.start_date.tzinfo is UTC
        assert request.end_date.tzinfo is UTC
        assert request.start_date == datetime(2026, 4, 15, tzinfo=UTC)
        assert request.end_date == datetime(2026, 4, 22, tzinfo=UTC)

    def test_explicit_timezone_is_preserved(self) -> None:
        request = VkParseRequest(
            links=["https://vk.com/lentach"],
            start_date="2026-04-15T00:00:00+03:00",  # type: ignore[arg-type]
            end_date="2026-04-22T00:00:00+03:00",  # type: ignore[arg-type]
            top_n=5,
        )

        assert request.start_date.utcoffset() is not None
        assert request.start_date.utcoffset().total_seconds() == 3 * 3600


class TestCacheAndSaveTasks:
    """Focused tests for period calculations and cached-period writes."""

    def test_calculate_missing_periods_avoids_boundary_overlap(self) -> None:
        missing = calculate_missing_periods(
            request_start=datetime(2024, 1, 1, tzinfo=UTC),
            request_end=datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC),
            cached_periods=[
                Period(
                    start=datetime(2024, 1, 10, tzinfo=UTC),
                    end=datetime(2024, 1, 12, 23, 59, 59, tzinfo=UTC),
                ),
                Period(
                    start=datetime(2024, 1, 20, tzinfo=UTC),
                    end=datetime(2024, 1, 22, 23, 59, 59, tzinfo=UTC),
                ),
            ],
        )

        assert missing == [
            Period(
                start=datetime(2024, 1, 1, tzinfo=UTC),
                end=datetime(2024, 1, 9, 23, 59, 59, 999999, tzinfo=UTC),
            ),
            Period(
                start=datetime(2024, 1, 12, 23, 59, 59, 1, tzinfo=UTC),
                end=datetime(2024, 1, 19, 23, 59, 59, 999999, tzinfo=UTC),
            ),
            Period(
                start=datetime(2024, 1, 22, 23, 59, 59, 1, tzinfo=UTC),
                end=datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC),
            ),
        ]

    @pytest.mark.asyncio
    async def test_save_parsed_data_updates_existing_cached_period_instead_of_inserting_duplicate(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        group_inserts: list[Any] = []
        post_inserts: list[Any] = []
        cached_period_inserts: list[Any] = []
        cached_period_updates: list[dict[Any, Any]] = []

        async def record_group_insert(obj: Any) -> None:
            group_inserts.append(obj)

        async def record_post_insert(obj: Any) -> None:
            post_inserts.append(obj)

        async def record_cached_period_insert(obj: Any) -> None:
            cached_period_inserts.append(obj)

        monkeypatch.setattr(VkGroup, "exists", lambda: AwaitableWhere(False))
        monkeypatch.setattr(VkPost, "exists", lambda: AwaitableWhere(False))
        monkeypatch.setattr(CachedPeriod, "exists", lambda: AwaitableWhere(True))
        monkeypatch.setattr(VkGroup, "insert", record_group_insert)
        monkeypatch.setattr(VkPost, "insert", record_post_insert)
        monkeypatch.setattr(CachedPeriod, "insert", record_cached_period_insert)
        monkeypatch.setattr(CachedPeriod, "update", lambda payload: AwaitableUpdate(cached_period_updates, payload))

        task = SaveParsedDataTask()
        saved = await task.execute(
            SaveParsedDataInput(
                groups=[{"id": 123, "name": "Lentach", "screen_name": "lentach", "members_count": 100}],
                posts=[
                    {
                        "id": 555,
                        "id_groups": 123,
                        "message_timestamp": datetime(2024, 1, 15, tzinfo=UTC),
                        "edit_date": None,
                        "view_count": 42,
                        "reactions_count": 5,
                        "comments_count": 3,
                        "repost_count": 1,
                        "len_message": 99,
                    }
                ],
                period_start=datetime(2024, 1, 1, tzinfo=UTC),
                period_end=datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC),
            )
        )

        assert saved == 1
        assert len(group_inserts) == 1
        assert len(post_inserts) == 1
        assert cached_period_inserts == []
        assert len(cached_period_updates) == 1


class TestVkParserRuntimeMigration:
    """Focused tests for the off-domain VK parser runtime path."""

    def test_runtime_files_do_not_import_domain_modules(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        runtime_files = [
            repo_root / "src/Containers/AppSection/VkParser/Actions/ParseVkDataAction.py",
            repo_root / "src/Containers/AppSection/VkParser/Tasks/FetchVkWallTask.py",
            repo_root / "src/Containers/AppSection/VkParser/Tasks/SearchVkTask.py",
            repo_root / "src/VkParser/service.py",
            repo_root / "src/VkParser/extractors.py",
            repo_root / "src/VkParser/vk_client.py",
            repo_root / "src/VkParser/wall_fetch.py",
        ]

        for path in runtime_files:
            content = path.read_text(encoding="utf-8")
            assert "from domain." not in content
            assert "import domain." not in content
            assert "domain.models.vk" not in content
            assert "domain.parsers.vk" not in content

    @pytest.mark.asyncio
    async def test_fetch_vk_wall_task_uses_internal_service(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        async def fake_get_vk_data(**kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {"lentach": {"posts_count": 0}}

        monkeypatch.setattr(vk_service, "get_vk_data", fake_get_vk_data)

        task = FetchVkWallTask()
        result = await task.execute(
            FetchVkWallInput(
                vk_token="vk-token",
                links=["https://vk.com/lentach"],
                start_date=datetime(2024, 1, 1, tzinfo=UTC),
                end_date=datetime(2024, 1, 31, tzinfo=UTC),
                top_n=5,
                sort_params={"views": {"priority": 1, "reverse": True}},
            )
        )

        assert result == {"lentach": {"posts_count": 0}}
        assert captured["token"] == "vk-token"
        assert captured["links"] == ["https://vk.com/lentach"]
        assert captured["top_n"] == 5

    @pytest.mark.asyncio
    async def test_search_vk_task_uses_internal_service(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        async def fake_search_vk(*, token: str, q: str) -> dict[str, Any]:
            captured["token"] = token
            captured["q"] = q
            return {"items": [{"description": "Lentach"}]}

        monkeypatch.setattr(vk_service, "search_vk", fake_search_vk)

        task = SearchVkTask()
        result = await task.execute(SearchVkInput(vk_token="vk-token", query="lentach"))

        assert result == {"items": [{"description": "Lentach"}]}
        assert captured == {"token": "vk-token", "q": "lentach"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("vk_error_code", "expected_exception", "expected_status", "expected_code"),
        [
            (5, VkAuthenticationError, 401, "VK_AUTH_ERROR"),
            (27, VkAuthenticationError, 401, "VK_AUTH_ERROR"),
            (15, VkAuthenticationError, 403, "VK_AUTH_ERROR"),
            (7, VkAuthenticationError, 403, "VK_AUTH_ERROR"),
        ],
    )
    async def test_search_vk_task_maps_vk_api_error_to_domain_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
        vk_error_code: int,
        expected_exception: type[Exception],
        expected_status: int,
        expected_code: str,
    ) -> None:
        """VkAPIError must not leak raw request_params (access_token) into logs.

        SearchVkTask wraps aiovk's VkAPIError into a domain exception so that
        Logfire's default scrubber stops masking the whole payload as
        ``[Scrubbed due to 'auth']`` and the HTTP layer returns the right
        status code with a clean ``vk_error_code`` field.
        """
        from aiovk.exceptions import VkAPIError

        error_msg = f"VK rejected token with code {vk_error_code}"

        async def fake_search_vk(*, token: str, q: str) -> dict[str, Any]:
            raise VkAPIError(
                {"error_code": vk_error_code, "error_msg": error_msg, "request_params": []},
                url="https://api.vk.com/method/search.getHints",
            )

        monkeypatch.setattr(vk_service, "search_vk", fake_search_vk)

        task = SearchVkTask()
        with pytest.raises(expected_exception) as exc_info:
            await task.execute(SearchVkInput(vk_token="vk-token", query="рбк"))

        assert exc_info.value.status_code == expected_status
        assert exc_info.value.code == expected_code
        assert exc_info.value.details["vk_error_code"] == vk_error_code
        assert exc_info.value.details["vk_error_msg"] == error_msg
        assert exc_info.value.details["vk_method"] == "search.getHints"

    @pytest.mark.asyncio
    async def test_search_vk_task_maps_unknown_vk_error_to_vk_api_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unknown VK error codes must surface as 502 VK_API_ERROR, not 500."""
        from aiovk.exceptions import VkAPIError

        from src.Containers.AppSection.VkParser.Exceptions import VkApiError

        async def fake_search_vk(*, token: str, q: str) -> dict[str, Any]:
            raise VkAPIError(
                {"error_code": 100, "error_msg": "One of the parameters is invalid", "request_params": []},
                url="https://api.vk.com/method/search.getHints",
            )

        monkeypatch.setattr(vk_service, "search_vk", fake_search_vk)

        task = SearchVkTask()
        with pytest.raises(VkApiError) as exc_info:
            await task.execute(SearchVkInput(vk_token="vk-token", query="test"))

        assert exc_info.value.status_code == 502
        assert exc_info.value.code == "VK_API_ERROR"
        assert exc_info.value.details["vk_error_code"] == 100
        assert exc_info.value.details["vk_error_msg"] == "One of the parameters is invalid"

    @pytest.mark.asyncio
    async def test_internal_service_builds_legacy_compatible_parse_payload(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class FakeVkParser:
            def __init__(self, token: str) -> None:
                self.token = token

            async def resolve_domain_links(self, links: list[str]) -> tuple[list[str], list[str], list[Any]]:
                assert links == ["https://vk.com/lentach"]
                return [], ["lentach"], []

            async def get_wall_info(
                self,
                _user_domains: list[str],
                group_domains: list[str],
            ) -> tuple[dict[str, Any], dict[str, Any]]:
                assert group_domains == ["lentach"]
                return {}, {
                    "lentach": {
                        "id": 123,
                        "name": "Lentach",
                        "screen_name": "lentach",
                        "members_count": 1000,
                    }
                }

            async def get_posts_count(self, infos: dict[str, Any]) -> None:
                infos["lentach"].posts_count = 2

            async def get_wall_posts(
                self,
                infos: dict[str, Any],
                _start_date: datetime,
                _end_date: datetime,
            ) -> None:
                infos["lentach"].posts = [
                    {
                        "id": 1,
                        "owner_id": -123,
                        "date": int(datetime(2024, 1, 10, tzinfo=UTC).timestamp()),
                        "edited": None,
                        "text": "a" * 20,
                        "views": {"count": 50},
                        "likes": {"count": 5},
                        "comments": {"count": 2},
                        "reposts": {"count": 1},
                    },
                    {
                        "id": 2,
                        "owner_id": -123,
                        "date": int(datetime(2024, 1, 11, tzinfo=UTC).timestamp()),
                        "edited": None,
                        "text": "b" * 40,
                        "views": {"count": 100},
                        "likes": {"count": 8},
                        "comments": {"count": 3},
                        "reposts": {"count": 2},
                    },
                ]

            async def close(self) -> None:
                return None

        monkeypatch.setattr(vk_service, "VkParser", FakeVkParser)

        result = await vk_service.get_vk_data(
            token="vk-token",
            links=["https://vk.com/lentach"],
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC),
            top_n=1,
            sort_params={
                "date": {"priority": 0, "reverse": False},
                "engagement_rate": {"priority": 0, "reverse": False},
                "views": {"priority": 10, "reverse": False},
                "comments": {"priority": 0, "reverse": False},
                "reposts": {"priority": 0, "reverse": False},
            },
        )

        assert list(result.keys()) == ["lentach"]
        assert result["lentach"]["id"] == 123
        assert result["lentach"]["posts_count"] == 2
        assert result["lentach"]["top_posts"][0]["id"] == 2
        assert result["lentach"]["down_posts"][0]["id"] == 1
        assert "id" not in result["lentach"]["graph_data"][0]
        assert result["lentach"]["period_posts_metrics"]["period_posts_count"] == 2
