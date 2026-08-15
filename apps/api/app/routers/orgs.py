"""Organizaciones (scope multi-org)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import db
from ..deps import CurrentUser, current_user
from ..schemas import OrgOut

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.get("/me", response_model=OrgOut)
async def my_org(user: CurrentUser = Depends(current_user)) -> OrgOut:
    row = await db.pool().fetchrow(
        "SELECT id, name, slug, vertical, primary_color, baseline_response_s "
        "FROM organizations WHERE id=$1",
        user.org_id,
    )
    return OrgOut(**dict(row))


@router.get("/public")
async def public_orgs() -> list[dict]:
    """Lista publica de organizaciones/territorios (para la PWA ciudadana)."""
    rows = await db.pool().fetch(
        "SELECT id, name, vertical, primary_color FROM organizations ORDER BY name"
    )
    return [dict(r) | {"id": str(r["id"])} for r in rows]
