"""Tests for Read API endpoints (groups, posts).

These tests verify routing and controller wiring. DB-dependent tests
return 500 when PostgreSQL is not available (expected in local dev
without Docker). Full integration tests require ``docker-compose up``.
"""

from litestar.testing import TestClient


class TestReadGroupsAPI:
    """Tests for GET /api/v1/groups."""

    def test_list_groups_route_exists(self, client: TestClient):
        """Groups endpoint is routed and reachable (may 500 without DB)."""
        response = client.get("/api/v1/groups")
        assert response.status_code in (200, 500)

    def test_list_groups_with_filter(self, client: TestClient):
        """Groups endpoint accepts screen_name query parameter."""
        response = client.get("/api/v1/groups", params={"screen_name": "lentach"})
        assert response.status_code in (200, 500)

    def test_list_groups_bad_limit(self, client: TestClient):
        """Validation rejects limit > 200."""
        response = client.get("/api/v1/groups", params={"limit": 999})
        assert response.status_code == 400


class TestReadPostsAPI:
    """Tests for GET /api/v1/groups/{group_id}/posts."""

    def test_list_posts_route_exists(self, client: TestClient):
        """Posts endpoint is routed and reachable (may 500 without DB)."""
        response = client.get("/api/v1/groups/12345/posts")
        assert response.status_code in (200, 500)

    def test_list_posts_with_date_filter(self, client: TestClient):
        """Posts endpoint accepts date range filters."""
        response = client.get(
            "/api/v1/groups/12345/posts",
            params={"start_date": "2024-01-01T00:00:00", "end_date": "2024-12-31T23:59:59"},
        )
        assert response.status_code in (200, 500)

    def test_list_posts_bad_limit(self, client: TestClient):
        """Validation rejects limit > 200."""
        response = client.get("/api/v1/groups/12345/posts", params={"limit": 999})
        assert response.status_code == 400

    def test_list_posts_accepts_date_only_filter(self, client: TestClient):
        """Frontend sends ``YYYY-MM-DD`` via ``toISOString().slice(0, 10)``.

        Controller must accept date-only form in addition to RFC3339
        datetimes, otherwise legitimate queries get a 400.
        """
        response = client.get(
            "/api/v1/groups/12345/posts",
            params={"start_date": "2026-03-24", "end_date": "2026-04-23", "limit": 200},
        )
        assert response.status_code in (200, 500)

    def test_list_posts_accepts_mixed_date_forms(self, client: TestClient):
        """Mixing date-only and RFC3339 in one request is allowed."""
        response = client.get(
            "/api/v1/groups/12345/posts",
            params={"start_date": "2026-03-24", "end_date": "2026-04-23T23:59:59Z"},
        )
        assert response.status_code in (200, 500)

    def test_list_posts_rejects_garbage_date(self, client: TestClient):
        """Clearly broken date strings surface as 400, not 500."""
        response = client.get(
            "/api/v1/groups/12345/posts",
            params={"start_date": "not-a-date"},
        )
        assert response.status_code == 400
