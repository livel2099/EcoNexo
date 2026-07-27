"""Vision satelital aplicada (OpenCV).

Procesa un raster satelital (banda termica / RGB) para detectar zonas de
calor y humo por umbralizacion + morfologia, y devuelve los centroides de
los focos detectados. Si no hay imagen real disponible, sintetiza un raster
de muestra con focos calientes para demostrar el pipeline OpenCV.
"""
from __future__ import annotations

import numpy as np
import cv2


def synth_thermal_raster(w: int = 256, h: int = 256, hotspots: int = 3, seed: int = 7) -> np.ndarray:
    """Genera un raster termico sintetico (0..255) con focos calientes."""
    rng = np.random.default_rng(seed)
    base = rng.normal(90, 12, (h, w)).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(hotspots):
        cy, cx = rng.integers(30, h - 30), rng.integers(30, w - 30)
        r = rng.integers(8, 18)
        blob = 180 * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))
        base += blob
    return np.clip(base, 0, 255).astype(np.uint8)


def detect_heat_zones(raster: np.ndarray, thresh: int = 200) -> list[dict]:
    """Umbraliza la banda termica, limpia con morfologia y extrae contornos.

    Devuelve una lista de focos: centroide (px), area y temperatura relativa.
    """
    _, mask = cv2.threshold(raster, thresh, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    zones: list[dict] = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < 12:
            continue
        m = cv2.moments(c)
        if m["m00"] == 0:
            continue
        cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
        peak = int(raster[int(cy), int(cx)])
        zones.append({
            "px": [round(cx, 1), round(cy, 1)],
            "area_px": round(area, 1),
            "intensity": peak,
            "confidence": round(min(1.0, peak / 255.0), 3),
        })
    return zones


def analyze(raster: np.ndarray | None = None) -> dict:
    if raster is None:
        raster = synth_thermal_raster()
    zones = detect_heat_zones(raster)
    return {"width": raster.shape[1], "height": raster.shape[0], "heat_zones": zones}
