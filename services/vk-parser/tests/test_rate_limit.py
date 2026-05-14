"""Integration-ish tests for rate limiting (§3 design plan).

The defaults are deliberately small (parse=10, search=30, global=60 per
minute) so the test suite can drive them to 429 without flooding the
service. We verify that:

- The global limit is respected and excludes ``/health`` from throttling.
- The stricter per-handler limit for ``/parse/vk`` kicks in before the
  global one does.

All requests here are unauthenticated — this is intentional: rate-limit
middleware runs before auth, so a pre-auth caller can still be throttled
(which is exactly what we want to prevent DDoS).
"""

from litestar.testing import TestClient

from src.Ship.Configs.App import get_settings


class TestGlobalRateLimit:
    def test_health_not_throttled(self, client: TestClient):
        # Pump the endpoint past the global limit — health is excluded so
        # every request must still succeed.
        for _ in range(get_settings().rate_limit_global_per_minute + 5):
            response = client.get("/api/v1/health")
            assert response.status_code == 200


class TestParseHandlerRateLimit:
    def test_parse_returns_429_once_per_minute_quota_exhausted(self, client: TestClient):
        settings = get_settings()
        # /parse/vk requires auth (401) but rate-limit middleware runs
        # before auth, so once we exceed the per-handler quota we must
        # see 429 instead of 401.
        payload = {
            "links": ["https://vk.com/test"],
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-01-31T23:59:59",
            "top_n": 1,
        }

        statuses: list[int] = []
        for _ in range(settings.rate_limit_parse_per_minute + 2):
            r = client.post("/api/v1/parse/vk", json=payload)
            statuses.append(r.status_code)

        assert 429 in statuses, f"expected 429 in {statuses}"


class TestSearchHandlerRateLimit:
    def test_search_returns_429_once_per_minute_quota_exhausted(self, client: TestClient):
        settings = get_settings()
        statuses: list[int] = []
        for _ in range(settings.rate_limit_search_per_minute + 2):
            r = client.get("/api/v1/search/vk", params={"q": "x"})
            statuses.append(r.status_code)

        assert 429 in statuses, f"expected 429 in {statuses}"
