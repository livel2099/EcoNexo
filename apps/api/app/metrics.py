"""Aritmetica de los KPI del producto.

Funciones puras, sin base ni red, para que el calculo sea verificable y no se
duplique entre la tarjeta del tablero y los informes institucionales.
"""
from __future__ import annotations

# Piso de la reduccion de tiempo de respuesta.
#
# La formula es 1 - respuesta / baseline, que no tiene cota inferior: con un
# baseline de 3600 s, una sola alerta reconocida once dias despues de haberse
# detectado da -264, y la tarjeta muestra "-26431%". Un numero asi no informa
# nada, solo parece roto.
#
# -1.0 equivale a "la respuesta tardo el doble del baseline". Cualquier
# demora peor ya esta dicha con eso: lo que importa es que se incumplio, no
# por cuantos ordenes de magnitud.
REDUCCION_MINIMA = -1.0


def response_time_reduction(respuesta_s: float | None,
                            baseline_s: float | int | None) -> float | None:
    """Reduccion del tiempo de respuesta frente al baseline, acotada por abajo.

    Devuelve ``None`` cuando no hay dato suficiente para afirmar nada: sin
    respuestas registradas o sin baseline valido. Un ``None`` explicito es
    preferible a un cero, que se leeria como "no hubo mejora".
    """
    if respuesta_s is None or not baseline_s or baseline_s <= 0:
        return None
    return round(max(REDUCCION_MINIMA, 1 - respuesta_s / baseline_s), 3)


def ratio(parte: int | None, total: int | None) -> float | None:
    """Proporcion parte/total, o ``None`` si no hay universo que medir."""
    if not total:
        return None
    return round((parte or 0) / total, 3)
