from __future__ import annotations

import pytest

pytest.importorskip("asyncpg")
pytest.importorskip("aiomqtt")
pytest.importorskip("jose")


def test_fastapi_routes_and_openapi_can_be_created() -> None:
    from app.main import app

    schema = app.openapi()
    assert "/health" in schema["paths"]
    assert "/auth/register" in schema["paths"]
    assert "/auth/community/register" in schema["paths"]
    assert "/foi/posts" in schema["paths"]
    assert "/admin/notifications/{notification_id}/read" in schema["paths"]
    assert "/auth/change-password" in schema["paths"]
    assert not any(path.startswith("/platform") for path in schema["paths"])
    route_paths = {route.path for route in app.routes}
    assert "/platform/summary" in route_paths
    assert "/platform/users" in route_paths
