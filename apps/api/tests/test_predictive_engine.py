from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.predictive_engine import (baseline, drift, evaluation, future_features,
                                   label_forecast, probability, train_model)

NOW = datetime(2026, 10, 6, 10, 25, tzinfo=timezone.utc)
DEVICE = uuid4()


def weather(hours=96):
    start = NOW.replace(hour=0, minute=0)
    return dict(hourly_units={"temperature_2m": "°C", "relative_humidity_2m": "%", "wind_speed_10m": "km/h", "precipitation": "mm"},
                hourly={"time": [(start + timedelta(hours=i)).isoformat() for i in range(hours)],
                        "temperature_2m": [35.0] * hours, "relative_humidity_2m": [20.0] * hours,
                        "wind_speed_10m": [45.0] * hours, "precipitation": [0.0] * hours})


def forecast(**changes):
    return dict(id=uuid4(), device_id=DEVICE, latitude=-26.92, longitude=-54.78,
                issued_at=NOW, valid_from=NOW + timedelta(hours=1), valid_to=NOW + timedelta(hours=25),
                warning=True, probability=None, risk_index=0.8, **changes)


def observation(outcome, start, end=None):
    return dict(device_id=DEVICE, latitude=-26.92, longitude=-54.78,
                outcome=outcome, start_at=start, end_at=end or start)


@pytest.mark.parametrize("horizon", [6, 24, 72])
def test_only_complete_future_hours_contribute(horizon):
    payload = weather()
    payload["hourly"]["temperature_2m"][0] = 999  # Hora pasada excluida.
    features, start, end, series = future_features(payload, NOW, horizon)
    assert start > NOW and end - start == timedelta(hours=horizon)
    assert len(series) == horizon and features["temperature_max_c"] == 35
    assert features["rain_total_mm"] == 0


@pytest.mark.parametrize("change", ["missing", "nan", "bad_units", "duplicate", "negative_rain"])
def test_bad_weather_never_becomes_low_risk(change):
    payload = weather()
    if change == "missing": payload["hourly"]["temperature_2m"][12] = None
    if change == "nan": payload["hourly"]["wind_speed_10m"][12] = float("nan")
    if change == "bad_units": payload["hourly_units"]["wind_speed_10m"] = "m/s"
    if change == "duplicate": payload["hourly"]["time"][12] = payload["hourly"]["time"][11]
    if change == "negative_rain": payload["hourly"]["precipitation"][12] = -1
    with pytest.raises(ValueError): future_features(payload, NOW, 24)


def test_higher_rain_reduces_index_without_claiming_probability():
    features = future_features(weather(), NOW, 24)[0]
    hot, reasons = baseline(features)
    wet, _ = baseline({**features, "rain_total_mm": 30})
    assert 0 <= wet < hot <= 1 and len(reasons) == 4


def test_missing_or_partial_evidence_is_unknown_and_moved_node_does_not_match():
    p = forecast()
    assert label_forecast(p, [])[0] is None
    obs = observation("no_event", p["valid_from"], p["valid_to"] - timedelta(minutes=1))
    assert label_forecast(p, [obs])[0] is None
    obs["end_at"] = p["valid_to"]
    assert label_forecast(p, [obs])[0] == 0
    obs["latitude"] += 0.1
    assert label_forecast(p, [obs])[0] is None


def test_omitted_events_count_even_without_any_forecast():
    obs = observation("event", NOW + timedelta(hours=2))
    result = evaluation([], [obs], NOW + timedelta(days=2))
    assert result["events_missed"] == 1 and result["event_recall"] == 0
    assert result["precision"] is None and result["brier"] is None


def test_metrics_do_not_count_repeated_forecasts_as_multiple_events():
    p = forecast()
    another = {**p, "id": uuid4(), "issued_at": NOW - timedelta(hours=1)}
    obs = observation("event", NOW + timedelta(hours=2))
    result = evaluation([p, another], [obs], NOW + timedelta(days=2))
    assert result["tp"] == 2 and result["events_warned"] == 1
    assert result["median_lead_hours"] == 3 and result["brier"] is None


def test_probability_calibration_and_false_alarm_metrics():
    p = {**forecast(), "probability": 0.8}
    obs = observation("no_event", p["valid_from"], p["valid_to"])
    result = evaluation([p], [obs], NOW + timedelta(days=2))
    assert result["fp"] == 1 and result["precision"] == 0
    assert result["brier"] == pytest.approx(0.64)
    assert result["calibration"][0]["observed_rate"] == 0


def training_rows():
    rows = []
    for index in range(300):
        issued = NOW - timedelta(days=400 - index)
        label = index % 2
        features = dict(temperature_max_c=35 if label else 17, humidity_min_pct=20 if label else 85,
                        wind_max_kmh=45 if label else 5, rain_total_mm=0 if label else 20)
        rows.append(dict(id=str(index), issued_at=issued, valid_to=issued + timedelta(hours=25),
                         features=features, label=label, risk_index=baseline(features)[0]))
    return rows


def test_training_is_purged_temporal_calibrated_and_reproducible():
    artifact, metrics = train_model(training_rows(), 24)
    assert metrics["eligible"] and metrics["purged"] > 0
    assert metrics["train_end"] < metrics["calibration_start"]
    assert metrics["calibration_end"] < metrics["test_start"]
    assert metrics["brier"] < metrics["prevalence_brier"]
    assert probability(training_rows()[1]["features"], artifact) > probability(training_rows()[0]["features"], artifact)
    assert train_model(training_rows(), 24)[0] == artifact


def test_test_data_never_changes_training_or_calibration():
    rows = training_rows()
    artifact, _ = train_model(rows, 24)
    for row in rows[240:]:
        row["label"] = 1 - row["label"]
    changed_artifact, metrics = train_model(rows, 24)
    assert artifact == changed_artifact and not metrics["eligible"]


def test_insufficient_labels_block_training():
    with pytest.raises(ValueError, match="120"): train_model(training_rows()[:50], 24)
    rows = training_rows()
    for row in rows: row["label"] = 0
    with pytest.raises(ValueError, match="eventos"): train_model(rows, 24)


def test_drift_has_no_false_healthy_status_without_samples():
    artifact, _ = train_model(training_rows(), 24)
    assert drift([], artifact)["status"] == "insufficient_data"
    changed = {**training_rows()[1]["features"], "temperature_max_c": 64}
    assert drift([changed] * 20, artifact)["status"] == "review"
