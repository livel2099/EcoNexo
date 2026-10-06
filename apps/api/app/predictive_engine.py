"""Pronósticos ambientales por riesgo: índices y modelos supervisados versionables.

Sin dependencias de ML adicionales. El aprendizaje usa etiquetas independientes,
cortes cronológicos con purga del horizonte y calibración en un bloque separado.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

FEATURES = ("temperature_max_c", "humidity_min_pct", "wind_max_kmh", "rain_total_mm")
BASELINE_VERSION = "fire-weather-index-v1"
HAZARDS = ("fire", "hydric", "health_heat", "health_air")
FEATURE_SETS = {
    "fire": FEATURES,
    "hydric": ("rain_total_mm", "rain_peak_mm", "rain_6h_max_mm"),
    "health_heat": ("apparent_max_c", "apparent_min_c", "hot_hours"),
    "health_air": ("pm25_mean_ug_m3", "pm25_max_ug_m3", "pm25_high_hours"),
}


def baseline_version(hazard: str) -> str:
    if hazard not in HAZARDS:
        raise ValueError("Riesgo desconocido")
    return BASELINE_VERSION if hazard == "fire" else f"{hazard}-environment-index-v1"


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(-35, min(35, value))))


def future_features(payload: dict, issued_at: datetime, hours: int, hazard: str = "fire") -> tuple[dict, datetime, datetime, list[dict]]:
    """Exige una serie futura completa, horaria, finita y con unidades explícitas."""
    if not isinstance(payload, dict):
        raise ValueError("Respuesta de pronóstico inválida")
    hourly = payload.get("hourly") or {}
    units = payload.get("hourly_units") or {}
    mapping = {"temperature_2m": "°C", "relative_humidity_2m": "%",
               "wind_speed_10m": "km/h", "precipitation": "mm"}
    if hazard == "hydric":
        mapping = {"precipitation": "mm"}
    elif hazard == "health_heat":
        mapping = {"apparent_temperature": "°C"}
    elif hazard == "health_air":
        mapping = {"pm2_5": "μg/m³"}
    elif hazard != "fire":
        raise ValueError("Riesgo desconocido")
    if not isinstance(hourly, dict) or not isinstance(units, dict) or any(str(units.get(key)).replace("µ", "μ") != unit for key, unit in mapping.items()):
        raise ValueError("El pronóstico no declara las unidades esperadas")
    start = issued_at.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    end = start + timedelta(hours=hours)
    series = []
    times = hourly.get("time", [])
    if not isinstance(times, list) or any(not isinstance(hourly.get(key), list) for key in mapping):
        raise ValueError("Serie horaria inválida")
    for index, raw_time in enumerate(times):
        if not isinstance(raw_time, str):
            raise ValueError("Timestamp horario inválido")
        timestamp = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        # Open-Meteo fecha la lluvia al final de la hora precedente. Para el
        # objetivo pluvial se archiva la hora de inicio de esa acumulación.
        if hazard == "hydric":
            timestamp -= timedelta(hours=1)
        if not start <= timestamp < end:
            continue
        item = {"time": timestamp.isoformat()}
        for key in mapping:
            values = hourly.get(key) or []
            value = values[index] if index < len(values) else None
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError(f"Pronóstico incompleto: {key}")
            item[key] = float(value)
        ranges = {"temperature_2m": (-90, 65), "relative_humidity_2m": (0, 100),
                  "wind_speed_10m": (0, 400), "precipitation": (0, 1000),
                  "apparent_temperature": (-110, 90), "pm2_5": (0, 5000)}
        if any(not ranges[key][0] <= item[key] <= ranges[key][1] for key in mapping):
            raise ValueError("Pronóstico fuera de rangos físicos")
        series.append(item)
    expected = [(start + timedelta(hours=i)).isoformat() for i in range(hours)]
    if [item["time"] for item in series] != expected:
        raise ValueError("Faltan horas futuras o hay timestamps duplicados/desordenados")
    if hazard == "hydric":
        rain = [item["precipitation"] for item in series]
        features = dict(zip(FEATURE_SETS[hazard], (sum(rain), max(rain), max(sum(rain[i:i + 6]) for i in range(len(rain) - 5)))))
    elif hazard == "health_heat":
        heat = [item["apparent_temperature"] for item in series]
        features = dict(zip(FEATURE_SETS[hazard], (max(heat), min(heat), sum(value >= 35 for value in heat))))
    elif hazard == "health_air":
        air = [item["pm2_5"] for item in series]
        features = dict(zip(FEATURE_SETS[hazard], (statistics.mean(air), max(air), sum(value >= 35 for value in air))))
    else:
        features = dict(zip(FEATURES, (
            max(item["temperature_2m"] for item in series),
            min(item["relative_humidity_2m"] for item in series),
            max(item["wind_speed_10m"] for item in series),
            sum(item["precipitation"] for item in series),
        )))
    return features, start, end, series


def baseline(features: dict, hazard: str = "fire") -> tuple[float, list[str]]:
    clamp = lambda value: max(0, min(1, value))
    if hazard == "hydric":
        total, peak, six = [float(features[key]) for key in FEATURE_SETS[hazard]]
        score = 0.3 * clamp(total / 150) + 0.3 * clamp(peak / 40) + 0.4 * clamp(six / 80)
        return round(score, 6), [f"Lluvia acumulada: {total:.1f} mm", f"Pico horario: {peak:.1f} mm", f"Máximo en 6 h: {six:.1f} mm", "Susceptibilidad meteorológica a anegamiento; falta validación de drenaje, suelo y relieve local."]
    if hazard == "health_heat":
        maximum, minimum, hot = [float(features[key]) for key in FEATURE_SETS[hazard]]
        score = 0.6 * clamp((maximum - 28) / 17) + 0.25 * clamp((minimum - 20) / 12) + 0.15 * clamp(hot / 12)
        return round(score, 6), [f"Sensación térmica máxima: {maximum:.1f} °C", f"Mínima: {minimum:.1f} °C", f"Horas con sensación ≥35 °C: {hot:.0f}", "Índice ambiental experimental; no estima enfermedad individual ni brotes."]
    if hazard == "health_air":
        mean, maximum, high = [float(features[key]) for key in FEATURE_SETS[hazard]]
        score = 0.6 * clamp(mean / 75) + 0.25 * clamp(maximum / 150) + 0.15 * clamp(high / 12)
        return round(score, 6), [f"PM2.5 medio del horizonte: {mean:.1f} μg/m³", f"Máximo horario: {maximum:.1f} μg/m³", f"Horas con PM2.5 ≥35 μg/m³: {high:.0f}", "Índice experimental de exposición ambiental; los cortes son heurísticos, no límites legales ni diagnósticos."]
    if hazard != "fire":
        raise ValueError("Riesgo desconocido")
    temperature, humidity, wind, rain = [float(features[key]) for key in FEATURES]
    score = (0.3 * clamp((temperature - 15) / 25) + 0.4 * clamp((80 - humidity) / 65)
             + 0.3 * clamp(wind / 50)) * (1 - 0.7 * clamp(rain / 15))
    reasons = [f"Máxima prevista: {temperature:.1f} °C", f"Humedad mínima: {humidity:.0f}%",
               f"Viento máximo: {wind:.1f} km/h", f"Lluvia acumulada: {rain:.1f} mm"]
    return round(score, 6), reasons


def same_scope(prediction: dict, observation: dict) -> bool:
    return (prediction["device_id"] == observation["device_id"]
            and prediction.get("hazard", "fire") == observation.get("hazard", "fire")
            and abs(prediction["latitude"] - observation["latitude"]) < 0.00001
            and abs(prediction["longitude"] - observation["longitude"]) < 0.00001)


def label_forecast(prediction: dict, observations: list[dict]) -> tuple[int | None, datetime | None]:
    events = [obs["start_at"] for obs in observations if same_scope(prediction, obs)
              and obs["outcome"] == "event" and prediction["valid_from"] <= obs["start_at"] < prediction["valid_to"]]
    if events:
        return 1, min(events)
    covered = any(same_scope(prediction, obs) and obs["outcome"] == "no_event"
                  and obs["start_at"] <= prediction["valid_from"] and obs["end_at"] >= prediction["valid_to"]
                  for obs in observations)
    return (0, None) if covered else (None, None)


def evaluation(predictions: list[dict], observations: list[dict], now: datetime) -> dict:
    matured = [p for p in predictions if p["valid_to"] <= now]
    observations_by_device = {}
    predictions_by_device = {}
    for obs in observations:
        observations_by_device.setdefault(obs["device_id"], []).append(obs)
    for prediction in predictions:
        predictions_by_device.setdefault(prediction["device_id"], []).append(prediction)
    samples = []
    for prediction in matured:
        label, event_at = label_forecast(prediction, observations_by_device.get(prediction["device_id"], []))
        if label is not None:
            samples.append((prediction, label, event_at))
    tp = sum(p["warning"] and y == 1 for p, y, _ in samples)
    fp = sum(p["warning"] and y == 0 for p, y, _ in samples)
    fn = sum(not p["warning"] and y == 1 for p, y, _ in samples)
    tn = sum(not p["warning"] and y == 0 for p, y, _ in samples)
    events = [obs for obs in observations if obs["outcome"] == "event" and obs["start_at"] <= now]
    leads = []
    for event in events:
        hits = [p for p in predictions_by_device.get(event["device_id"], []) if same_scope(p, event) and p["warning"]
                and p["issued_at"] < event["start_at"] and p["valid_from"] <= event["start_at"] < p["valid_to"]]
        if hits:
            leads.append((event["start_at"] - min(p["issued_at"] for p in hits)).total_seconds() / 3600)
    probabilistic = [(p["probability"], y) for p, y, _ in samples if p.get("probability") is not None]
    bins = []
    for index in range(5):
        bucket = [(prob, y) for prob, y in probabilistic if min(4, int(prob * 5)) == index]
        if bucket:
            bins.append(dict(count=len(bucket), mean_probability=statistics.mean(p for p, _ in bucket),
                             observed_rate=statistics.mean(y for _, y in bucket)))
    return dict(matured=len(matured), evaluated=len(samples), pending_labels=len(matured) - len(samples),
                tp=tp, fp=fp, fn=fn, tn=tn,
                precision=tp / (tp + fp) if tp + fp else None,
                recall=tp / (tp + fn) if tp + fn else None,
                brier=statistics.mean((p - y) ** 2 for p, y in probabilistic) if probabilistic else None,
                calibration=bins, independent_events=len(events), events_warned=len(leads),
                events_missed=len(events) - len(leads),
                event_recall=len(leads) / len(events) if events else None,
                median_lead_hours=statistics.median(leads) if leads else None)


def _fit(x: list[list[float]], y: list[int], steps: int = 800) -> tuple[list[float], float]:
    weights = [0.0] * len(x[0])
    intercept = 0.0
    for _ in range(steps):
        errors = [sigmoid(intercept + sum(w * v for w, v in zip(weights, row))) - label for row, label in zip(x, y)]
        intercept -= 0.1 * statistics.mean(errors)
        weights = [weight - 0.1 * (statistics.mean(error * row[j] for error, row in zip(errors, x)) + 0.01 * weight)
                   for j, weight in enumerate(weights)]
    return weights, intercept


def raw_logit(features: dict, artifact: dict) -> float:
    return artifact["intercept"] + sum(weight * (features[key] - mean) / scale
        for key, weight, mean, scale in zip(artifact.get("features", FEATURES), artifact["weights"], artifact["means"], artifact["scales"]))


def probability(features: dict, artifact: dict) -> float:
    return sigmoid(artifact["calibration_slope"] * raw_logit(features, artifact) + artifact["calibration_intercept"])


def train_model(rows: list[dict], horizon: int, hazard: str = "fire") -> tuple[dict, dict]:
    """Entrena sólo con features archivadas al emitir; no reconstruye el pasado."""
    feature_keys = FEATURE_SETS[hazard]
    if any(row.get("hazard", "fire") != hazard for row in rows):
        raise ValueError("No se pueden mezclar resultados de distintos riesgos")
    rows = sorted(rows, key=lambda row: (row["issued_at"], str(row["id"])))
    if len(rows) < 120:
        raise ValueError("Se necesitan al menos 120 pronósticos maduros con resultados independientes verificados")
    first, second = rows[int(len(rows) * 0.6)]["issued_at"], rows[int(len(rows) * 0.8)]["issued_at"]
    train = [row for row in rows if row["valid_to"] < first]
    calibration = [row for row in rows if first <= row["issued_at"] < second and row["valid_to"] < second]
    test = [row for row in rows if row["issued_at"] >= second]
    for name, block in (("entrenamiento", train), ("calibración", calibration), ("test", test)):
        if len(block) < 20 or sum(row["label"] for row in block) < 5 or sum(1 - row["label"] for row in block) < 5:
            raise ValueError(f"El bloque temporal de {name} necesita 20 muestras, al menos 5 eventos y 5 no eventos; se purgan ventanas solapadas")
    means = [statistics.mean(row["features"][key] for row in train) for key in feature_keys]
    scales = [max(statistics.pstdev(row["features"][key] for row in train), 1) for key in feature_keys]
    x = [[(row["features"][key] - mean) / scale for key, mean, scale in zip(feature_keys, means, scales)] for row in train]
    weights, intercept = _fit(x, [row["label"] for row in train])
    artifact = dict(schema=f"{hazard}-logistic-v1", features=list(feature_keys), means=means, scales=scales,
                    weights=weights, intercept=intercept)
    slopes, offset = _fit([[raw_logit(row["features"], artifact)] for row in calibration], [row["label"] for row in calibration])
    artifact.update(calibration_slope=slopes[0], calibration_intercept=offset)
    # El umbral se decide en calibración, nunca en test.
    threshold, best_f1 = 0.5, -1.0
    for candidate in [i / 20 for i in range(1, 20)]:
        tp = sum(probability(row["features"], artifact) >= candidate and row["label"] == 1 for row in calibration)
        fp = sum(probability(row["features"], artifact) >= candidate and row["label"] == 0 for row in calibration)
        fn = sum(probability(row["features"], artifact) < candidate and row["label"] == 1 for row in calibration)
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
        if f1 > best_f1:
            threshold, best_f1 = candidate, f1
    artifact["threshold"] = threshold
    prevalence = statistics.mean(row["label"] for row in train)
    probs = [probability(row["features"], artifact) for row in test]
    brier = statistics.mean((p - row["label"]) ** 2 for p, row in zip(probs, test))
    reference_brier = statistics.mean((prevalence - row["label"]) ** 2 for row in test)
    index_brier = statistics.mean((row["risk_index"] - row["label"]) ** 2 for row in test)
    tp = sum(p >= threshold and row["label"] == 1 for p, row in zip(probs, test))
    fp = sum(p >= threshold and row["label"] == 0 for p, row in zip(probs, test))
    fn = sum(p < threshold and row["label"] == 1 for p, row in zip(probs, test))
    digest = hashlib.sha256(json.dumps([(str(row["id"]), row["label"], row["features"]) for row in rows], sort_keys=True).encode()).hexdigest()
    metrics = dict(samples=len(rows), train=len(train), calibration=len(calibration), test=len(test),
                   purged=len(rows) - len(train) - len(calibration) - len(test),
                   train_end=max(row["valid_to"] for row in train).isoformat(),
                   calibration_start=first.isoformat(), calibration_end=max(row["valid_to"] for row in calibration).isoformat(),
                   test_start=second.isoformat(), test_end=max(row["valid_to"] for row in test).isoformat(),
                   dataset_sha256=digest, horizon_hours=horizon, hazard=hazard, brier=brier,
                   prevalence_brier=reference_brier, heuristic_index_brier=index_brier,
                   precision=tp / (tp + fp) if tp + fp else None, recall=tp / (tp + fn),
                   threshold=threshold, spatial_validation=False,
                   eligible=brier < reference_brier and brier < index_brier and tp / (tp + fn) >= 0.6,
                   scope="Validación temporal local; requiere evaluación prospectiva, no generalizable a otros territorios")
    return artifact, metrics


def drift(features: list[dict], artifact: dict) -> dict:
    if len(features) < 20:
        return dict(status="insufficient_data", samples=len(features), shifts={})
    shifts = {key: abs(statistics.mean(row[key] for row in features) - mean) / scale
              for key, mean, scale in zip(artifact.get("features", FEATURES), artifact["means"], artifact["scales"])}
    return dict(status="review" if max(shifts.values()) >= 2 else "within_reference", samples=len(features), shifts=shifts)
