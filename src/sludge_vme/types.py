from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CaseConfig:
    raw: dict[str, Any]
    source_path: Path
    content_hash: str


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str


@dataclass
class ValidationReport:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    normalized_simplex_residuals: dict[str, float] = field(default_factory=dict)
    element_double_count_checks: dict[str, str] = field(default_factory=dict)
    source_coverage: float = 0.0

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [asdict(item) for item in self.errors],
            "warnings": [asdict(item) for item in self.warnings],
            "normalized_simplex_residuals": self.normalized_simplex_residuals,
            "element_double_count_checks": self.element_double_count_checks,
            "source_coverage": self.source_coverage,
        }


@dataclass(frozen=True)
class NormalizedFeed:
    dry_fractions: dict[str, float]
    water_kg_per_kg_dry_by_feedstock: dict[str, float]
    mixture_water_kg_per_kg_dry: float


@dataclass(frozen=True)
class RunStatus:
    code: str
    message: str
    success: bool


@dataclass
class ForwardResult:
    fidelity: str
    status: RunStatus
    coordinates: dict[str, Any]
    fields: dict[str, Any]
    summary: dict[str, Any]
    conservation: dict[str, Any]
    flags: list[str]
    warnings: list[str]
    provenance: dict[str, Any]
    solver_statistics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "fidelity": self.fidelity,
            "status": asdict(self.status),
            "coordinates": self.coordinates,
            "fields": self.fields,
            "summary": self.summary,
            "conservation": self.conservation,
            "flags": self.flags,
            "warnings": self.warnings,
            "provenance": self.provenance,
            "solver_statistics": self.solver_statistics,
        }
