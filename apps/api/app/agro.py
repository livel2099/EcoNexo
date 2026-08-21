"""EcoNexo AG: motor agronomico sobre datos meteorologicos reales.

Todo lo que este modulo calcula sale de mediciones y reanalisis de Open-Meteo,
no de datos sinteticos:

  * historico diario -> ``archive-api.open-meteo.com`` (reanalisis ERA5).
  * pronostico horario y diario -> ``api.open-meteo.com``.

La ET0 no se estima aca: Open-Meteo la publica ya calculada por FAO-56
Penman-Monteith, que es el metodo de referencia. Lo que agrega EcoNexo es la
capa agronomica: grados dia, fenologia, coeficiente de cultivo, balance
hidrico, ventanas de pulverizacion y presion de enfermedad.

Los coeficientes del catalogo son valores de literatura (FAO-56 para Kc,
temperaturas base de uso corriente). Son un punto de partida parametrizable,
no una calibracion local: un agronomo deberia ajustarlos por zona, cultivar y
manejo antes de tomar decisiones productivas.

Las funciones de calculo son puras y no tocan la red ni la base, para que
puedan probarse sin infraestructura.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Sequence

import httpx

from .config import get_settings

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "America/Argentina/Buenos_Aires"

DAILY_VARIABLES = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "et0_fao_evapotranspiration",
)
HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_gusts_10m",
    "soil_moisture_0_to_7cm",
)


# --------------------------------------------------------------------------
# Catalogo de cultivos
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Stage:
    """Etapa fenologica delimitada por grados dia acumulados."""

    key: str
    name: str
    gdd_from: float
    gdd_to: float | None  # None = etapa final, abierta
    kc: float             # coeficiente de cultivo FAO-56 para la etapa


@dataclass(frozen=True)
class Crop:
    key: str
    name: str
    perennial: bool
    t_base: float          # temperatura base para grados dia (C)
    t_cap: float           # techo termico: por encima no acumula mas (C)
    frost_c: float         # umbral de dano por frio (C, temperatura del aire a 2 m)
    heat_c: float          # umbral de estres termico (C)
    stages: tuple[Stage, ...]
    perennial_kc: float    # Kc unico para perennes, que no tienen ciclo desde siembra
    disease_name: str      # enfermedad de referencia para la presion fungica
    disease_t_min: float   # rango termico favorable al patogeno (C)
    disease_t_max: float
    disease_rh: float      # humedad relativa minima que se considera hoja mojada (%)
    disease_hours: int     # horas consecutivas favorables que disparan riesgo alto

    def stage_for(self, gdd_accum: float) -> Stage | None:
        """Etapa correspondiente a los grados dia acumulados."""
        if self.perennial or not self.stages:
            return None
        for stage in self.stages:
            if stage.gdd_to is None:
                if gdd_accum >= stage.gdd_from:
                    return stage
            elif stage.gdd_from <= gdd_accum < stage.gdd_to:
                return stage
        return self.stages[-1]

    def kc_for(self, gdd_accum: float) -> float:
        if self.perennial:
            return self.perennial_kc
        stage = self.stage_for(gdd_accum)
        return stage.kc if stage else self.perennial_kc


def _anual(nombre: str, key: str, t_base: float, kc_ini: float, kc_med: float,
           kc_fin: float, gdd_emergencia: float, gdd_vegetativo: float,
           gdd_floracion: float, gdd_llenado: float, gdd_madurez: float,
           frost_c: float, heat_c: float, disease_name: str,
           disease_t: tuple[float, float], disease_rh: float,
           disease_hours: int, t_cap: float = 30.0) -> Crop:
    """Arma un cultivo anual con las cinco etapas que usa FAO-56."""
    return Crop(
        key=key, name=nombre, perennial=False, t_base=t_base, t_cap=t_cap,
        frost_c=frost_c, heat_c=heat_c, perennial_kc=kc_med,
        stages=(
            Stage("emergencia", "Emergencia", 0.0, gdd_emergencia, kc_ini),
            Stage("vegetativo", "Desarrollo vegetativo", gdd_emergencia, gdd_vegetativo,
                  round((kc_ini + kc_med) / 2, 2)),
            Stage("floracion", "Floración", gdd_vegetativo, gdd_floracion, kc_med),
            Stage("llenado", "Llenado de grano", gdd_floracion, gdd_llenado, kc_med),
            Stage("madurez", "Madurez", gdd_llenado, gdd_madurez, kc_fin),
            Stage("cosecha", "Listo para cosecha", gdd_madurez, None, kc_fin),
        ),
        disease_name=disease_name,
        disease_t_min=disease_t[0], disease_t_max=disease_t[1],
        disease_rh=disease_rh, disease_hours=disease_hours,
    )


def _perenne(nombre: str, key: str, t_base: float, kc: float, frost_c: float,
             heat_c: float, disease_name: str, disease_t: tuple[float, float],
             disease_rh: float, disease_hours: int) -> Crop:
    return Crop(
        key=key, name=nombre, perennial=True, t_base=t_base, t_cap=32.0,
        frost_c=frost_c, heat_c=heat_c, stages=(), perennial_kc=kc,
        disease_name=disease_name,
        disease_t_min=disease_t[0], disease_t_max=disease_t[1],
        disease_rh=disease_rh, disease_hours=disease_hours,
    )


# Cultivos de Misiones y de la region. Kc segun FAO-56 (Allen et al., 1998);
# temperaturas base de uso corriente en la bibliografia agronomica regional.
CROPS: dict[str, Crop] = {
    crop.key: crop for crop in (
        _perenne("Yerba mate", "yerba_mate", 8.0, 0.90, 0.0, 35.0,
                 "Rulo de la yerba (Gyropsylla spegazziniana)", (18.0, 28.0), 80.0, 8),
        _perenne("Té", "te", 10.0, 1.00, 1.0, 35.0,
                 "Ampolla de la hoja (Exobasidium vexans)", (16.0, 25.0), 85.0, 10),
        _perenne("Citrus", "citrus", 12.5, 0.65, -1.0, 38.0,
                 "Cancrosis (Xanthomonas citri)", (20.0, 30.0), 85.0, 8),
        _anual("Maíz", "maiz", 10.0, 0.30, 1.20, 0.35,
               120, 700, 1100, 1500, 1700, 2.0, 35.0,
               "Tizón común (Exserohilum turcicum)", (18.0, 27.0), 85.0, 8),
        _anual("Soja", "soja", 10.0, 0.40, 1.15, 0.50,
               110, 600, 950, 1350, 1600, 2.0, 34.0,
               "Roya asiática (Phakopsora pachyrhizi)", (18.0, 26.0), 85.0, 8),
        _anual("Tabaco", "tabaco", 10.0, 0.35, 1.10, 0.80,
               130, 620, 900, 1200, 1450, 3.0, 34.0,
               "Moho azul (Peronospora tabacina)", (15.0, 23.0), 85.0, 10),
        _anual("Mandioca", "mandioca", 13.0, 0.30, 1.10, 0.50,
               160, 900, 1600, 2400, 3000, 3.0, 38.0,
               "Bacteriosis (Xanthomonas axonopodis)", (22.0, 30.0), 85.0, 10),
    )
}


# --------------------------------------------------------------------------
# Calculos agronomicos (funciones puras)
# --------------------------------------------------------------------------

def growing_degree_days(tmax: float, tmin: float, t_base: float,
                        t_cap: float) -> float:
    """Grados dia por el metodo de promedio simple con techo termico.

    GDD = max(0, (min(Tmax, techo) + max(Tmin, base)) / 2 - base)

    El recorte de Tmax por el techo y el de Tmin por la base es la correccion
    habitual para que dias muy calidos o muy frios no distorsionen la suma.
    """
    tmax_ajustada = min(tmax, t_cap)
    tmin_ajustada = max(tmin, t_base)
    if tmax_ajustada < t_base:
        return 0.0
    return max(0.0, (tmax_ajustada + tmin_ajustada) / 2 - t_base)


def wet_bulb_c(temp_c: float, rh: float) -> float:
    """Temperatura de bulbo humedo por la aproximacion de Stull (2011).

    Valida para presion cercana al nivel del mar, temperaturas de -20 a 50 C y
    humedad relativa de 5 a 99 %, que cubre de sobra las condiciones de
    pulverizacion en Misiones.
    """
    rh = min(max(rh, 5.0), 99.0)
    return (
        temp_c * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(temp_c + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )


def delta_t(temp_c: float, rh: float) -> float:
    """Delta-T: diferencia entre bulbo seco y bulbo humedo.

    Es el indicador estandar de aptitud para pulverizar. Por debajo de 2 C la
    gota casi no evapora y hay riesgo de deriva por inversion termica; por
    encima de 8 C la gota se evapora antes de llegar al objetivo.
    """
    return temp_c - wet_bulb_c(temp_c, rh)


@dataclass
class DailyPoint:
    """Un dia de serie agronomica ya procesado."""

    day: date
    tmax: float
    tmin: float
    precipitation_mm: float
    et0_mm: float
    gdd: float
    gdd_accum: float
    kc: float
    etc_mm: float
    balance_mm: float        # precipitacion - ETc del dia
    balance_accum_mm: float  # acumulado del periodo
    stage_key: str | None
    stage_name: str | None


def build_daily_series(crop: Crop, days: Sequence[dict[str, Any]],
                       gdd_inicial: float = 0.0) -> list[DailyPoint]:
    """Procesa la serie diaria cruda de Open-Meteo a indicadores agronomicos.

    ``days`` son diccionarios con ``day``, ``tmax``, ``tmin``,
    ``precipitation_mm`` y ``et0_mm``. Los dias sin datos completos se saltean
    en vez de rellenarse: preferimos una serie con huecos declarados antes que
    una serie inventada.
    """
    salida: list[DailyPoint] = []
    gdd_accum = gdd_inicial
    balance_accum = 0.0
    for crudo in days:
        tmax = crudo.get("tmax")
        tmin = crudo.get("tmin")
        if tmax is None or tmin is None:
            continue
        et0 = crudo.get("et0_mm")
        lluvia = crudo.get("precipitation_mm") or 0.0
        gdd = growing_degree_days(float(tmax), float(tmin), crop.t_base, crop.t_cap)
        gdd_accum += gdd
        kc = crop.kc_for(gdd_accum)
        etc = round(float(et0) * kc, 3) if et0 is not None else 0.0
        balance = round(float(lluvia) - etc, 3)
        balance_accum = round(balance_accum + balance, 3)
        etapa = crop.stage_for(gdd_accum)
        salida.append(DailyPoint(
            day=crudo["day"],
            tmax=round(float(tmax), 2),
            tmin=round(float(tmin), 2),
            precipitation_mm=round(float(lluvia), 2),
            et0_mm=round(float(et0), 3) if et0 is not None else 0.0,
            gdd=round(gdd, 2),
            gdd_accum=round(gdd_accum, 2),
            kc=kc,
            etc_mm=etc,
            balance_mm=balance,
            balance_accum_mm=balance_accum,
            stage_key=etapa.key if etapa else None,
            stage_name=etapa.name if etapa else None,
        ))
    return salida


@dataclass
class SprayWindow:
    """Tramo horario apto para pulverizar."""

    start: datetime
    end: datetime
    hours: int
    delta_t_min: float
    delta_t_max: float
    wind_min: float
    wind_max: float


def spray_windows(hourly: Sequence[dict[str, Any]]) -> list[SprayWindow]:
    """Ventanas de pulverizacion segun condiciones horarias reales.

    Una hora es apta cuando se cumplen a la vez:

      * viento entre 3 y 15 km/h: menos es riesgo de inversion termica, mas es
        deriva;
      * rafagas por debajo de 20 km/h;
      * sin precipitacion en la hora;
      * delta-T entre 2 y 8 C;
      * temperatura entre 5 y 30 C.

    Son los criterios de uso extendido en pulverizacion terrestre. No
    reemplazan la etiqueta del producto ni la decision del aplicador.
    """
    aptas: list[dict[str, Any]] = []
    for hora in hourly:
        temp = hora.get("temperature")
        rh = hora.get("humidity")
        viento = hora.get("wind")
        rafaga = hora.get("gust")
        lluvia = hora.get("precipitation") or 0.0
        if temp is None or rh is None or viento is None:
            continue
        dt = delta_t(float(temp), float(rh))
        apta = (
            3.0 <= float(viento) <= 15.0
            and (rafaga is None or float(rafaga) < 20.0)
            and float(lluvia) <= 0.0
            and 2.0 <= dt <= 8.0
            and 5.0 <= float(temp) <= 30.0
        )
        aptas.append({"ts": hora["ts"], "apta": apta, "delta_t": dt, "wind": float(viento)})

    ventanas: list[SprayWindow] = []
    tramo: list[dict[str, Any]] = []

    def cerrar() -> None:
        if len(tramo) < 2:  # una hora suelta no es una ventana operable
            return
        deltas = [t["delta_t"] for t in tramo]
        vientos = [t["wind"] for t in tramo]
        ventanas.append(SprayWindow(
            start=tramo[0]["ts"],
            end=tramo[-1]["ts"] + timedelta(hours=1),
            hours=len(tramo),
            delta_t_min=round(min(deltas), 2),
            delta_t_max=round(max(deltas), 2),
            wind_min=round(min(vientos), 1),
            wind_max=round(max(vientos), 1),
        ))

    for hora in aptas:
        if hora["apta"]:
            tramo.append(hora)
        else:
            cerrar()
            tramo = []
    cerrar()
    return ventanas


def disease_pressure(crop: Crop, hourly: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Presion de enfermedad por horas de mojado foliar favorables.

    Se cuenta la racha mas larga de horas consecutivas con humedad relativa por
    encima del umbral del cultivo y temperatura dentro del rango favorable al
    patogeno. Es el esquema clasico de los modelos tipo Mills: la humedad
    relativa alta se usa como sustituto del mojado foliar, que no se mide.
    """
    racha = 0
    mejor = 0
    horas_favorables = 0
    for hora in hourly:
        temp = hora.get("temperature")
        rh = hora.get("humidity")
        if temp is None or rh is None:
            racha = 0
            continue
        favorable = (
            float(rh) >= crop.disease_rh
            and crop.disease_t_min <= float(temp) <= crop.disease_t_max
        )
        if favorable:
            racha += 1
            horas_favorables += 1
            mejor = max(mejor, racha)
        else:
            racha = 0

    if mejor >= crop.disease_hours:
        nivel = "alto"
    elif mejor >= max(2, crop.disease_hours // 2):
        nivel = "medio"
    else:
        nivel = "bajo"
    return {
        "nivel": nivel,
        "enfermedad": crop.disease_name,
        "racha_horas": mejor,
        "horas_favorables": horas_favorables,
        "umbral_horas": crop.disease_hours,
        "umbral_hr": crop.disease_rh,
        "rango_c": [crop.disease_t_min, crop.disease_t_max],
    }


def frost_outlook(crop: Crop, daily: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Riesgo de helada sobre la minima diaria pronosticada.

    Open-Meteo entrega la temperatura del aire a 2 m. En noches serenas la
    superficie del suelo y el canopeo bajo pueden estar varios grados por
    debajo, asi que se avisa con margen: se considera riesgo cuando la minima
    se acerca al umbral del cultivo, no solo cuando lo cruza.
    """
    eventos = []
    for dia in daily:
        tmin = dia.get("tmin")
        if tmin is None:
            continue
        tmin = float(tmin)
        if tmin <= crop.frost_c:
            nivel = "alto"
        elif tmin <= crop.frost_c + 3.0:
            nivel = "medio"
        else:
            continue
        eventos.append({"dia": dia["day"], "tmin": round(tmin, 1), "nivel": nivel})
    return {
        "umbral_c": crop.frost_c,
        "eventos": eventos,
        "nivel": "alto" if any(e["nivel"] == "alto" for e in eventos)
        else "medio" if eventos else "bajo",
    }


def heat_outlook(crop: Crop, daily: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Dias con maxima por encima del umbral de estres termico del cultivo."""
    eventos = [
        {"dia": dia["day"], "tmax": round(float(dia["tmax"]), 1)}
        for dia in daily
        if dia.get("tmax") is not None and float(dia["tmax"]) >= crop.heat_c
    ]
    return {"umbral_c": crop.heat_c, "eventos": eventos,
            "nivel": "alto" if len(eventos) >= 2 else "medio" if eventos else "bajo"}


def irrigation_outlook(series: Sequence[DailyPoint], dias: int = 14) -> dict[str, Any]:
    """Deficit hidrico acumulado en la ventana reciente.

    El balance es climatico: lluvia menos evapotranspiracion del cultivo. No
    modela el agua util del suelo, que depende de textura, profundidad de
    raices y del agua almacenada al inicio. Sirve para ordenar prioridades de
    riego entre lotes, no para calcular una lamina exacta.
    """
    ventana = list(series)[-dias:]
    if not ventana:
        return {"dias": 0, "balance_mm": 0.0, "lluvia_mm": 0.0, "etc_mm": 0.0,
                "nivel": "sin datos"}
    balance = round(sum(p.balance_mm for p in ventana), 1)
    lluvia = round(sum(p.precipitation_mm for p in ventana), 1)
    etc = round(sum(p.etc_mm for p in ventana), 1)
    if balance <= -60:
        nivel = "alto"
    elif balance <= -25:
        nivel = "medio"
    else:
        nivel = "bajo"
    return {"dias": len(ventana), "balance_mm": balance, "lluvia_mm": lluvia,
            "etc_mm": etc, "nivel": nivel}


# --------------------------------------------------------------------------
# Acceso a datos reales
# --------------------------------------------------------------------------

def _serie(payload: dict[str, Any], bloque: str, clave: str) -> list[Any]:
    return (payload.get(bloque) or {}).get(clave) or []


def _parse_daily(payload: dict[str, Any]) -> list[dict[str, Any]]:
    fechas = _serie(payload, "daily", "time")
    tmax = _serie(payload, "daily", "temperature_2m_max")
    tmin = _serie(payload, "daily", "temperature_2m_min")
    lluvia = _serie(payload, "daily", "precipitation_sum")
    et0 = _serie(payload, "daily", "et0_fao_evapotranspiration")
    salida = []
    for i, fecha in enumerate(fechas):
        salida.append({
            "day": date.fromisoformat(fecha),
            "tmax": tmax[i] if i < len(tmax) else None,
            "tmin": tmin[i] if i < len(tmin) else None,
            "precipitation_mm": lluvia[i] if i < len(lluvia) else None,
            "et0_mm": et0[i] if i < len(et0) else None,
        })
    return salida


def _parse_hourly(payload: dict[str, Any]) -> list[dict[str, Any]]:
    horas = _serie(payload, "hourly", "time")
    temp = _serie(payload, "hourly", "temperature_2m")
    rh = _serie(payload, "hourly", "relative_humidity_2m")
    lluvia = _serie(payload, "hourly", "precipitation")
    viento = _serie(payload, "hourly", "wind_speed_10m")
    rafaga = _serie(payload, "hourly", "wind_gusts_10m")
    suelo = _serie(payload, "hourly", "soil_moisture_0_to_7cm")
    salida = []
    for i, ts in enumerate(horas):
        salida.append({
            "ts": datetime.fromisoformat(ts),
            "temperature": temp[i] if i < len(temp) else None,
            "humidity": rh[i] if i < len(rh) else None,
            "precipitation": lluvia[i] if i < len(lluvia) else None,
            "wind": viento[i] if i < len(viento) else None,
            "gust": rafaga[i] if i < len(rafaga) else None,
            "soil_moisture": suelo[i] if i < len(suelo) else None,
        })
    return salida


async def fetch_history(lat: float, lon: float, desde: date,
                        hasta: date) -> list[dict[str, Any]]:
    """Serie diaria historica (reanalisis ERA5 via Open-Meteo)."""
    settings = get_settings()
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": desde.isoformat(),
        "end_date": hasta.isoformat(),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": TIMEZONE,
    }
    async with httpx.AsyncClient(timeout=settings.pipeline_http_timeout_seconds) as client:
        respuesta = await client.get(ARCHIVE_URL, params=params)
        respuesta.raise_for_status()
        return _parse_daily(respuesta.json())


async def fetch_forecast(lat: float, lon: float, dias: int = 7
                         ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Pronostico diario y horario. Devuelve ``(diario, horario)``."""
    settings = get_settings()
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "forecast_days": str(dias),
        "daily": ",".join(DAILY_VARIABLES),
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": TIMEZONE,
    }
    async with httpx.AsyncClient(timeout=settings.pipeline_http_timeout_seconds) as client:
        respuesta = await client.get(settings.open_meteo_forecast_url, params=params)
        respuesta.raise_for_status()
        payload = respuesta.json()
    return _parse_daily(payload), _parse_hourly(payload)


def crop_or_404(crop_key: str) -> Crop:
    from fastapi import HTTPException

    crop = CROPS.get(crop_key)
    if crop is None:
        raise HTTPException(422, f"Cultivo desconocido: {crop_key}")
    return crop


def catalog() -> list[dict[str, Any]]:
    """Catalogo serializable, con los parametros a la vista.

    Se exponen a proposito: quien lee un indicador tiene que poder ver con que
    coeficientes se calculo y discutirlos.
    """
    return [
        {
            "key": crop.key,
            "name": crop.name,
            "perennial": crop.perennial,
            "t_base_c": crop.t_base,
            "t_cap_c": crop.t_cap,
            "frost_c": crop.frost_c,
            "heat_c": crop.heat_c,
            "kc_perennial": crop.perennial_kc if crop.perennial else None,
            "stages": [
                {"key": s.key, "name": s.name, "gdd_from": s.gdd_from,
                 "gdd_to": s.gdd_to, "kc": s.kc}
                for s in crop.stages
            ],
            "disease": {
                "name": crop.disease_name,
                "rango_c": [crop.disease_t_min, crop.disease_t_max],
                "hr_min": crop.disease_rh,
                "horas_umbral": crop.disease_hours,
            },
        }
        for crop in CROPS.values()
    ]
