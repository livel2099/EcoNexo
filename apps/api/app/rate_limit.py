"""Limitador liviano por proceso para endpoints publicos.

Es una defensa de dia cero. En despliegues con multiples replicas debe
reemplazarse por un backend compartido (Redis, API Gateway o WAF).
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = asyncio.Lock()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> None:
    now = time.monotonic()
    key = f"{bucket}:{client_ip(request)}"
    cutoff = now - window_seconds
    async with _lock:
        values = _hits[key]
        while values and values[0] < cutoff:
            values.popleft()
        if len(values) >= limit:
            retry_after = max(1, int(window_seconds - (now - values[0])))
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Demasiadas solicitudes. Intenta nuevamente mas tarde.",
                headers={"Retry-After": str(retry_after)},
            )
        values.append(now)
