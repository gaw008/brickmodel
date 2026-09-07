"""Validate and trace evidence dependencies before a physical model is evaluated.

This verifies declared metadata and domain compatibility. It does not establish that
a citation is scientifically correct or that its asserted reading status is authentic.
Those claims require the separate recorded source review and experimental validation.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import urlparse

from .units import UnitError, require_unit

KINDS = frozenset({
    "physical_law_or_constant", "measured_public_data", "literature_constitutive_model",
    "derived_from_evidence", "virtual_design_choice", "numerical_policy",
    "manufactured_test_fixture", "unknown",
})
ROLES = frozenset({"physical_parameter", "equation", "output", "design_input", "numerical_setting"})
READ_STATES = frozenset({"full_text_checked", "data_checked", "metadata_only", "abstract_only", "not_read"})
DIRECT_KINDS = frozenset({"physical_law_or_constant", "measured_public_data", "literature_constitutive_model"})
DOMAIN_AXES = {"material_classes": "material_class", "atmospheres": "atmosphere", "geometries": "geometry"}


class EvidenceError(ValueError):
    """Registry syntax or its dependency graph is invalid."""


@dataclass(frozen=True)
class EvidenceIssue:
    node_id: str
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class EvidenceAssessment:
    allowed: bool
    result_lane: str
    traceability_coverage: float
    issues: tuple[EvidenceIssue, ...]
    required_node_ids: tuple[str, ...]
    scientific_validation: str = "not_established_by_registry"
    source_assets: str = "not_checked"

    def as_dict(self) -> dict:
        return asdict(self)


def _text(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{field} must be nonempty text")


def _choice(value: Any, allowed: set | frozenset, field: str) -> None:
    if not isinstance(value, str) or value not in allowed:
        raise EvidenceError(f"Invalid {field}")


def _numeric_data(value: Any) -> None:
    """Structured parameter values may contain numeric data, never missing placeholders."""
    if type(value) in (int, float):
        try:
            if math.isfinite(value):
                return
        except OverflowError:
            pass
        raise EvidenceError("Parameter value exceeds finite numeric range")
    if isinstance(value, list) and value:
        for item in value:
            _numeric_data(item)
        return
    if isinstance(value, dict) and value and all(isinstance(k, str) and k for k in value):
        for item in value.values():
            _numeric_data(item)
        return
    raise EvidenceError("Parameter data must contain finite numbers; empty/null/text/bool rejected")


def _finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise EvidenceError("Nonfinite value in registry")
    if isinstance(value, dict):
        for item in value.values():
            _finite(item)
    elif isinstance(value, list):
        for item in value:
            _finite(item)


def _range(value: Any, field: str) -> None:
    try:
        valid = (isinstance(value, (list, tuple)) and len(value) == 2
                 and all(type(v) in (float, int) and math.isfinite(v) for v in value)
                 and value[0] <= value[1])
    except OverflowError:
        valid = False
    if not valid:
        raise EvidenceError(f"{field} must be a finite ordered [lower, upper] range")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


class EvidenceRegistry:
    """A snapshot of an acyclic evidence graph; all outward records are copies."""

    def __init__(self, payload: dict):
        self._payload = deepcopy(payload)
        self._sources: dict[str, dict] = {}
        self._nodes: dict[str, dict] = {}
        self._validate()

    @classmethod
    def from_dict(cls, payload: dict) -> "EvidenceRegistry":
        return cls(payload)

    @classmethod
    def from_file(cls, path: Path | str) -> "EvidenceRegistry":
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        except (OSError, ValueError) as exc:
            raise EvidenceError("Cannot read registry JSON") from exc
        return cls(payload)

    @property
    def digest(self) -> str:
        data = json.dumps(self._payload, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(data).hexdigest()

    def _validate(self) -> None:
        p = self._payload
        if not isinstance(p, dict) or p.get("schema_version") != "1.0":
            raise EvidenceError("Unsupported registry schema")
        _finite(p)
        for field, destination in (("sources", self._sources), ("nodes", self._nodes)):
            records = p.get(field)
            if not isinstance(records, list):
                raise EvidenceError(f"{field} must be a list")
            for record in records:
                if not isinstance(record, dict):
                    raise EvidenceError(f"{field} entries must be objects")
                identifier = record.get("id")
                if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", identifier):
                    raise EvidenceError("Invalid record id")
                if identifier in destination:
                    raise EvidenceError(f"Duplicate id: {identifier}")
                destination[identifier] = record
        for source in self._sources.values():
            for key in ("title", "url", "license", "retrieved_at"):
                _text(source.get(key), f"source.{key}")
            if urlparse(source["url"]).scheme not in ("https", "http") or not urlparse(source["url"]).netloc:
                raise EvidenceError("Source URL must be an HTTP(S) location")
            if not isinstance(source.get("authors"), list) or not source["authors"]:
                raise EvidenceError("Source authors are required")
            for author in source["authors"]:
                _text(author, "author")
            if type(source.get("year")) is not int or source["year"] < 1:
                raise EvidenceError("Source year is required")
            try:
                date.fromisoformat(source["retrieved_at"])
            except ValueError as exc:
                raise EvidenceError("retrieved_at must be an ISO calendar date") from exc
            _choice(source.get("read_status"), READ_STATES, "source read_status")
        for node in self._nodes.values():
            self._validate_node(node)
        # Visit every node, including unused records, to reject hidden cycles.
        self._ordered(tuple(self._nodes))

    def _validate_node(self, node: dict) -> None:
        kind, role = node.get("evidence_kind"), node.get("role")
        _choice(kind, KINDS, "evidence kind")
        _choice(role, ROLES, "role")
        if kind == "virtual_design_choice" and role != "design_input":
            raise EvidenceError("virtual_design_choice requires design_input role")
        if kind == "numerical_policy" and role != "numerical_setting":
            raise EvidenceError("numerical_policy requires numerical_setting role")
        _text(node.get("basis"), "node.basis")
        try:
            require_unit(node.get("unit"))
        except UnitError as exc:
            raise EvidenceError(str(exc)) from exc
        if "value" not in node or (kind == "unknown" and node["value"] is not None):
            raise EvidenceError("Unknown values must be explicit null")
        if role in ("physical_parameter", "design_input", "numerical_setting") and kind != "unknown":
            _numeric_data(node["value"])
        if role == "equation" and kind != "unknown":
            _text(node["value"], "equation.value")
        dependencies = node.get("dependencies")
        if not isinstance(dependencies, list) or any(not isinstance(i, str) for i in dependencies):
            raise EvidenceError("dependencies must be a list of ids")
        if len(dependencies) != len(set(dependencies)):
            raise EvidenceError("Duplicate dependency")
        if kind == "derived_from_evidence" and not dependencies:
            raise EvidenceError("Derived node requires upstream dependencies")
        if role in {"physical_parameter", "equation"} and kind == "derived_from_evidence":
            _text(node.get("derivation"), "derived node.derivation")
        citations = node.get("citations")
        if not isinstance(citations, list):
            raise EvidenceError("citations must be a list")
        for citation in citations:
            if (not isinstance(citation, dict) or not isinstance(citation.get("source_id"), str)
                    or citation["source_id"] not in self._sources):
                raise EvidenceError("Unknown citation source")
            _text(citation.get("locator"), "citation.locator")
            _choice(citation.get("support"), {"value", "equation", "context"}, "citation support")
        for field, statuses in (("applicability", {"matched", "conditional", "unassessed", "mismatch"}),
                                ("uncertainty", {"reported", "derived", "unquantified", "exact", "not_applicable"})):
            entry = node.get(field)
            if not isinstance(entry, dict):
                raise EvidenceError(f"Invalid {field}")
            _choice(entry.get("status"), statuses, field)
            _text(entry.get("rationale"), f"{field}.rationale")
        if kind in {"virtual_design_choice", "numerical_policy", "manufactured_test_fixture"}:
            _text(node.get("rationale"), "node.rationale")
        domain = node.get("domain")
        if not isinstance(domain, dict) or not domain:
            raise EvidenceError("Explicit domain is required")
        allowed = {*DOMAIN_AXES, "temperature_K", "pressure_Pa", "universal", "notes"}
        if set(domain) - allowed:
            raise EvidenceError("Unknown domain axis")
        if "universal" in domain and type(domain["universal"]) is not bool:
            raise EvidenceError("universal must be boolean")
        if domain.get("universal") and (kind != "physical_law_or_constant" or len(domain) != 1):
            raise EvidenceError("Only a physical law/constant can declare a universal domain")
        if not domain.get("universal") and not set(domain).intersection({*DOMAIN_AXES, "temperature_K", "pressure_Pa"}):
            raise EvidenceError("Domain notes cannot substitute for explicit applicability axes")
        for axis in DOMAIN_AXES:
            if axis in domain and (not isinstance(domain[axis], list) or not domain[axis]
                                   or any(not isinstance(i, str) or not i.strip() for i in domain[axis])):
                raise EvidenceError(f"Invalid domain axis {axis}")
        for axis in ("temperature_K", "pressure_Pa"):
            if axis in domain:
                _range(domain[axis], axis)
                if domain[axis][0] <= 0:
                    raise EvidenceError(f"{axis} must be positive")

    def _ordered(self, roots: tuple[str, ...]) -> list[str]:
        order, done, active = [], set(), set()

        def visit(identifier: str):
            if identifier not in self._nodes:
                raise EvidenceError(f"Missing dependency: {identifier}")
            if identifier in active:
                raise EvidenceError(f"Dependency cycle: {identifier}")
            if identifier in done:
                return
            active.add(identifier)
            for dependency in self._nodes[identifier]["dependencies"]:
                visit(dependency)
            active.remove(identifier)
            done.add(identifier)
            order.append(identifier)

        for root in roots:
            visit(root)
        return order

    def trace(self, node_id: str) -> dict:
        order = self._ordered((node_id,))
        sources = sorted({c["source_id"] for i in order for c in self._nodes[i]["citations"]})
        return {"root": node_id, "registry_sha256": self.digest,
                "nodes": deepcopy([self._nodes[i] for i in order]),
                "sources": deepcopy([self._sources[i] for i in sources]),
                "scope": "declared_source_trace_not_scientific_validation"}

    def assess(self, roots: list[str], context: Mapping[str, Any], *, mode: str = "evidence") -> EvidenceAssessment:
        if mode not in ("evidence", "exploratory", "manufactured"):
            raise EvidenceError("Unknown execution mode")
        if not isinstance(roots, list) or not roots or any(not isinstance(i, str) for i in roots):
            raise EvidenceError("Nonempty requested node ids are required")
        if not isinstance(context, Mapping):
            raise EvidenceError("Context must be a mapping")
        order = self._ordered(tuple(roots))
        issues: list[EvidenceIssue] = []
        covered: dict[str, bool] = {}
        physical_roots: dict[str, set[str]] = {}
        equation_roots: dict[str, set[str]] = {}
        lane = {"evidence": "evidence_constrained", "exploratory": "exploratory",
                "manufactured": "manufactured_test_fixture"}[mode]
        for identifier in order:
            node = self._nodes[identifier]
            kind, role = node["evidence_kind"], node["role"]
            own_coverage = True
            physical_roots[identifier] = set().union(
                *(physical_roots[i] for i in node["dependencies"]))
            equation_roots[identifier] = set().union(
                *(equation_roots[i] for i in node["dependencies"]))

            def issue(code: str, message: str, severity: str = "error"):
                issues.append(EvidenceIssue(identifier, code, message, severity))

            if kind == "unknown":
                issue("unknown_dependency", "No supported value is available")
                own_coverage = False
            elif kind == "manufactured_test_fixture":
                own_coverage = False
                if mode != "manufactured":
                    issue("fixture_not_evidence", "Manufactured values require the dedicated test mode")
            elif kind in DIRECT_KINDS:
                support = "equation" if role == "equation" else "value"
                own_coverage = any(
                    c["support"] == support and self._sources[c["source_id"]]["read_status"]
                    in {"full_text_checked", "data_checked"} for c in node["citations"])
                if not own_coverage:
                    issue("direct_evidence_missing", "No checked citation directly supports this value/relation")
                elif role in {"physical_parameter", "equation"}:
                    physical_roots[identifier].add(identifier)
                    if role == "equation":
                        equation_roots[identifier].add(identifier)
            if (kind == "derived_from_evidence" and role in {"physical_parameter", "equation"}
                    and not physical_roots[identifier]):
                own_coverage = False
                issue("physical_evidence_root_missing", "Design/numerical choices cannot establish a material property")
            if kind == "derived_from_evidence" and role == "equation" and not equation_roots[identifier]:
                own_coverage = False
                if mode != "manufactured":
                    issue("equation_evidence_root_missing",
                          "A derived relation must trace an upstream sourced equation, not only a measured number")
            applicable = node["applicability"]["status"]
            if applicable != "matched":
                severity = "warning" if applicable == "conditional" and mode == "exploratory" else "error"
                issue("applicability_" + applicable, node["applicability"]["rationale"], severity)
            for axis, key in DOMAIN_AXES.items():
                if axis in node["domain"]:
                    if key not in context:
                        issue("context_missing", f"Required context: {key}")
                    elif context[key] not in node["domain"][axis]:
                        issue("outside_domain", f"Context does not match {axis}")
            for axis in ("temperature_K", "pressure_Pa"):
                if axis not in node["domain"]:
                    continue
                if axis not in context:
                    issue("context_missing", f"Required context: {axis}")
                    continue
                value = context[axis]
                interval = [value, value] if type(value) in (int, float) else value
                try:
                    _range(interval, axis)
                except EvidenceError:
                    issue("invalid_context", f"Invalid context range: {axis}")
                    continue
                low, high = node["domain"][axis]
                if interval[0] < low or interval[1] > high:
                    issue("outside_domain", f"Context range exceeds {axis}")
            covered[identifier] = own_coverage and all(covered[i] for i in node["dependencies"])
        physical = [i for i in order if self._nodes[i]["role"] in {"physical_parameter", "equation"}]
        coverage = sum(covered[i] for i in physical) / len(physical) if physical else 0.0
        return EvidenceAssessment(not any(i.severity == "error" for i in issues), lane, coverage,
                                  tuple(issues), tuple(order))
