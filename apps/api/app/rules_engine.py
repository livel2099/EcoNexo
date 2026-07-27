"""Motor logico de reglas.

Evalua condiciones del tipo:
  SI [variable][operador][umbral] DURANTE [ventana] EN [zona/dispositivos]
  ENTONCES [severidad + acciones]

`evaluate_rule` es pura (recibe lecturas ya agregadas por la capa de datos):
para cada variable de la regla se pasa el valor representativo dentro de la
ventana (p.ej. el promedio o el ultimo). Testeable sin base de datos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

_OPS: dict[str, Callable[[float, float], bool]] = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


@dataclass
class Condition:
    variable: str
    operator: str
    threshold: float

    def matches(self, value: float) -> bool:
        op = _OPS.get(self.operator)
        if op is None:
            raise ValueError(f"Operador no soportado: {self.operator}")
        return op(value, self.threshold)


@dataclass
class Rule:
    conditions: list[Condition]
    logic: str = "AND"                 # AND | OR
    require_satellite: bool = False


@dataclass
class RuleEvaluation:
    fired: bool
    matched_conditions: list[Condition]
    missing_variables: list[str]


def evaluate_rule(
    rule: Rule,
    values: dict[str, float],
    satellite_confirmed: bool = False,
) -> RuleEvaluation:
    """Evalua una regla contra los valores representativos de la ventana.

    `values` mapea variable -> valor agregado dentro de la ventana temporal.
    Si falta una variable, esa condicion cuenta como no cumplida.
    """
    matched: list[Condition] = []
    missing: list[str] = []

    for cond in rule.conditions:
        if cond.variable not in values:
            missing.append(cond.variable)
            continue
        if cond.matches(values[cond.variable]):
            matched.append(cond)

    if rule.logic == "OR":
        base = len(matched) >= 1
    else:  # AND
        base = len(matched) == len(rule.conditions)

    fired = base and (satellite_confirmed if rule.require_satellite else True)
    return RuleEvaluation(fired=fired, matched_conditions=matched, missing_variables=missing)
