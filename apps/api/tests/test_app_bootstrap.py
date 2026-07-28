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
    assert "/admin/notifications/{notification_id}/read" in schema["paths"]
