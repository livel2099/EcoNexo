"""anomaly-service — API de scoring de anomalias (PyTorch)."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import asyncpg
from fastapi import FastAPI
from pydantic import BaseModel

from .model import AnomalyModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("econexo.anomaly")

MODEL = AnomalyModel()


def _dsn() -> str:
    # DATABASE_URL primero: al mover la base a Supabase, las POSTGRES_* dejaron
    # de describir un host alcanzable y este servicio seguia apuntando a
    # localhost, entrenando siempre con cero muestras.
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    return (
        f"postgresql://{os.getenv('POSTGRES_USER','econexo')}:"
        f"{os.getenv('POSTGRES_PASSWORD','econexo_dev_pw')}@"
        f"{os.getenv('POSTGRES_HOST','localhost')}:{os.getenv('POSTGRES_PORT','5432')}/"
        f"{os.getenv('POSTGRES_DB','econexo')}"
    )


def _connect_kwargs() -> dict[str, object]:
    """Mismo search_path que el API: las extensiones no viven en `public`."""
    return {
        "server_settings": {
            "search_path": os.getenv("DB_SEARCH_PATH", "public,extensions")
        }
    }


async def _train_from_db() -> None:
    try:
        conn = await asyncpg.connect(_dsn(), **_connect_kwargs())
    except Exception as exc:
        log.warning("No se pudo conectar a la DB para entrenar: %s", exc)
        return
    try:
        rows = await conn.fetch(
            "SELECT variable, value, ts FROM readings "
            "WHERE ts > now() - interval '30 days' ORDER BY ts"
        )
        data = [(r["variable"], float(r["value"]), r["ts"].hour) for r in rows]
        n = MODEL.train(data)
        log.info("Autoencoder entrenado con %d muestras (%d variables)", n, len(MODEL.var_stats))
    finally:
        await conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _train_from_db()
    yield


app = FastAPI(title="EcoNexo anomaly-service", version="0.1.0", lifespan=lifespan)


class ScoreIn(BaseModel):
    device_id: str
    variable: str
    value: float
    hour: int | None = None


class ScoreOut(BaseModel):
    score: float
    trained: bool


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "trained": MODEL.trained, "variables": list(MODEL.var_stats)}


@app.post("/score", response_model=ScoreOut)
async def score(body: ScoreIn) -> ScoreOut:
    hour = body.hour if body.hour is not None else datetime.now(timezone.utc).hour
    return ScoreOut(score=MODEL.score(body.variable, body.value, hour), trained=MODEL.trained)


@app.post("/retrain")
async def retrain() -> dict:
    await _train_from_db()
    return {"trained": MODEL.trained, "variables": list(MODEL.var_stats)}
