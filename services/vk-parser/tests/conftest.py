"""Test configuration for VK Parser Service."""

import pytest
from litestar.testing import TestClient

from src.Ship.App import create_app


@pytest.fixture()
def app():
    """Create application instance for testing."""
    return create_app()


@pytest.fixture()
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture()
def test_account_id() -> str:
    """Stable AuthService-style user id for test account."""
    return "cltestuser1234567890abcdef"


@pytest.fixture()
def bearer_token_value() -> str:
    """Opaque bearer token used in auth-flow tests."""
    return "test.bearer.token"


@pytest.fixture()
def legacy_cookie_token_value() -> str:
    """Opaque legacy cookie token used in compatibility tests."""
    return "legacy.cookie.token"
