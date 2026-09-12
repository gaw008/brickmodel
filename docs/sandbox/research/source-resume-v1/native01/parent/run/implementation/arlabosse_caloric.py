"""Source-specific dry-mass Cp and sensible enthalpy difference, never molar U."""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import math
import hashlib
import json
from pathlib import Path

SOURCE_SHA256 = '2f9caf23689092e548b2b3d7abf7c54d58d177569a7850b47c69df15e74295d6'
NODE_ID = 'ARLABOSSE2005_DRY_CP_EQ2'
DELTA_H_NODE_ID = 'ARLABOSSE2005_DRY_SENSIBLE_ENTHALPY_DIFF'
SOURCE_ID = 'SRC_ARLABOSSE_2005_CONTACT_DRYING'
F = Fraction


class CaloricError(ValueError):
    """Source binding, units or the declared calorimetric domain is invalid."""


def _exact(value: object) -> Fraction:
    if type(value) in (int, Fraction):
        return F(value)
    if type(value) is Decimal and value.is_finite():
        return F(value)
    if type(value) is float and math.isfinite(value):
        # Explicit decimal-readout semantics, never a clipped physical input.
        return F(repr(value))
    raise CaloricError('finite_temperature_number_required')


def _celsius(value: object, unit: str) -> Fraction:
    if type(unit) is not str or unit not in ('K', 'degC'):
        raise CaloricError('explicit_K_or_degC_required')
    result = _exact(value) - (F(27315, 100) if unit == 'K' else 0)
    if not 35 <= result <= 105:
        raise CaloricError('temperature_outside_measured_35_to_105_degC')
    return result


@dataclass(frozen=True)
class CaloricValue:
    value: Fraction
    unit: str
    source_sha256: str
    input_temperatures_degC: tuple[Fraction, ...]
    input_policy_id: str = 'exact_values_float_shortest_decimal_readout_v1'
    node_id: str = NODE_ID
    basis: str = 'kg dry matter of Arlabosse2005 mixed-feed sample'
    fit_error: None = None
    material_qualified: bool = False
    qualification: str = 'reported_fit_evaluation_not_independent_prediction_or_molar_storage'


@dataclass(frozen=True)
class ArlabosseDryCaloric:
    """Pinned source/assets checked at construction and every operation.

    Temperatures require explicit K/degC. int/Fraction/Decimal are exact; finite
    floats mean their shortest round-trip decimal readout, not their exact
    binary value. Fraction.from_float requests that latter interpretation.
    No values are clipped to the source temperature domain.
    """
    source_path: Path
    repository_root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, 'source_path', Path(self.source_path).resolve())
        object.__setattr__(self, 'repository_root', Path(self.repository_root).resolve())
        self._source()

    def _source(self) -> dict:
        try:
            raw = self.source_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
                raise CaloricError('reviewed_source_metadata_changed')
            source = json.loads(raw)
            for asset in source['assets']:
                path = (self.repository_root / asset['path']).resolve()
                if not path.is_relative_to(self.repository_root):
                    raise CaloricError('source_asset_outside_repository')
                if hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
                    raise CaloricError('reviewed_source_asset_changed')
            return source
        except OSError as exc:
            raise CaloricError('reviewed_source_asset_unavailable') from exc

    def cp(self, temperature: int | float | Decimal | Fraction, *, unit: str) -> CaloricValue:
        """Evaluate dry-mass Cp; source fit uncertainty remains unquantified."""
        self._source()
        t = _celsius(temperature, unit)
        return CaloricValue(F(1434) + F(329, 100) * t, 'J/(kg*K)', SOURCE_SHA256, (t,))

    def delta_h(self, start: int | float | Decimal | Fraction, end: int | float | Decimal | Fraction, *, unit: str) -> CaloricValue:
        """Integrate Cp over its measured domain; no absolute formation reference."""
        self._source()
        a, b = _celsius(start, unit), _celsius(end, unit)
        value = F(1434) * (b - a) + F(329, 200) * (b*b - a*a)
        return CaloricValue(value, 'J/kg', SOURCE_SHA256, (a, b), node_id=DELTA_H_NODE_ID)

    def registry_payload(self) -> dict:
        """Return a v1 evidence-registry payload, not a runtime material admission."""
        s = self._source()
        payload = {'schema_version': '1.0', 'sources': [{
            'id': SOURCE_ID, 'title': s['title'], 'url': s['url'],
            'authors': s['authors'], 'year': s['year'], 'license': s['license'],
            'retrieved_at': s['accessed_at_utc'][:10], 'read_status': 'full_text_checked',
            'reading_scope': s['read_status'], 'metadata_sha256': SOURCE_SHA256,
            'assets': s['assets']}], 'nodes': [{
                'id': NODE_ID, 'evidence_kind': 'literature_constitutive_model',
                'role': 'equation', 'basis': s['caloric_relation']['basis'],
                'unit': 'J/(kg*K)', 'value': s['caloric_relation']['equation'],
                'dependencies': [], 'citations': [{'source_id': SOURCE_ID,
                    'locator': s['caloric_relation']['locator'], 'support': 'equation'}],
                'applicability': {'status': 'conditional', 'rationale': 'Only the original mixed-feed dry sample and calorimetric interval; no brick/reaction transfer.'},
                'uncertainty': {'status': 'unquantified', 'rationale': 'No fit residuals or parameter uncertainty reported in inspected source.'},
                'domain': {'temperature_K': [308.15, 378.15],
                    'material_classes': [s['material']['class']],
                    'notes': 'Sample preparation/feed fractions are bound by source metadata hash; dry-mass Cp is not molar Cv or reaction enthalpy.'}}]}

        cp_node = payload['nodes'][0]
        payload['nodes'].append({
            **cp_node, 'id': DELTA_H_NODE_ID, 'unit': 'J/kg',
            'evidence_kind': 'derived_from_evidence', 'dependencies': [NODE_ID],
            'value': 'delta_h(a,b)=1434*(b-a)+(3.29/2)*(b*b-a*a); a,b in degC',
            'derivation': 'arlabosse_caloric.py:ArlabosseDryCaloric.delta_h analytically integrates the source dry-mass Cp; no absolute formation enthalpy is assigned.',
            'citations': [{'source_id': SOURCE_ID,
                          'locator': s['caloric_relation']['locator'], 'support': 'context'}]})
        return payload
