"""Frozen dimensionless configuration; no measured material defaults."""
from dataclasses import asdict, dataclass, fields
import json
import math
import re

SCOPE = "dimensionless_reaction_transport_benchmark"


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError("nonfinite JSON constant")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)


@dataclass(frozen=True)
class Config:
    schema_version: int
    scope: str
    scenario_id: str
    K: float
    Gamma: float
    Bi: float
    boundary_mode: str
    reservoir_ratio: float | None
    n_cells: int
    tau_end: float
    diagnostic_thresholds: list

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != {f.name for f in fields(cls)}:
            raise ValueError("configuration fields differ from frozen schema")
        return cls(**data)

    @classmethod
    def from_json(cls, text):
        return cls.from_dict(strict_json(text))

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1 or self.scope != SCOPE:
            raise ValueError("unsupported schema or scope")
        if not isinstance(self.scenario_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.scenario_id):
            raise ValueError("invalid scenario identifier")
        for name in ("K", "Gamma", "Bi", "tau_end"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("invalid nonnegative finite parameter")
        if self.Gamma == 0 or self.tau_end == 0:
            raise ValueError("Gamma and horizon must be positive")
        if type(self.n_cells) is not int or not 2 <= self.n_cells <= 127:
            raise ValueError("cell count outside bounded research range [2,127]")
        if self.boundary_mode not in ("infinite", "finite", "sealed"):
            raise ValueError("unknown boundary mode")
        if self.boundary_mode == "finite":
            if (self.reservoir_ratio is None or type(self.reservoir_ratio) not in (int, float)
                    or not math.isfinite(self.reservoir_ratio) or self.reservoir_ratio <= 0):
                raise ValueError("finite reservoir requires positive ratio")
        elif self.reservoir_ratio is not None:
            raise ValueError("no reservoir state in this mode; ratio must be null")
        if self.diagnostic_thresholds != [0.95, 0.99]:
            raise ValueError("diagnostic thresholds are frozen, not tolerances")

    def to_dict(self):
        return asdict(self)
