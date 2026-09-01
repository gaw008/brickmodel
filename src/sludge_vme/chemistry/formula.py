from __future__ import annotations

import re
from collections.abc import Mapping

ATOMIC_WEIGHTS_KG_PER_MOL: dict[str, float] = {
    "H": 0.00100794,
    "C": 0.0120107,
    "N": 0.0140067,
    "O": 0.0159994,
    "Na": 0.02298977,
    "Mg": 0.024305,
    "Al": 0.02698154,
    "Si": 0.0280855,
    "P": 0.03097376,
    "S": 0.032065,
    "Cl": 0.035453,
    "K": 0.0390983,
    "Ca": 0.040078,
    "Ti": 0.047867,
    "Fe": 0.055845,
}
_TOKEN = re.compile(r"([A-Z][a-z]?)([0-9]*\.?[0-9]*)")


def parse_formula(formula: str | Mapping[str, float]) -> dict[str, float]:
    if isinstance(formula, Mapping):
        parsed = {str(element): float(count) for element, count in formula.items()}
    elif isinstance(formula, str):
        parsed: dict[str, float] = {}
        position = 0
        for match in _TOKEN.finditer(formula):
            if match.start() != position:
                raise ValueError(f"unsupported formula syntax at position {position}: {formula!r}")
            element, count_text = match.groups()
            parsed[element] = parsed.get(element, 0.0) + (float(count_text) if count_text else 1.0)
            position = match.end()
        if position != len(formula) or not parsed:
            raise ValueError(f"unsupported formula: {formula!r}")
    else:
        raise TypeError("formula must be a string or element-count mapping")
    if any(count <= 0.0 for count in parsed.values()):
        raise ValueError("formula counts must be positive")
    return parsed


def formula_molar_mass(formula: str | Mapping[str, float]) -> float:
    parsed = parse_formula(formula)
    try:
        return sum(ATOMIC_WEIGHTS_KG_PER_MOL[element] * count for element, count in parsed.items())
    except KeyError as exc:
        raise ValueError(f"unknown atomic weight for element {exc.args[0]!r}") from exc


def formula_element_moles(formula: str | Mapping[str, float], amount_mol: float) -> dict[str, float]:
    return {element: count * amount_mol for element, count in parse_formula(formula).items()}
