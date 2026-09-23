"""Estadísticas NDVI por polígono, Sentinel-2 L2A / Copernicus CDSE."""
import math
from datetime import date, timedelta
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .copernicus import access_token, CopernicusError


class Polygon(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    type: Literal["Polygon"]
    coordinates: list[list[tuple[float, float]]] = Field(min_length=1, max_length=1)

    @model_validator(mode="after")
    def check_ring(self):
        ring = self.coordinates[0]
        if not 4 <= len(ring) <= 500 or ring[0] != ring[-1] or len(set(ring[:-1])) < 3:
            raise ValueError("Polígono cerrado requerido: entre 4 y 500 vértices")
        if any(not (-180 <= x <= 180 and -80 <= y <= 80) for x, y in ring):
            raise ValueError("Coordenadas fuera de rango WGS84")
        xs, ys = zip(*ring)
        if max(xs)-min(xs) > 0.2 or max(ys)-min(ys) > 0.2:
            raise ValueError("El lote no puede superar 0,2 grados por lado; dividí el área")
        return self


EVALSCRIPT = '''//VERSION=3
function setup() {
 return {input: [{bands: ["B04", "B08", "SCL", "dataMask"]}],
 output: [{id: "ndvi", bands: 1, sampleType: "FLOAT32"}, {id: "dataMask", bands: 1}]};
}
function evaluatePixel(s) {
 const valid = s.dataMask && [4,5,6].includes(s.SCL) && s.B08+s.B04 > 0;
 return {ndvi: [valid ? (s.B08-s.B04)/(s.B08+s.B04) : 0], dataMask: [valid ? 1 : 0]};
}'''


def parse_statistics(payload: dict) -> list[dict]:
    result = []
    for item in payload.get("data", []):
        stats = item.get("outputs", {}).get("ndvi", {}).get("bands", {}).get("B0", {}).get("stats", {})
        count = stats.get("sampleCount", 0)
        missing = stats.get("noDataCount", count)
        mean = stats.get("mean")
        if count <= 0 or missing >= count or not isinstance(mean, (int, float)) or not math.isfinite(mean) or not -1 <= mean <= 1:
            continue
        result.append({"day": item["interval"]["from"][:10], "ndvi": round(mean, 4),
                       "valid_pixel_pct": round(100 * (count-missing)/count, 1)})
    return sorted(result, key=lambda row: row["day"])


async def fetch_ndvi(polygon: Polygon) -> dict:
    today = date.today()
    token = await access_token()
    request = {
        "input": {"bounds": {"geometry": polygon.model_dump(), "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}},
                  "data": [{"type": "sentinel-2-l2a", "dataFilter": {"mosaickingOrder": "leastCC"}}]},
        "aggregation": {"timeRange": {"from": f"{today-timedelta(days=30)}T00:00:00Z", "to": f"{today}T00:00:00Z"},
                        "aggregationInterval": {"of": "P1D"}, "evalscript": EVALSCRIPT,
                        "resx": 0.0001, "resy": 0.0001},
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post("https://sh.dataspace.copernicus.eu/statistics/v1", json=request, headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "OK" or any(item.get("error") for item in payload.get("data", [])):
                raise CopernicusError("Copernicus no completó las estadísticas; intentá nuevamente")
            series = parse_statistics(payload)
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        raise CopernicusError("No se pudo obtener NDVI de Copernicus; verificá disponibilidad y cuota") from exc
    return {"series": series, "source": "Copernicus CDSE · Sentinel-2 L2A · NDVI B08/B04 · máscara SCL 4/5/6",
            "period_start": str(today-timedelta(days=30)), "period_end": str(today),
            "note": "Resolución 0,0001 grados. Cobertura válida conservadora respecto de la grilla solicitada. El agua se conserva para detectar ausencia de vegetación; se excluyen nubes, sombras y nieve. Sin observaciones válidas no se infiere producción.",
            "documentation": "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Statistical/Examples.html"}