"""Copernicus predeterminado: Process API y fallback WMS por organizacion."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from .. import db
from ..audit import record_audit
from ..config import get_settings
from ..copernicus import (
    CopernicusError,
    process_image,
    public_status,
    resolve_provider,
    system_wms_url,
    test_process_api,
    test_wms,
    validate_bbox,
    validate_layer,
)
from ..deps import CurrentUser, current_user, require_role
from ..rate_limit import enforce_rate_limit
from ..schemas import CopernicusStatusOut, CopernicusTestIn, CopernicusWmsTestOut

router = APIRouter(prefix="/copernicus", tags=["copernicus"])


async def _settings_row(org_id) -> Any:
    row = await db.pool().fetchrow(
        """
        INSERT INTO environmental_source_settings (org_id, copernicus_enabled, copernicus_use_system_default)
        VALUES ($1,true,true)
        ON CONFLICT (org_id) DO NOTHING
        RETURNING *
        """,
        org_id,
    )
    if row is None:
        row = await db.pool().fetchrow(
            "SELECT * FROM environmental_source_settings WHERE org_id=$1",
            org_id,
        )
    return row


@router.get("/status", response_model=CopernicusStatusOut)
async def status(user: CurrentUser = Depends(current_user)) -> CopernicusStatusOut:
    row = await _settings_row(user.org_id)
    return CopernicusStatusOut(**public_status(dict(row)))


@router.post("/test", response_model=CopernicusWmsTestOut)
async def test_copernicus(
    body: CopernicusTestIn,
    request: Request,
    user: CurrentUser = Depends(require_role("admin")),
) -> CopernicusWmsTestOut:
    await enforce_rate_limit(request, bucket="copernicus-test", limit=10, window_seconds=300)
    row = await _settings_row(user.org_id)
    settings = get_settings()
    resolution = resolve_provider(dict(row), settings)
    provider = body.provider
    if provider == "auto":
        provider = resolution.provider
    if provider == "none":
        provider = "process_api" if settings.copernicus_process_configured else "wms"

    ok = False
    title = None
    layers: list[str] = []
    detail = ""
    try:
        if provider == "process_api":
            size = await test_process_api(settings)
            ok = True
            layers = ["TRUE_COLOR", "NDVI", "MOISTURE_INDEX", "NBR_RAW"]
            title = "Sentinel Hub Process API · Sentinel-2 L2A"
            detail = f"Conexión correcta. Imagen de prueba PNG recibida ({size} bytes)."
        else:
            url = body.url or resolution.effective_wms_url or system_wms_url(settings)
            if not url:
                raise CopernicusError(
                    "No existe una URL WMS efectiva. Configurá INSTANCE_ID o usá Process API."
                )
            title, layers = await test_wms(url, settings)
            ok = True
            detail = f"Conexión WMS correcta. {len(layers)} capas informadas por GetCapabilities."
    except (CopernicusError, ValueError) as exc:
        detail = str(exc)

    await db.pool().execute(
        """
        UPDATE environmental_source_settings SET
          copernicus_last_test_at=now(), copernicus_last_test_ok=$2,
          copernicus_last_error=$3,
          copernicus_available_layers=$4::jsonb,
          updated_by=$5, updated_at=now()
        WHERE org_id=$1
        """,
        user.org_id,
        ok,
        None if ok else detail[:1000],
        __import__("json").dumps(layers[:100], ensure_ascii=False),
        user.id,
    )
    await record_audit(
        org_id=user.org_id,
        user_id=user.id,
        action="test",
        resource="copernicus",
        resource_id=user.org_id,
        metadata={"provider": provider, "ok": ok, "layers": layers[:30]},
    )
    return CopernicusWmsTestOut(
        ok=ok,
        provider=provider,
        configured=ok,
        service_title=title,
        layers=layers[:100],
        detail=detail,
    )


@router.get("/image")
async def image(
    request: Request,
    layer: str = Query(default="TRUE_COLOR", min_length=2, max_length=40),
    west: float = Query(..., ge=-180, le=180),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    north: float = Query(..., ge=-90, le=90),
    width: int = Query(default=768, ge=64, le=1024),
    height: int = Query(default=512, ge=64, le=1024),
    user: CurrentUser = Depends(current_user),
) -> Response:
    await enforce_rate_limit(request, bucket="copernicus-image", limit=60, window_seconds=60)
    row = await _settings_row(user.org_id)
    resolution = resolve_provider(dict(row))
    if not resolution.configured:
        raise HTTPException(
            503,
            "Copernicus todavía no tiene credenciales OAuth ni una instancia WMS configurada",
        )
    if resolution.provider != "process_api":
        raise HTTPException(
            409,
            "La organización usa WMS directo; el frontend debe consumir la URL WMS efectiva",
        )
    try:
        normalized_layer = validate_layer(layer)
        bbox = validate_bbox(west, south, east, north)
        content = await process_image(
            layer=normalized_layer,
            bbox=bbox,
            width=width,
            height=height,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except CopernicusError as exc:
        raise HTTPException(502, str(exc)) from exc

    return Response(
        content=content,
        media_type="image/png",
        headers={
            "Cache-Control": "private, max-age=300",
            "X-Copernicus-Layer": normalized_layer,
            "X-Copernicus-Provider": "process_api",
        },
    )
