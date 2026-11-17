"""Normalización territorial de avisos de Mato Grosso; sin datos simulados."""
import csv
import hashlib
import io
import json
import math
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def municipalities():
    return json.loads((Path(__file__).parent / "data/mato-grosso.geojson").read_text(encoding="utf-8-sig"))["features"]


def in_ring(x, y, ring):
    inside = False
    for a, b in zip(ring, ring[1:]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def contains(geometry, lon, lat):
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    return any(in_ring(lon, lat, p[0]) and not any(in_ring(lon, lat, h) for h in p[1:]) for p in polygons)


@lru_cache(maxsize=1)
def municipal_bounds():
    result = []
    for feature in municipalities():
        geometry = feature["geometry"]
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        points = [point for polygon in polygons for point in polygon[0]]
        result.append((feature, min(p[0] for p in points), min(p[1] for p in points),
                       max(p[0] for p in points), max(p[1] for p in points)))
    return result


def locate(lon, lat):
    return next((f["properties"] for f, west, south, east, north in municipal_bounds() if west <= lon <= east and south <= lat <= north and contains(f["geometry"], lon, lat)), None)


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value).casefold()) if not unicodedata.combining(c))


def fire_features(text, source):
    reader = csv.DictReader(io.StringIO(text))
    if not {"latitude", "longitude", "acq_date", "acq_time"}.issubset(reader.fieldnames or []):
        raise ValueError("Respuesta FIRMS inválida")
    result = {}
    skipped = 0
    for row in reader:
        try:
            lat, lon = float(row["latitude"]), float(row["longitude"])
            if not math.isfinite(lat) or not math.isfinite(lon):
                raise ValueError()
            time = row["acq_time"].zfill(4)
            observed = datetime.strptime(row["acq_date"] + time, "%Y-%m-%d%H%M").replace(tzinfo=timezone.utc).isoformat()
            place = locate(lon, lat)
            if not place:
                continue
            key = hashlib.sha256(f"{source}|{lat}|{lon}|{observed}".encode()).hexdigest()
            result[key] = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"id": key, "kind": "fire", "source": "NASA FIRMS · " + source,
                    "observed_at": observed, "municipality": place["name"], "municipality_code": place["codarea"],
                    "title": "Foco de calor · requiere verificación", "confidence": row.get("confidence", "Sin informar"),
                    "status": "Por verificar"}}
        except (ValueError, KeyError, TypeError):
            skipped += 1
    return list(result.values()), skipped


def deforestation_features(features, source):
    result = []
    skipped = 0
    by_name = {normalized(f["properties"]["name"]): f["properties"]["codarea"] for f in municipalities()}
    for feature in features:
        p = feature.get("properties") or {}
        if p.get("uf") != "MT" or p.get("classname") not in {"DESMATAMENTO_CR", "DESMATAMENTO_VEG", "CICATRIZ_DE_QUEIMADA"}:
            continue
        try:
            observed = datetime.strptime(str(p["view_date"])[:10], "%Y-%m-%d").date().isoformat()
            geometry = feature["geometry"]
            if geometry["type"] not in {"Polygon", "MultiPolygon"} or not geometry["coordinates"]:
                raise ValueError()
            code = p.get("mun_geocod") or by_name.get(normalized(p.get("municipality", "")), "")
            result.append({"type": "Feature", "geometry": geometry, "properties": {
                "id": source + ":" + str(feature.get("id") or p["gid"]), "kind": "burned" if p["classname"] == "CICATRIZ_DE_QUEIMADA" else "deforestation",
                "source": source, "observed_at": observed, "municipality": p.get("municipality", "Sin municipio"),
                "municipality_code": str(code), "title": "Zona quemada · cicatriz DETER" if p["classname"] == "CICATRIZ_DE_QUEIMADA" else "Aviso de deforestación · " + p["classname"],
                "status": "Aviso DETER · no verificado en campo"}})
        except (ValueError, KeyError, TypeError):
            skipped += 1
    return result, skipped
