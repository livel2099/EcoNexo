from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app import deps, subscriptions
from app.deps import CurrentUser
from app.routers import platform, subscriptions as routes
from app.schemas import PlatformPasswordResetIn, PlatformUserUpdateIn


class Context:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *args):
        return False


@pytest.fixture
def database(monkeypatch):
    pool = SimpleNamespace(fetchrow=AsyncMock(), fetchval=AsyncMock(), execute=AsyncMock(), fetch=AsyncMock())
    pool.acquire = lambda: Context(pool)
    pool.transaction = lambda: Context(pool)
    monkeypatch.setattr(deps.db, "pool", lambda: pool)
    return pool


@pytest.fixture
def identity(monkeypatch, database):
    actor = CurrentUser(uuid4(), uuid4(), "admin", "owner@example.com", platform_admin=True)
    row = dict(org_id=actor.org_id, role="admin", email=actor.email, account_type="institutional",
               is_active=True, organization_active=True, access_status="approved", token_version=0,
               must_change_password=False)
    payload = dict(sub=str(actor.id), org_id=str(actor.org_id), role="visualizador", email=actor.email,
                   platform_admin=False, token_version=0)
    monkeypatch.setattr(deps, "decode_token", lambda token: payload)
    monkeypatch.setattr(deps, "get_settings", lambda: SimpleNamespace(platform_admin_list=[actor.email]))
    monkeypatch.setattr(platform, "get_settings", lambda: SimpleNamespace(platform_admin_list=[actor.email]))
    database.fetchrow.return_value = row
    return actor, row, payload


def request(path):
    return Request({"type": "http", "path": path, "headers": [], "method": "GET"})


@pytest.mark.asyncio
async def test_live_role_restores_admin_core_without_new_login(database, identity):
    user = await deps.current_user("Bearer test", request("/admin/summary"))
    assert user.role == "admin"
    assert user.platform_admin


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value,expected", [
    ("is_active", False, 401), ("organization_active", False, 403),
    ("access_status", "pending", 403), ("token_version", 1, 401),
    ("must_change_password", True, 403),
])
async def test_existing_sessions_obey_account_changes(database, identity, field, value, expected):
    identity[1][field] = value
    with pytest.raises(HTTPException) as failure:
        await deps.current_user("Bearer test", request("/admin/summary"))
    assert failure.value.status_code == expected


@pytest.mark.asyncio
async def test_demotion_ignores_old_privileged_token(identity):
    identity[1]["role"] = "operador"
    identity[2].update(role="admin", platform_admin=True)
    user = await deps.current_user("Bearer test", request("/auth/me"))
    assert user.role == "operador"
    with pytest.raises(HTTPException):
        deps.require_platform_admin(user)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["cancelled", "suspended", "expired"])
async def test_inactive_license_blocks_operation_but_keeps_admin_core(database, identity, status):
    identity[1]["email"] = "admin@organization.com"
    license_row = dict(status=status, expires_at=None, database_now=datetime.now(timezone.utc))
    database.fetchrow.side_effect = [identity[1], license_row]
    with pytest.raises(HTTPException) as failure:
        await deps.current_user("Bearer test", request("/alerts"))
    assert failure.value.status_code == 402
    database.fetchrow.side_effect = None
    database.fetchrow.return_value = identity[1]
    assert (await deps.current_user("Bearer test", request("/admin/summary"))).role == "admin"
    assert (await deps.current_user("Bearer test", request("/subscriptions/me"))).role == "admin"


@pytest.mark.asyncio
async def test_temporary_password_allows_only_session_and_password_routes(identity):
    identity[1]["must_change_password"] = True
    await deps.current_user("Bearer test", request("/auth/change-password"))
    await deps.current_user("Bearer test", request("/auth/me"))


def test_every_plan_and_custom_module_list_keep_core():
    for plan in subscriptions.PLAN_DEFINITIONS.values():
        row = dict(plan_entitlements=plan["entitlements"], custom_entitlements={"included_modules": ["ecocampo"]})
        assert subscriptions.merged_entitlements(row)["included_modules"] == ["core", "ecocampo"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status,expiry", [("cancelled", None), ("active", datetime.now(timezone.utc) - timedelta(days=1))])
async def test_module_sync_does_not_reactivate_cancelled_or_expired_licenses(database, status, expiry):
    row = dict(status=status, expires_at=expiry, database_now=datetime.now(timezone.utc),
               plan_entitlements={"included_modules": ["core", "agro", "ecocampo"]}, custom_entitlements={})
    await subscriptions.sync_modules(uuid4(), subscription=row, conn=database)
    calls = database.execute.call_args_list
    assert len(calls) == 5
    assert all(call.args[3] == "suspended" and call.args[-1] is False for call in calls)


@pytest.mark.asyncio
async def test_cancel_keeps_contract_and_records_history(database, identity):
    database.fetchrow.return_value = {"plan_key": "municipal", "status": "active"}
    result = await routes.cancel_platform_subscription(uuid4(), identity[0])
    assert result == {"status": "cancelled"}
    statements = [call.args[0] for call in database.execute.call_args_list]
    assert any("auto_renew=false" in sql for sql in statements)
    assert any("organization_modules" in sql and "suspended" in sql for sql in statements)
    assert any("subscription_events" in sql for sql in statements)
    assert any("audit_events" in sql for sql in statements)
    assert not any("DELETE" in sql or "custom_entitlements=" in sql for sql in statements)


@pytest.mark.asyncio
async def test_cancel_is_idempotent(database, identity):
    database.fetchrow.return_value = {"plan_key": "municipal", "status": "cancelled"}
    assert await routes.cancel_platform_subscription(uuid4(), identity[0]) == {"status": "cancelled"}
    database.execute.assert_not_awaited()


def test_organization_admin_cannot_manage_other_organizations(identity):
    app = FastAPI()
    app.include_router(platform.router)
    app.include_router(routes.router)
    actor = CurrentUser(uuid4(), uuid4(), "admin", "tenant@example.com")
    app.dependency_overrides[deps.current_user] = lambda: actor
    with TestClient(app) as client:
        target = str(uuid4())
        assert client.post(f"/subscriptions/platform/{target}/cancel").status_code == 403
        assert client.patch(f"/platform/users/{target}", json={"email": "next@example.com"}).status_code == 403
        assert client.post(f"/platform/users/{target}/reset-password", json={"temporary_password": "Temporary2026!"}).status_code == 403


@pytest.mark.asyncio
async def test_contact_edit_normalizes_email_and_revokes_old_identity(database, identity, monkeypatch):
    target = uuid4()
    database.fetchrow.return_value = dict(id=target, org_id=uuid4(), email="old@example.com", role="admin", is_active=True)
    database.fetchval.return_value = False
    monkeypatch.setattr(platform, "_user_out", AsyncMock(return_value={"id": target}))
    audit = AsyncMock()
    monkeypatch.setattr(platform, "record_audit", audit)
    await platform.update_user(target, PlatformUserUpdateIn(name="Nombre corregido", email="NEW@example.com", phone=""), identity[0])
    sql, *params = database.execute.call_args.args
    assert params[4] == "new@example.com"
    assert params[5:] == [True, "", True]
    assert "token_version=token_version" in sql and "google_sub=CASE" in sql
    assert audit.call_args.kwargs["metadata"]["name"] == "Nombre corregido"


@pytest.mark.asyncio
async def test_cannot_remove_last_admin_or_take_protected_email(database, identity):
    target = uuid4()
    database.fetchrow.return_value = dict(id=target, org_id=uuid4(), email="old@example.com", role="admin", is_active=True)
    database.fetchval.return_value = 0
    for change in [{"role": "operador"}, {"is_active": False}, {"email": identity[0].email}]:
        with pytest.raises(HTTPException) as failure:
            await platform.update_user(target, PlatformUserUpdateIn(**change), identity[0])
        assert failure.value.status_code == 409
    database.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_email_is_a_conflict(database, identity):
    target = uuid4()
    database.fetchrow.return_value = dict(id=target, org_id=uuid4(), email="old@example.com", role="admin", is_active=True)
    database.fetchval.return_value = True
    with pytest.raises(HTTPException) as failure:
        await platform.update_user(target, PlatformUserUpdateIn(email="taken@example.com"), identity[0])
    assert failure.value.status_code == 409
    database.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_password_reset_revokes_sessions_without_reactivating_paused_user(database, identity, monkeypatch):
    target = uuid4()
    database.fetchrow.return_value = dict(id=target, org_id=uuid4(), email="target@example.com")
    audit = AsyncMock()
    monkeypatch.setattr(platform, "record_audit", audit)
    password = "TemporarySecure2026!"
    await platform.reset_password(target, PlatformPasswordResetIn(temporary_password=password), identity[0])
    sql, _, hashed = database.execute.call_args.args
    assert hashed != password
    assert "token_version=token_version+1" in sql
    assert "is_active=true" not in sql
    assert password not in str(audit.call_args)


def test_http_dependency_applies_license_guard_and_allows_management(database, identity):
    app = FastAPI()
    identity[1]['email'] = 'tenant@example.com'

    @app.get('/alerts')
    @app.get('/admin/summary')
    async def protected(user=Depends(deps.current_user)):
        return {'role': user.role}

    database.fetchrow.side_effect = [identity[1], dict(status='cancelled', expires_at=None, database_now=datetime.now(timezone.utc)), identity[1]]
    with TestClient(app) as client:
        assert client.get('/alerts', headers={'Authorization': 'Bearer test'}).status_code == 402
        response = client.get('/admin/summary', headers={'Authorization': 'Bearer test'})
        assert response.status_code == 200
        assert response.json()['role'] == 'admin'
