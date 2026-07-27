"""Tests del motor logico de reglas."""
from app.rules_engine import Condition, Rule, evaluate_rule


def test_and_all_conditions_must_match() -> None:
    # incendio forestal: temp alta + humedad baja
    rule = Rule(
        conditions=[
            Condition("temp", ">", 42),
            Condition("humidity", "<", 20),
        ],
        logic="AND",
    )
    assert evaluate_rule(rule, {"temp": 45, "humidity": 15}).fired is True
    assert evaluate_rule(rule, {"temp": 45, "humidity": 30}).fired is False


def test_or_any_condition_matches() -> None:
    rule = Rule(
        conditions=[Condition("nivel", ">", 8), Condition("turbidez", ">", 100)],
        logic="OR",
    )
    assert evaluate_rule(rule, {"nivel": 3, "turbidez": 120}).fired is True
    assert evaluate_rule(rule, {"nivel": 3, "turbidez": 50}).fired is False


def test_missing_variable_reported_and_blocks_and() -> None:
    rule = Rule(conditions=[Condition("temp", ">", 42), Condition("mq4", ">", 300)])
    ev = evaluate_rule(rule, {"temp": 50})
    assert ev.fired is False
    assert "mq4" in ev.missing_variables


def test_require_satellite_gates_firing() -> None:
    rule = Rule(conditions=[Condition("temp", ">", 42)], require_satellite=True)
    assert evaluate_rule(rule, {"temp": 50}, satellite_confirmed=False).fired is False
    assert evaluate_rule(rule, {"temp": 50}, satellite_confirmed=True).fired is True


def test_unsupported_operator_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        Condition("temp", "><", 1).matches(5)
