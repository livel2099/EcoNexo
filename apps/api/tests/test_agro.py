"""Pruebas del motor agronomico de EcoNexo AG.

Las funciones de calculo son puras, asi que se verifican sin red ni base. Los
valores esperados salen de calcular a mano el mismo metodo, no de correr el
codigo y anotar lo que devolvio.
"""
from datetime import date, datetime, timedelta

import pytest

from app import agro


# --------------------------------------------------------------------------
# Grados dia
# --------------------------------------------------------------------------

def test_gdd_metodo_promedio_simple():
    # (30 + 15) / 2 - 10 = 12.5
    assert agro.growing_degree_days(30.0, 15.0, 10.0, 35.0) == pytest.approx(12.5)


def test_gdd_recorta_la_maxima_con_el_techo():
    # La maxima real de 40 se recorta a 30: (30 + 20) / 2 - 10 = 15
    assert agro.growing_degree_days(40.0, 20.0, 10.0, 30.0) == pytest.approx(15.0)


def test_gdd_eleva_la_minima_hasta_la_base():
    # La minima de 4 se eleva a 10: (25 + 10) / 2 - 10 = 7.5
    assert agro.growing_degree_days(25.0, 4.0, 10.0, 30.0) == pytest.approx(7.5)


def test_gdd_es_cero_cuando_no_supera_la_base():
    assert agro.growing_degree_days(8.0, 2.0, 10.0, 30.0) == 0.0


def test_gdd_nunca_es_negativo():
    assert agro.growing_degree_days(-5.0, -12.0, 10.0, 30.0) == 0.0


# --------------------------------------------------------------------------
# Bulbo humedo y delta-T
# --------------------------------------------------------------------------

def test_bulbo_humedo_con_saturacion_iguala_al_bulbo_seco():
    # Con humedad relativa casi total, el bulbo humedo tiende al seco.
    assert agro.wet_bulb_c(20.0, 99.0) == pytest.approx(20.0, abs=0.5)


def test_delta_t_crece_cuando_baja_la_humedad():
    humedo = agro.delta_t(25.0, 80.0)
    seco = agro.delta_t(25.0, 30.0)
    assert seco > humedo
    assert humedo >= 0


def test_delta_t_en_rango_conocido():
    # 25 C con 50 % de HR da un bulbo humedo cercano a 18 C: delta-T ~ 7 C.
    assert agro.delta_t(25.0, 50.0) == pytest.approx(7.0, abs=1.0)


# --------------------------------------------------------------------------
# Fenologia y coeficiente de cultivo
# --------------------------------------------------------------------------

def test_la_etapa_avanza_con_los_grados_dia():
    maiz = agro.CROPS["maiz"]
    assert maiz.stage_for(50).key == "emergencia"
    assert maiz.stage_for(400).key == "vegetativo"
    assert maiz.stage_for(900).key == "floracion"
    assert maiz.stage_for(1800).key == "cosecha"


def test_el_kc_sigue_a_la_etapa():
    maiz = agro.CROPS["maiz"]
    assert maiz.kc_for(50) == 0.30      # inicial
    assert maiz.kc_for(900) == 1.20     # pleno desarrollo
    assert maiz.kc_for(1800) == 0.35    # final


def test_los_perennes_no_tienen_etapa_y_usan_un_kc_fijo():
    yerba = agro.CROPS["yerba_mate"]
    assert yerba.perennial is True
    assert yerba.stage_for(5000) is None
    assert yerba.kc_for(5000) == yerba.perennial_kc


# --------------------------------------------------------------------------
# Serie diaria
# --------------------------------------------------------------------------

def _dias(cantidad, tmax=30.0, tmin=18.0, lluvia=0.0, et0=5.0):
    inicio = date(2026, 1, 1)
    return [
        {"day": inicio + timedelta(days=i), "tmax": tmax, "tmin": tmin,
         "precipitation_mm": lluvia, "et0_mm": et0}
        for i in range(cantidad)
    ]


def test_la_serie_acumula_grados_dia():
    maiz = agro.CROPS["maiz"]
    serie = agro.build_daily_series(maiz, _dias(3))
    # (30 + 18) / 2 - 10 = 14 por dia
    assert [p.gdd for p in serie] == [14.0, 14.0, 14.0]
    assert serie[-1].gdd_accum == pytest.approx(42.0)


def test_el_balance_hidrico_resta_la_demanda_del_cultivo():
    maiz = agro.CROPS["maiz"]
    # Con 42 GDD el cultivo esta en emergencia: Kc = 0.30, ETc = 5 * 0.30 = 1.5
    serie = agro.build_daily_series(maiz, _dias(3, lluvia=0.5, et0=5.0))
    assert serie[0].etc_mm == pytest.approx(1.5)
    assert serie[0].balance_mm == pytest.approx(-1.0)
    assert serie[-1].balance_accum_mm == pytest.approx(-3.0)


def test_los_dias_incompletos_se_saltean_en_vez_de_inventarse():
    maiz = agro.CROPS["maiz"]
    crudos = _dias(3)
    crudos[1]["tmax"] = None
    serie = agro.build_daily_series(maiz, crudos)
    assert len(serie) == 2


def test_la_serie_puede_continuar_una_acumulacion_previa():
    maiz = agro.CROPS["maiz"]
    serie = agro.build_daily_series(maiz, _dias(1), gdd_inicial=700.0)
    assert serie[0].gdd_accum == pytest.approx(714.0)
    assert serie[0].stage_key == "floracion"


# --------------------------------------------------------------------------
# Ventanas de pulverizacion
# --------------------------------------------------------------------------

def _horas(specs):
    inicio = datetime(2026, 1, 1, 6, 0)
    return [
        {"ts": inicio + timedelta(hours=i), "temperature": t, "humidity": hr,
         "wind": viento, "gust": rafaga, "precipitation": lluvia}
        for i, (t, hr, viento, rafaga, lluvia) in enumerate(specs)
    ]


def test_detecta_una_ventana_de_pulverizacion():
    # 22 C con 60 % de HR da delta-T cercano a 5 C, dentro del rango util.
    horas = _horas([(22.0, 60.0, 8.0, 15.0, 0.0)] * 4)
    ventanas = agro.spray_windows(horas)
    assert len(ventanas) == 1
    assert ventanas[0].hours == 4
    assert 2.0 <= ventanas[0].delta_t_min <= 8.0


def test_el_viento_fuerte_descarta_la_hora():
    horas = _horas([(22.0, 60.0, 25.0, 40.0, 0.0)] * 4)
    assert agro.spray_windows(horas) == []


def test_la_calma_total_descarta_la_hora_por_riesgo_de_inversion():
    horas = _horas([(22.0, 60.0, 0.5, 2.0, 0.0)] * 4)
    assert agro.spray_windows(horas) == []


def test_la_lluvia_interrumpe_la_ventana():
    horas = _horas([
        (22.0, 60.0, 8.0, 15.0, 0.0),
        (22.0, 60.0, 8.0, 15.0, 0.0),
        (22.0, 60.0, 8.0, 15.0, 1.2),   # llueve
        (22.0, 60.0, 8.0, 15.0, 0.0),
        (22.0, 60.0, 8.0, 15.0, 0.0),
    ])
    ventanas = agro.spray_windows(horas)
    assert len(ventanas) == 2
    assert [v.hours for v in ventanas] == [2, 2]


def test_una_hora_suelta_no_cuenta_como_ventana():
    horas = _horas([
        (22.0, 60.0, 8.0, 15.0, 0.0),
        (22.0, 60.0, 30.0, 45.0, 0.0),
    ])
    assert agro.spray_windows(horas) == []


# --------------------------------------------------------------------------
# Presion de enfermedad
# --------------------------------------------------------------------------

def test_la_racha_humeda_prolongada_da_riesgo_alto():
    soja = agro.CROPS["soja"]  # umbral: 8 h con HR >= 85 % y 18-26 C
    horas = _horas([(22.0, 92.0, 5.0, 10.0, 0.0)] * 10)
    resultado = agro.disease_pressure(soja, horas)
    assert resultado["nivel"] == "alto"
    assert resultado["racha_horas"] == 10


def test_el_aire_seco_no_genera_presion():
    soja = agro.CROPS["soja"]
    horas = _horas([(22.0, 40.0, 5.0, 10.0, 0.0)] * 12)
    assert agro.disease_pressure(soja, horas)["nivel"] == "bajo"


def test_la_racha_se_corta_con_una_hora_desfavorable():
    soja = agro.CROPS["soja"]
    horas = _horas(
        [(22.0, 92.0, 5.0, 10.0, 0.0)] * 5
        + [(22.0, 40.0, 5.0, 10.0, 0.0)]
        + [(22.0, 92.0, 5.0, 10.0, 0.0)] * 4
    )
    resultado = agro.disease_pressure(soja, horas)
    assert resultado["racha_horas"] == 5
    assert resultado["horas_favorables"] == 9
    assert resultado["nivel"] == "medio"


def test_la_temperatura_fuera_del_rango_no_favorece_al_patogeno():
    soja = agro.CROPS["soja"]  # rango favorable 18-26 C
    horas = _horas([(35.0, 95.0, 5.0, 10.0, 0.0)] * 12)
    assert agro.disease_pressure(soja, horas)["nivel"] == "bajo"


# --------------------------------------------------------------------------
# Helada, calor y riego
# --------------------------------------------------------------------------

def test_la_helada_avisa_con_margen_sobre_el_umbral():
    maiz = agro.CROPS["maiz"]  # umbral 2 C
    diario = [
        {"day": date(2026, 6, 1), "tmax": 14.0, "tmin": 1.0},   # cruza: alto
        {"day": date(2026, 6, 2), "tmax": 16.0, "tmin": 4.0},   # se acerca: medio
        {"day": date(2026, 6, 3), "tmax": 20.0, "tmin": 12.0},  # sin riesgo
    ]
    resultado = agro.frost_outlook(maiz, diario)
    assert resultado["nivel"] == "alto"
    assert [e["nivel"] for e in resultado["eventos"]] == ["alto", "medio"]


def test_el_estres_termico_cuenta_los_dias_sobre_el_umbral():
    soja = agro.CROPS["soja"]  # umbral 34 C
    diario = [
        {"day": date(2026, 1, 1), "tmax": 36.0},
        {"day": date(2026, 1, 2), "tmax": 35.0},
        {"day": date(2026, 1, 3), "tmax": 28.0},
    ]
    resultado = agro.heat_outlook(soja, diario)
    assert len(resultado["eventos"]) == 2
    assert resultado["nivel"] == "alto"


def test_el_deficit_hidrico_sostenido_pide_riego():
    maiz = agro.CROPS["maiz"]
    serie = agro.build_daily_series(maiz, _dias(20, lluvia=0.0, et0=6.0), gdd_inicial=800.0)
    resultado = agro.irrigation_outlook(serie, dias=14)
    assert resultado["dias"] == 14
    assert resultado["balance_mm"] < -60
    assert resultado["nivel"] == "alto"


def test_la_lluvia_abundante_no_dispara_riego():
    maiz = agro.CROPS["maiz"]
    serie = agro.build_daily_series(maiz, _dias(20, lluvia=12.0, et0=5.0), gdd_inicial=800.0)
    assert agro.irrigation_outlook(serie)["nivel"] == "bajo"


def test_sin_serie_no_se_inventa_un_diagnostico():
    assert agro.irrigation_outlook([])["nivel"] == "sin datos"


# --------------------------------------------------------------------------
# Catalogo
# --------------------------------------------------------------------------

def test_el_catalogo_expone_los_parametros_de_cada_cultivo():
    catalogo = {c["key"]: c for c in agro.catalog()}
    assert "yerba_mate" in catalogo
    assert "soja" in catalogo
    maiz = catalogo["maiz"]
    assert maiz["t_base_c"] == 10.0
    assert maiz["disease"]["hr_min"] == 85.0
    assert len(maiz["stages"]) == 6


def test_un_cultivo_desconocido_es_error_de_contrato():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        agro.crop_or_404("quinoa_marciana")
    assert exc.value.status_code == 422


# --------------------------------------------------------------------------
# Licenciamiento
# --------------------------------------------------------------------------

def test_todos_los_planes_incluyen_el_modulo_agro():
    """EcoNexo AG es transversal: no hay plan que lo deje afuera.

    Si alguien agrega un plan nuevo y se olvida del modulo, esta prueba lo
    detecta antes de que un cliente se encuentre con un 402.
    """
    from app.subscriptions import PLAN_DEFINITIONS

    sin_agro = [
        clave for clave, plan in PLAN_DEFINITIONS.items()
        if "agro" not in plan["entitlements"]["included_modules"]
    ]
    assert sin_agro == [], f"planes sin el modulo agro: {sin_agro}"


def test_ningun_plan_racionaria_informes():
    """El tope mensual de informes se elimino: ningun plan debe reintroducirlo."""
    from app.subscriptions import PLAN_DEFINITIONS

    con_tope = [
        clave for clave, plan in PLAN_DEFINITIONS.items()
        if "max_reports_per_month" in plan["entitlements"]
    ]
    assert con_tope == [], f"planes con tope de informes: {con_tope}"


# --------------------------------------------------------------------------
# Consulta a Open-Meteo: reintentos y errores explicitos
# --------------------------------------------------------------------------

class _RespuestaFalsa:
    def __init__(self, status_code, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        # httpx siempre expone headers; el doble tambien, para que un cambio
        # que los lea no falle por el doble en vez de por el codigo.
        self.headers = headers or {}

    def json(self):
        return self._payload


class _ClienteFalso:
    """Reemplaza httpx.AsyncClient devolviendo una secuencia fija."""

    def __init__(self, respuestas, registro):
        self._respuestas = list(respuestas)
        self._registro = registro

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        self._registro.append((url, dict(params or {})))
        siguiente = self._respuestas.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


@pytest.fixture
def sin_esperas(monkeypatch):
    """Anula la espera entre reintentos para que la prueba no tarde."""
    async def _dormir(_segundos):
        return None

    monkeypatch.setattr(agro.asyncio, "sleep", _dormir)


def _montar(monkeypatch, respuestas):
    registro = []
    monkeypatch.setattr(agro.httpx, "AsyncClient", _ClienteFalso(respuestas, registro))
    return registro


@pytest.mark.asyncio
async def test_reintenta_ante_un_limite_de_consultas(monkeypatch, sin_esperas):
    registro = _montar(monkeypatch, [
        _RespuestaFalsa(429),
        _RespuestaFalsa(429),
        _RespuestaFalsa(200, {"daily": {"time": []}}),
    ])
    resultado = await agro._consultar("https://x/y", {}, "histórico")
    assert resultado == {"daily": {"time": []}}
    assert len(registro) == 3


@pytest.mark.asyncio
async def test_agota_los_reintentos_y_explica_el_limite(monkeypatch, sin_esperas):
    _montar(monkeypatch, [_RespuestaFalsa(429)] * 3)
    with pytest.raises(agro.OpenMeteoError) as exc:
        await agro._consultar("https://x/y", {}, "histórico")
    mensaje = str(exc.value)
    assert "429" in mensaje
    assert "límite de consultas" in mensaje
    assert "histórico" in mensaje


@pytest.mark.asyncio
async def test_un_error_del_pedido_no_se_reintenta(monkeypatch, sin_esperas):
    # Un 400 no mejora reintentando: reintentar solo demora el diagnostico.
    registro = _montar(monkeypatch, [_RespuestaFalsa(400, text="Bad Request")])
    with pytest.raises(agro.OpenMeteoError) as exc:
        await agro._consultar("https://x/y", {}, "pronóstico")
    assert "rechazó la consulta" in str(exc.value)
    assert len(registro) == 1


@pytest.mark.asyncio
async def test_el_timeout_dice_cuanto_espero(monkeypatch, sin_esperas):
    import httpx

    _montar(monkeypatch, [httpx.TimeoutException("timeout")] * 3)
    with pytest.raises(agro.OpenMeteoError) as exc:
        await agro._consultar("https://x/y", {}, "histórico")
    assert "no respondió" in str(exc.value)


@pytest.mark.asyncio
async def test_un_5xx_transitorio_se_supera_reintentando(monkeypatch, sin_esperas):
    registro = _montar(monkeypatch, [
        _RespuestaFalsa(503),
        _RespuestaFalsa(200, {"hourly": {"time": []}}),
    ])
    assert await agro._consultar("https://x/y", {}, "pronóstico") == {"hourly": {"time": []}}
    assert len(registro) == 2


# --------------------------------------------------------------------------
# Zona horaria y solapamiento historico/pronostico
# --------------------------------------------------------------------------

def test_la_fecha_es_la_del_territorio_no_la_del_servidor():
    """Entre las 21 y las 24 de Argentina, UTC ya esta en el dia siguiente.

    Si se usara la fecha del servidor, el historico se pediria hasta el dia que
    el pronostico da por primero y la serie repetiria ese dia.
    """
    from datetime import datetime, timezone as tz

    hoy = agro.today_local()
    ahora_utc = datetime.now(tz.utc)
    assert hoy in {ahora_utc.date(), (ahora_utc - timedelta(days=1)).date()}
    # Argentina esta detras de UTC: nunca puede ir un dia adelante.
    assert hoy <= ahora_utc.date()


def test_un_dia_repetido_no_entra_dos_veces_en_la_serie():
    maiz = agro.CROPS["maiz"]
    dia = {"day": date(2026, 8, 21), "tmax": 30.0, "tmin": 18.0,
           "precipitation_mm": 0.0, "et0_mm": 5.0}
    serie = agro.build_daily_series(maiz, [dia, dict(dia)])
    assert len(serie) == 1


def test_ante_un_dia_solapado_gana_el_dato_observado():
    """El historico se pasa primero, asi que su valor es el que queda."""
    maiz = agro.CROPS["maiz"]
    observado = {"day": date(2026, 8, 21), "tmax": 30.0, "tmin": 18.0,
                 "precipitation_mm": 12.0, "et0_mm": 5.0}
    pronosticado = {"day": date(2026, 8, 21), "tmax": 25.0, "tmin": 15.0,
                    "precipitation_mm": 0.0, "et0_mm": 3.0}
    serie = agro.build_daily_series(maiz, [observado, pronosticado])
    assert len(serie) == 1
    assert serie[0].tmax == 30.0
    assert serie[0].precipitation_mm == 12.0


@pytest.mark.asyncio
async def test_la_clave_comercial_viaja_en_cada_consulta(monkeypatch, sin_esperas):
    """Con clave propia el cupo deja de depender de la IP compartida del hosting."""
    from app.config import get_settings

    monkeypatch.setenv("OPEN_METEO_API_KEY", "clave-de-prueba")
    get_settings.cache_clear()
    try:
        registro = _montar(monkeypatch, [_RespuestaFalsa(200, {"daily": {"time": []}})])
        await agro._consultar("https://x/y", {"latitude": "-27.4"}, "pronóstico")
        _, params = registro[0]
        assert params["apikey"] == "clave-de-prueba"
        assert params["latitude"] == "-27.4"
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_sin_clave_no_se_agrega_el_parametro(monkeypatch, sin_esperas):
    registro = _montar(monkeypatch, [_RespuestaFalsa(200, {"daily": {"time": []}})])
    await agro._consultar("https://x/y", {"latitude": "-27.4"}, "pronóstico")
    _, params = registro[0]
    assert "apikey" not in params


@pytest.mark.asyncio
async def test_respeta_el_retry_after_del_servidor(monkeypatch):
    """La espera lineal previa era mas corta que cualquier ventana real."""
    esperas = []

    async def _dormir(segundos):
        esperas.append(segundos)

    monkeypatch.setattr(agro.asyncio, "sleep", _dormir)
    _montar(monkeypatch, [
        _RespuestaFalsa(429, headers={"retry-after": "12"}),
        _RespuestaFalsa(200, {"daily": {"time": []}}),
    ])
    await agro._consultar("https://x/y", {}, "histórico")
    assert esperas == [12.0]


@pytest.mark.asyncio
async def test_un_retry_after_desmedido_se_recorta(monkeypatch):
    """Bloquear el request media hora es peor que reportar el limite."""
    esperas = []

    async def _dormir(segundos):
        esperas.append(segundos)

    monkeypatch.setattr(agro.asyncio, "sleep", _dormir)
    _montar(monkeypatch, [
        _RespuestaFalsa(429, headers={"retry-after": "3600"}),
        _RespuestaFalsa(200, {"daily": {"time": []}}),
    ])
    await agro._consultar("https://x/y", {}, "histórico")
    assert esperas == [30.0]


@pytest.mark.asyncio
async def test_sin_retry_after_la_espera_crece_geometricamente(monkeypatch):
    esperas = []

    async def _dormir(segundos):
        esperas.append(segundos)

    monkeypatch.setattr(agro.asyncio, "sleep", _dormir)
    _montar(monkeypatch, [_RespuestaFalsa(429)] * 3)
    with pytest.raises(agro.OpenMeteoError):
        await agro._consultar("https://x/y", {}, "histórico")
    # Antes eran 1.5 y 3.0 segundos: 4.5 en total para un cupo por IP.
    assert esperas == [1.5, 4.5]


@pytest.mark.asyncio
async def test_el_mensaje_sugiere_la_clave_solo_si_falta(monkeypatch, sin_esperas):
    _montar(monkeypatch, [_RespuestaFalsa(429)] * 3)
    with pytest.raises(agro.OpenMeteoError) as exc:
        await agro._consultar("https://x/y", {}, "histórico")
    assert "OPEN_METEO_API_KEY" in str(exc.value)
