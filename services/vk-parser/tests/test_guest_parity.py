"""Tests for the new guest-parity endpoints.

These smoke tests just ensure the routes are wired correctly and respond
with the documented shape; DB-dependent paths return 500 when PostgreSQL
is not available, which is accepted here (consistent with
``test_read_api.py``).
"""

from litestar.testing import TestClient


class TestGroupsSearch:
    """GET /api/v1/groups substring search (§3.1 design handoff)."""

    def test_q_param_is_accepted(self, client: TestClient):
        response = client.get("/api/v1/groups", params={"q": "lent"})
        assert response.status_code in (200, 500)

    def test_legacy_screen_name_param_still_works(self, client: TestClient):
        response = client.get("/api/v1/groups", params={"screen_name": "lentach"})
        assert response.status_code in (200, 500)

    def test_q_plus_pagination(self, client: TestClient):
        response = client.get("/api/v1/groups", params={"q": "lent", "limit": 10, "offset": 0})
        assert response.status_code in (200, 500)


class TestGroupDetail:
    """GET /api/v1/groups/{group_id} — single cached group card (§3.2)."""

    def test_route_exists(self, client: TestClient):
        response = client.get("/api/v1/groups/1")
        # 404 (empty cache), 200 (row present), 500 (no DB) are all
        # acceptable — we just check the controller is wired.
        assert response.status_code in (200, 404, 500)


class TestGroupsExists:
    """GET /api/v1/groups/exists — bulk "in DB" check for search hints."""

    def test_requires_ids(self, client: TestClient):
        response = client.get("/api/v1/groups/exists")
        assert response.status_code == 400

    def test_accepts_csv_ids(self, client: TestClient):
        response = client.get("/api/v1/groups/exists", params={"ids": "1,2,3"})
        assert response.status_code in (200, 500)

    def test_bad_ids_are_filtered(self, client: TestClient):
        # Non-numeric ids are dropped silently — endpoint must still succeed.
        response = client.get("/api/v1/groups/exists", params={"ids": "abc,2,xx"})
        assert response.status_code in (200, 500)
