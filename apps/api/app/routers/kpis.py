"""KPIs del producto en vivo (los 4 del plan)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import db
from ..deps import CurrentUser, current_user
from ..metrics import ratio, response_time_reduction
from ..schemas import KpiOut

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("", response_model=KpiOut)
async def kpis(user: CurrentUser = Depends(current_user)) -> KpiOut:
    p = db.pool()
    org = await p.fetchrow(
        "SELECT baseline_response_s FROM organizations WHERE id=$1", user.org_id
    )
    baseline = org["baseline_response_s"]

    # KPI1 — tiempo de deteccion: latencia desde la ultima lectura del nodo
    # hasta la creacion de la alerta (segundos).
    det = await p.fetchval(
        """
        SELECT percentile_cont(0.5) WITHIN GROUP (
                 ORDER BY EXTRACT(EPOCH FROM (a.detected_at - r.ts)))
        FROM alerts a
        JOIN LATERAL (
            SELECT ts FROM readings
            WHERE device_id = a.device_id AND ts <= a.detected_at
            ORDER BY ts DESC LIMIT 1
        ) r ON true
        WHERE a.org_id=$1 AND a.device_id IS NOT NULL
          AND a.detected_at > now() - interval '7 days'
        """,
        user.org_id,
    )

    # KPI2 — precision del motor: confirmadas / (confirmadas + descartadas)
    prec = await p.fetchrow(
        """
        SELECT
          count(*) FILTER (WHERE status='confirmada') AS ok,
          count(*) FILTER (WHERE status IN ('confirmada','descartada')) AS total
        FROM alerts WHERE org_id=$1
        """,
        user.org_id,
    )
    precision = ratio(prec["ok"], prec["total"])

    # KPI3 — reportes ciudadanos validos y accionables
    rep = await p.fetchrow(
        """
        SELECT
          count(*) FILTER (WHERE status='verificado') AS ok,
          count(*) FILTER (WHERE status IN ('verificado','rechazado')) AS total
        FROM citizen_reports WHERE org_id=$1
        """,
        user.org_id,
    )
    valid_rate = ratio(rep["ok"], rep["total"])

    # KPI4 — reduccion del tiempo de respuesta institucional vs baseline
    # Mediana, no promedio: la tarjeta describe el comportamiento tipico y no
    # puede quedar definida por el caso extremo de una alerta olvidada.
    resp = await p.fetchval(
        """
        SELECT percentile_cont(0.5) WITHIN GROUP (
                 ORDER BY EXTRACT(EPOCH FROM (acknowledged_at - detected_at)))
        FROM alerts WHERE org_id=$1 AND acknowledged_at IS NOT NULL
          AND detected_at > now() - interval '30 days'
        """,
        user.org_id,
    )
    reduction = response_time_reduction(
        float(resp) if resp is not None else None, baseline)

    # Banner de estado global
    active = await p.fetchrow(
        """
        SELECT
          count(*) FILTER (WHERE status IN ('nueva','escalada','asignada')) AS active,
          count(*) FILTER (WHERE status IN ('nueva','escalada') AND severity='critica') AS crit,
          count(*) FILTER (WHERE status IN ('nueva','escalada') AND severity IN ('alta','media')) AS att
        FROM alerts WHERE org_id=$1
        """,
        user.org_id,
    )
    if active["crit"]:
        gstatus = "critico"
    elif active["att"]:
        gstatus = "atencion"
    else:
        gstatus = "normal"

    return KpiOut(
        detection_time_s=round(float(det), 1) if det is not None else None,
        model_precision=precision,
        valid_reports_rate=valid_rate,
        response_time_reduction=reduction,
        global_status=gstatus,
        active_alerts=active["active"],
    )
