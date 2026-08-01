"""Catálogo y validación territorial de EcoNexo para Misiones.

La plataforma usa una lista provincial versionada de 79 municipios y un
polígono operacional local. GeoRef puede complementar la nomenclatura, pero la
operación crítica no depende de un tercero.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass

TERRITORY_VERSION = "2026-07-27"
MISIONES_CENTER = (-26.92, -54.78)
MISIONES_BOUNDS = ((-28.20, -56.10), (-25.45, -53.55))
MISIONES_POLYGON = [
    (-25.50, -54.64), (-25.58, -54.30), (-25.62, -53.98),
    (-25.78, -53.72), (-26.05, -53.60), (-26.30, -53.57),
    (-26.62, -53.68), (-27.02, -53.88), (-27.36, -54.20),
    (-27.62, -54.64), (-27.93, -55.12), (-28.18, -55.66),
    (-27.84, -55.86), (-27.37, -55.96), (-27.06, -55.72),
    (-26.70, -55.42), (-26.35, -55.08), (-25.98, -54.82),
    (-25.66, -54.68), (-25.50, -54.64),
]

@dataclass(frozen=True)
class Municipality:
    name: str
    department: str

@dataclass(frozen=True)
class Hub(Municipality):
    lat: float
    lon: float

MUNICIPALITIES = [
    Municipality("Apóstoles", "Apóstoles"),
    Municipality("Azara", "Apóstoles"),
    Municipality("San José", "Apóstoles"),
    Municipality("Tres Capones", "Apóstoles"),
    Municipality("Aristóbulo del Valle", "Cainguás"),
    Municipality("Campo Grande", "Cainguás"),
    Municipality("Dos de Mayo", "Cainguás"),
    Municipality("Salto Encantado", "Cainguás"),
    Municipality("Bonpland", "Candelaria"),
    Municipality("Candelaria", "Candelaria"),
    Municipality("Cerro Corá", "Candelaria"),
    Municipality("Loreto", "Candelaria"),
    Municipality("Mártires", "Candelaria"),
    Municipality("Profundidad", "Candelaria"),
    Municipality("Santa Ana", "Candelaria"),
    Municipality("Fachinal", "Capital"),
    Municipality("Garupá", "Capital"),
    Municipality("Posadas", "Capital"),
    Municipality("Concepción de la Sierra", "Concepción"),
    Municipality("Santa María", "Concepción"),
    Municipality("9 de Julio", "Eldorado"),
    Municipality("Colonia Delicia", "Eldorado"),
    Municipality("Colonia Victoria", "Eldorado"),
    Municipality("Eldorado", "Eldorado"),
    Municipality("Santiago de Liniers", "Eldorado"),
    Municipality("Bernardo de Irigoyen", "General Manuel Belgrano"),
    Municipality("Comandante Andresito", "General Manuel Belgrano"),
    Municipality("Dos Hermanas", "General Manuel Belgrano"),
    Municipality("San Antonio", "General Manuel Belgrano"),
    Municipality("El Soberbio", "Guaraní"),
    Municipality("Fracrán", "Guaraní"),
    Municipality("San Vicente", "Guaraní"),
    Municipality("Puerto Esperanza", "Iguazú"),
    Municipality("Puerto Iguazú", "Iguazú"),
    Municipality("Puerto Libertad", "Iguazú"),
    Municipality("Wanda", "Iguazú"),
    Municipality("Almafuerte", "Leandro N. Alem"),
    Municipality("Arroyo del Medio", "Leandro N. Alem"),
    Municipality("Caá Yarí", "Leandro N. Alem"),
    Municipality("Cerro Azul", "Leandro N. Alem"),
    Municipality("Dos Arroyos", "Leandro N. Alem"),
    Municipality("Gobernador López", "Leandro N. Alem"),
    Municipality("Leandro N. Alem", "Leandro N. Alem"),
    Municipality("Olegario Víctor Andrade", "Leandro N. Alem"),
    Municipality("Capioví", "Libertador General San Martín"),
    Municipality("El Alcázar", "Libertador General San Martín"),
    Municipality("Garuhapé", "Libertador General San Martín"),
    Municipality("Puerto Leoni", "Libertador General San Martín"),
    Municipality("Puerto Rico", "Libertador General San Martín"),
    Municipality("Ruiz de Montoya", "Libertador General San Martín"),
    Municipality("Caraguatay", "Montecarlo"),
    Municipality("Montecarlo", "Montecarlo"),
    Municipality("Puerto Piray", "Montecarlo"),
    Municipality("Campo Ramón", "Oberá"),
    Municipality("Campo Viera", "Oberá"),
    Municipality("Colonia Alberdi", "Oberá"),
    Municipality("General Alvear", "Oberá"),
    Municipality("Guaraní", "Oberá"),
    Municipality("Los Helechos", "Oberá"),
    Municipality("Oberá", "Oberá"),
    Municipality("Panambí", "Oberá"),
    Municipality("San Martín", "Oberá"),
    Municipality("Colonia Polana", "San Ignacio"),
    Municipality("Corpus Christi", "San Ignacio"),
    Municipality("General Urquiza", "San Ignacio"),
    Municipality("Gobernador Roca", "San Ignacio"),
    Municipality("Hipólito Yrigoyen", "San Ignacio"),
    Municipality("Jardín América", "San Ignacio"),
    Municipality("San Ignacio", "San Ignacio"),
    Municipality("Santo Pipó", "San Ignacio"),
    Municipality("Florentino Ameghino", "San Javier"),
    Municipality("Itacaruaré", "San Javier"),
    Municipality("Mojón Grande", "San Javier"),
    Municipality("San Javier", "San Javier"),
    Municipality("Pozo Azul", "San Pedro"),
    Municipality("San Pedro", "San Pedro"),
    Municipality("25 de Mayo", "25 de Mayo"),
    Municipality("Alba Posse", "25 de Mayo"),
    Municipality("Colonia Aurora", "25 de Mayo"),
]

DEPARTMENTS = tuple(dict.fromkeys(item.department for item in MUNICIPALITIES))

HUBS = [
    Hub("Posadas", "Capital", -27.3621, -55.9007),
    Hub("Garupá", "Capital", -27.4817, -55.8292),
    Hub("Candelaria", "Candelaria", -27.4594, -55.7456),
    Hub("Santa Ana", "Candelaria", -27.3696, -55.5818),
    Hub("San Ignacio", "San Ignacio", -27.2559, -55.5338),
    Hub("Jardín América", "San Ignacio", -27.0437, -55.2265),
    Hub("Puerto Rico", "Libertador General San Martín", -26.8109, -55.024),
    Hub("Montecarlo", "Montecarlo", -26.5662, -54.7574),
    Hub("Eldorado", "Eldorado", -26.4087, -54.6946),
    Hub("Puerto Iguazú", "Iguazú", -25.5972, -54.5786),
    Hub("Comandante Andresito", "General Manuel Belgrano", -25.6694, -54.0451),
    Hub("Bernardo de Irigoyen", "General Manuel Belgrano", -26.2552, -53.6478),
    Hub("San Antonio", "General Manuel Belgrano", -26.01709, -53.78987),
    Hub("San Pedro", "San Pedro", -26.6221, -54.1084),
    Hub("El Soberbio", "Guaraní", -27.2967, -54.1988),
    Hub("Oberá", "Oberá", -27.4871, -55.1199),
    Hub("Leandro N. Alem", "Leandro N. Alem", -27.6034, -55.3249),
    Hub("Apóstoles", "Apóstoles", -27.9143, -55.7541),
    Hub("San Javier", "San Javier", -27.8743, -55.1351),
    Hub("25 de Mayo", "25 de Mayo", -27.3768, -54.7431),
    Hub("Aristóbulo del Valle", "Cainguás", -27.0967, -54.8963),
    Hub("Concepción de la Sierra", "Concepción", -27.9831, -55.5203),
    Hub("San Vicente", "Guaraní", -26.9955, -54.4872),
    Hub("Wanda", "Iguazú", -25.9713, -54.5731),
    Hub("Dos Hermanas", "General Manuel Belgrano", -26.278, -53.757),
]

assert len(MUNICIPALITIES) == 79
assert len(DEPARTMENTS) == 17

def municipality_department(name: str) -> str | None:
    return next((item.department for item in MUNICIPALITIES if item.name == name), None)

def is_in_misiones(lat: float, lon: float) -> bool:
    if not math.isfinite(lat) or not math.isfinite(lon):
        return False
    (south, west), (north, east) = MISIONES_BOUNDS
    if lat < south or lat > north or lon < west or lon > east:
        return False
    inside = False
    j = len(MISIONES_POLYGON) - 1
    for i, (lat_i, lon_i) in enumerate(MISIONES_POLYGON):
        lat_j, lon_j = MISIONES_POLYGON[j]
        intersects = ((lon_i > lon) != (lon_j > lon)) and (
            lat < (lat_j - lat_i) * (lon - lon_i) / ((lon_j - lon_i) or 1e-12) + lat_i
        )
        if intersects:
            inside = not inside
        j = i
    return inside

def ensure_in_misiones(lat: float, lon: float) -> None:
    if not is_in_misiones(lat, lon):
        raise ValueError("La ubicación debe estar dentro de la provincia de Misiones")

def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def nearest_hub(lat: float, lon: float) -> Hub:
    return min(HUBS, key=lambda hub: _distance_km(lat, lon, hub.lat, hub.lon))

def local_context(lat: float, lon: float) -> dict[str, object]:
    inside = is_in_misiones(lat, lon)
    hub = nearest_hub(lat, lon)
    return {
        "inside_misiones": inside,
        "province": "Misiones" if inside else None,
        "nearest_locality": hub.name,
        "department": hub.department,
        "distance_to_reference_km": round(_distance_km(lat, lon, hub.lat, hub.lon), 2),
        "source": "EcoNexo territorial fallback v" + TERRITORY_VERSION,
    }


def decode_geojson_geometry(value: object) -> dict | None:
    """Normaliza una geometría GeoJSON almacenada como JSONB o texto JSON.

    Devuelve ``None`` para valores inválidos, colecciones vacías o tipos que no
    representan una geometría GeoJSON utilizable.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    if not isinstance(value, dict):
        return None

    geometry_type = value.get("type")
    valid_types = {
        "Point", "MultiPoint", "LineString", "MultiLineString",
        "Polygon", "MultiPolygon",
    }
    if geometry_type not in valid_types:
        return None

    coordinates = value.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        return None
    return {"type": geometry_type, "coordinates": coordinates}


def georef_misiones_feature(payload: dict) -> dict | None:
    """Devuelve únicamente la geometría provincial de Misiones de un GeoJSON."""
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        name = str(properties.get("nombre") or properties.get("name") or "").strip().lower()
        if name in {"misiones", "provincia de misiones"}:
            return feature
    return None
