"""Pruebas de la aritmetica de KPI.

El caso que las motiva es real: la tarjeta del tablero llego a mostrar
"-26431%" de reduccion del tiempo de respuesta.
"""
import pytest

from app.metrics import ratio, response_time_reduction


def test_responder_mas_rapido_que_el_baseline_da_reduccion_positiva():
    # 1800 s contra un baseline de 3600 s: la mitad del tiempo.
    assert response_time_reduction(1800, 3600) == pytest.approx(0.5)


def test_responder_igual_que_el_baseline_no_es_mejora():
    assert response_time_reduction(3600, 3600) == 0.0


def test_responder_mas_lento_da_reduccion_negativa():
    # 5400 s contra 3600: 50 % peor.
    assert response_time_reduction(5400, 3600) == pytest.approx(-0.5)


def test_el_doble_del_baseline_es_el_piso():
    assert response_time_reduction(7200, 3600) == -1.0


def test_una_demora_absurda_no_devuelve_un_numero_absurdo():
    """El caso que se vio en produccion: once dias contra un baseline de una hora."""
    once_dias = 11 * 24 * 3600
    assert response_time_reduction(once_dias, 3600) == -1.0


def test_sin_respuestas_registradas_no_se_afirma_nada():
    # None y no 0: un cero se leeria como "no hubo mejora".
    assert response_time_reduction(None, 3600) is None


def test_un_baseline_invalido_no_produce_division():
    assert response_time_reduction(1800, 0) is None
    assert response_time_reduction(1800, None) is None
    assert response_time_reduction(1800, -60) is None


def test_una_respuesta_instantanea_es_reduccion_total():
    assert response_time_reduction(0, 3600) == 1.0


def test_la_proporcion_sin_universo_es_desconocida():
    assert ratio(0, 0) is None
    assert ratio(None, None) is None


def test_la_proporcion_distingue_cero_de_desconocido():
    # Cero confirmadas sobre cinco moderadas es un dato, no una ausencia.
    assert ratio(0, 5) == 0.0
    assert ratio(3, 4) == 0.75
