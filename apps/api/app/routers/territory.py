"""Configuración territorial de Misiones y resolución de coordenadas."""
from __future__ import annotations

import asyncio

import httpx

from .. import db
from ..deps import CurrentUser, require_role
from fastapi import APIRouter, Depends, HTTPException, Query

from ..territory import (
    DEPARTMENTS,
    HUBS,
    MUNICIPALITIES,
    MISIONES_BOUNDS,
    MISIONES_CENTER,
    MISIONES_POLYGON,
    TERRITORY_VERSION,
    local_context,
    georef_misiones_feature,
)

router = APIRouter(prefix="/territory", tags=["territory"])
GEOREF_REVERSE_URL = "https://apis.datos.gob.ar/georef/api/ubicacion"
GEOREF_PROVINCES_GEOJSON_URL = "https://apis.datos.gob.ar/georef/api/v2.0/provincias.geojson"


@router.get("/config")
async def territory_config() -> dict:
    return {
        "province": "Misiones",
        "country": "Argentina",
        "version": TERRITORY_VERSION,
        "departments_count": len(DEPARTMENTS),
        "municipalities_count": len(MUNICIPALITIES),
        "departments": list(DEPARTMENTS),
        "municipalities": [item.__dict__ for item in MUNICIPALITIES],
        "center": {"lat": MISIONES_CENTER[0], "lon": MISIONES_CENTER[1]},
        "bounds": {
            "south": MISIONES_BOUNDS[0][0],
            "west": MISIONES_BOUNDS[0][1],
            "north": MISIONES_BOUNDS[1][0],
            "east": MISIONES_BOUNDS[1][1],
        },
        "polygon": [{"lat": lat, "lon": lon} for lat, lon in MISIONES_POLYGON],
        "operational_hubs": [hub.__dict__ for hub in HUBS],
        "emergency_number": "911",
        "scope": "Provincia de Misiones",
        "normalization": "Catálogo provincial EcoNexo + GeoRef IGN/INDEC cuando está disponible",
    }


async def _georef_context(lat: float, lon: float) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
            response = await client.get(GEOREF_REVERSE_URL, params={"lat": lat, "lon": lon})
            response.raise_for_status()
        payload = response.json()
        ubicacion = payload.get("ubicacion") or payload.get("ubicaciones", [None])[0]
        if not ubicacion:
            return None
        provincia = ubicacion.get("provincia") or {}
        departamento = ubicacion.get("departamento") or {}
        municipio = ubicacion.get("municipio") or {}
        return {
            "province": provincia.get("nombre"),
            "department": departamento.get("nombre"),
            "municipality": municipio.get("nombre"),
            "georef_source": "GeoRef Argentina (IGN/INDEC)",
        }
    except (httpx.HTTPError, KeyError, TypeError, IndexError, asyncio.TimeoutError):
        return None


@router.get("/resolve")
async def resolve_location(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    enrich: bool = Query(default=True),
) -> dict:
    context = local_context(lat, lon)
    if not context["inside_misiones"]:
        raise HTTPException(422, "La coordenada está fuera de la provincia de Misiones")
    if enrich:
        external = await _georef_context(lat, lon)
        if external and external.get("province") == "Misiones":
            context.update({key: value for key, value in external.items() if value})
    return context



@router.get("/geojson")
async def territory_geojson() -> dict:
    """Límite de Misiones: prioriza GeoRef oficial y usa fallback si aún no fue sincronizado."""
    try:
        row = await db.pool().fetchrow(
            """
            SELECT source, source_version, is_official, ST_AsGeoJSON(boundary)::jsonb AS geometry
            FROM territory_boundaries
            WHERE province='Misiones'
            ORDER BY is_official DESC, fetched_at DESC NULLS LAST, updated_at DESC
            LIMIT 1
            """
        )
    except Exception:
        row = None
    if row:
        return {
            "type": "Feature",
            "properties": {
                "province": "Misiones",
                "source": row["source"],
                "source_version": row["source_version"],
                "official": bool(row["is_official"]),
            },
            "geometry": row["geometry"],
        }
    coordinates = [[[lon, lat] for lat, lon in MISIONES_POLYGON]]
    return {
        "type": "Feature",
        "properties": {
            "province": "Misiones",
            "source": "EcoNexo fallback operativo",
            "source_version": TERRITORY_VERSION,
            "official": False,
        },
        "geometry": {"type": "Polygon", "coordinates": coordinates},
    }


@router.get("/boundary-status")
async def boundary_status() -> dict:
    try:
        rows = await db.pool().fetch(
            """
            SELECT source, source_version, source_url, is_official, fetched_at, updated_at,
                   round((ST_Area(boundary::geography) / 1000000.0)::numeric, 2) AS area_km2
            FROM territory_boundaries
            WHERE province='Misiones'
            ORDER BY is_official DESC, fetched_at DESC NULLS LAST, updated_at DESC
            """
        )
    except Exception:
        return {"province": "Misiones", "available": False, "official": False, "boundaries": []}
    return {
        "province": "Misiones",
        "available": bool(rows),
        "official": any(bool(row["is_official"]) for row in rows),
        "boundaries": [dict(row) for row in rows],
    }


@router.post("/sync-georef")
async def sync_georef_boundary(
    user: CurrentUser = Depends(require_role("admin")),
) -> dict:
    """Sincroniza el límite provincial oficial publicado por GeoRef Argentina."""
    del user  # el rol ya fue validado por la dependencia
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            response = await client.get(GEOREF_PROVINCES_GEOJSON_URL)
            response.raise_for_status()
        feature = georef_misiones_feature(response.json())
        if not feature or not feature.get("geometry"):
            raise HTTPException(502, "GeoRef no devolvió la geometría de Misiones")
        import json
        geometry_json = json.dumps(feature["geometry"], separators=(",", ":"))
        await db.pool().execute(
            """
            INSERT INTO territory_boundaries (
              province, source, source_version, source_url, is_official, boundary, fetched_at
            )
            VALUES (
              'Misiones', 'GeoRef Argentina (IGN/INDEC)', 'v2.0', $1, true,
              ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON($2), 4326)), now()
            )
            ON CONFLICT (province, source) DO UPDATE SET
              source_version=EXCLUDED.source_version,
              source_url=EXCLUDED.source_url,
              is_official=true,
              boundary=EXCLUDED.boundary,
              fetched_at=now(),
              updated_at=now()
            """,
            GEOREF_PROVINCES_GEOJSON_URL,
            geometry_json,
        )
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise HTTPException(502, f"No se pudo sincronizar GeoRef: {exc.__class__.__name__}") from exc
    return {
        "status": "ok",
        "province": "Misiones",
        "source": "GeoRef Argentina (IGN/INDEC)",
        "official": True,
    }
