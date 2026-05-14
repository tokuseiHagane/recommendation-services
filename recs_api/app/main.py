from __future__ import annotations

from litestar import Litestar

from recs_api.app.routes import health_check, recommend


def create_app() -> Litestar:
    return Litestar(
        route_handlers=[health_check, recommend],
        debug=True,
    )


app = create_app()
