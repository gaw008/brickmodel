"""Amadou2006 source-specific equilibrium desorption, not drying/energy closure."""
from dataclasses import dataclass
from decimal import Context, Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

from .evidence import EvidenceRegistry

SOURCE_SHA256 = '8070dddbca2b70863650d936bc11ad0e244c03b674aed677326c573368507c9a'
SOURCE_ID = 'SRC_AMADOU_2006_DESORPTION'
NODE_ID = 'AMADOU2006_OSWIN_DESORPTION'
MATERIAL_ID = 'rosheim_urban_biological_sludge_mechanically_dewatered_2006'
NUMERICAL_POLICY = 'decimal80_half_even_float_shortest_decimal_rounded_endpoint_inverse_v1'


class DesorptionError(ValueError):
    """Source binding, explicit units, or the source-specific domain is invalid."""


def _exact(value: object) -> Fraction:
    if type(value) in (int, Fraction):
        return Fraction(value)
    if type(value) is Decimal and value.is_finite():
        return Fraction(value)
    if type(value) is float and math.isfinite(value):
        return Fraction(repr(value))
    raise DesorptionError('finite_numeric_value_required')


def _decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def _temperature(value: object, unit: str) -> int:
    if type(unit) is not str or unit not in ('K', 'degC'):
        raise DesorptionError('explicit_K_or_degC_required')
    t = _exact(value) - (Fraction('273.15') if unit == 'K' else 0)
    if t not in (30, 50):
        raise DesorptionError('only_exact_30_or_50_degC_supported')
    return int(t)


@dataclass(frozen=True)
class DesorptionValue:
    value: Decimal
    quantity: str
    input_value: Fraction
    temperature_degC: int
    node_id: str
    basis: str
    unit: str = '1'
    material_id: str = MATERIAL_ID
    source_id: str = SOURCE_ID
    source_sha256: str = SOURCE_SHA256
    numerical_policy: str = NUMERICAL_POLICY
    uncertainty: None = None
    material_qualified: bool = False
    qualification: str = 'source_specific_desorption_fit_not_dynamic_or_full_material_validation'


@dataclass(frozen=True)
class AmadouDesorption:
    """Pinned metadata/PDF checked on construction and every operation.

    Inputs int/Fraction/Decimal are exact; finite floats denote their shortest
    decimal readout. Use Fraction.from_float for exact binary-value semantics.
    Calculations use a private 80-digit half-even Decimal context. Transcendental
    rounding is a numerical policy, not a certified enclosure or physical error.
    Inverse admission uses the *returned 80-digit forward endpoint values* and
    maps exact equality to the original activity endpoint. No epsilon, clipping,
    temperature interpolation, adsorption branch or sorption heat is provided.
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
                raise DesorptionError('reviewed_source_metadata_changed')
            source = json.loads(raw)
            for asset in source['assets']:
                path = (self.repository_root / asset['path']).resolve()
                if not path.is_relative_to(self.repository_root):
                    raise DesorptionError('source_asset_outside_repository')
                if hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
                    raise DesorptionError('reviewed_source_asset_changed')
            return source
        except OSError as exc:
            raise DesorptionError('reviewed_source_asset_unavailable') from exc

    def _evaluate(self, value: object, temperature: object, unit: str,
                  temperature_unit: str, inverse: bool) -> DesorptionValue:
        source = self._source()
        if type(unit) is not str or unit != '1':
            raise DesorptionError('explicit_dimensionless_unit_1_required')
        x = _exact(value)
        t = _temperature(temperature, temperature_unit)
        row = next(r for r in source['relation']['rows'] if r['temperature_degC'] == t)
        with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN)):
            k, n = Decimal(row['k']), Decimal(row['n'])
            def forward(a: Decimal) -> Decimal:
                return k * (a / (1 - a)) ** n
            a, b = Decimal('.1'), Decimal('.8')
            if inverse:
                low, high = forward(a), forward(b)
                if not Fraction(low) <= x <= Fraction(high):
                    raise DesorptionError('moisture_outside_source_activity_image')
                if x == Fraction(low):
                    result = a
                elif x == Fraction(high):
                    result = b
                else:
                    ratio = (_decimal(x) / k) ** (1 / n)
                    result = ratio / (1 + ratio)
            else:
                if not Fraction(a) <= x <= Fraction(b):
                    raise DesorptionError('activity_outside_inferred_0.10_to_0.80')
                result = forward(_decimal(x))
        suffix = 'INVERSE' if inverse else 'FORWARD'
        return DesorptionValue(result, 'water_activity' if inverse else 'equilibrium_dry_basis_moisture',
                               x, t, f'{NODE_ID}_{t}_{suffix}',
                               'equilibrium relative humidity fraction' if inverse else 'kg water / kg dry solid')

    def moisture(self, activity: object, temperature: object, *, unit: str,
                 temperature_unit: str) -> DesorptionValue:
        """Evaluate Xeq at source-specific activity and exactly30/50degC."""
        return self._evaluate(activity, temperature, unit, temperature_unit, False)

    def activity(self, moisture: object, temperature: object, *, unit: str,
                 temperature_unit: str) -> DesorptionValue:
        """Invert source Xeq with the same kg-water/kg-dry-solid basis."""
        return self._evaluate(moisture, temperature, unit, temperature_unit, True)

    def registry_payload(self) -> dict:
        """Validated equation -> parameter-row -> source trace, no material admission."""
        source = self._source()
        relation = source['relation']
        nodes = []
        for row in relation['rows']:
            t = row['temperature_degC']
            prefix = f'{NODE_ID}_{t}'
            common = {
                'basis': relation['basis'], 'unit': '1',
                'evidence_kind': 'literature_constitutive_model',
                'applicability': {'status': 'conditional', 'rationale': 'Only original Rosheim desorption sample; no generic sludge transfer.'},
                'uncertainty': {'status': 'unquantified', 'rationale': relation['EQM_qualification']},
                'domain': {'temperature_K': [t + 273.15, t + 273.15],
                           'material_classes': [source['material']['class']],
                           'notes': relation['domain_interpretation'] + ' ' + relation['temperature_policy']},
                'citations': [{'source_id': SOURCE_ID, 'locator': relation['locator'], 'support': 'value'}]}
            nodes.append({**common, 'id': prefix + '_PARAMETERS', 'role': 'physical_parameter',
                          'value': {'k': float(row['k']), 'n': float(row['n'])},
                          'printed_decimal_values': {'k': row['k'], 'n': row['n']}, 'dependencies': []})
            forward = {**common, 'id': prefix + '_FORWARD', 'role': 'equation',
                       'value': relation['equation'], 'dependencies': [prefix + '_PARAMETERS'],
                       'citations': [{'source_id': SOURCE_ID, 'locator': relation['locator'], 'support': 'equation'}]}
            nodes.append(forward)
            nodes.append({**common, 'id': prefix + '_INVERSE', 'role': 'equation',
                          'basis': 'equilibrium relative humidity fraction',
                          'evidence_kind': 'derived_from_evidence',
                          'value': 'aw=(Xeq/k)**(1/n)/(1+(Xeq/k)**(1/n))',
                          'dependencies': [prefix + '_FORWARD'],
                          'derivation': 'Algebraic inversion of monotone positive-k positive-n Oswin desorption relation; rounded endpoint policy ' + NUMERICAL_POLICY})
        payload = {'schema_version': '1.0', 'sources': [{
            'id': SOURCE_ID, 'title': source['title'], 'url': source['url'],
            'authors': source['authors'], 'year': source['year'], 'license': source['license'],
            'retrieved_at': source['accessed_at_utc'][:10], 'read_status': 'full_text_checked',
            'reading_scope': source['read_status'], 'metadata_sha256': SOURCE_SHA256,
            'activity_label_interpretation': relation['activity_label_interpretation'],
            'basis_locator': relation['basis_locator'],
            'assets': source['assets']}], 'nodes': nodes}
        EvidenceRegistry.from_dict(payload)
        return payload
