"""Reviewed discrete Arlabosse95°C readings and relative molar chemical potential.

This source interface has no interpolator, desorption rate, finite-path heat,
absolute chemical potential, wet storage term, or full-cycle material admission.
"""
from dataclasses import asdict, dataclass
from decimal import (
    Context, Decimal, DivisionByZero, InvalidOperation, Overflow,
    ROUND_HALF_EVEN, localcontext,
)
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

F = Fraction
SOURCE_SHA256 = 'd533f156e287a6772c10e8cea6e686449c2c47bcfb66f4cc26df6b4920349d94'
AW_NODE_ID = 'ARLABOSSE2005_ACTIVITY_95_DISCRETE'
HEAT_NODE_ID = 'ARLABOSSE2005_TOTAL_DESORPTION_95_DISCRETE'
MU_NODE_ID = 'ARLABOSSE2005_RELATIVE_MOLAR_MU_95_DISCRETE'
R_NODE_ID = 'CODATA2022_EXACT_MOLAR_GAS_CONSTANT'
ACTIVITY_NODE_ID = 'HACK2011_ACTIVITY_IDENTITY'


class DesorptionError(ValueError):
    """Evidence binding, explicit units or the discrete source domain is invalid."""


def _exact(value: object) -> Fraction:
    if type(value) in (int, Fraction):
        return F(value)
    if type(value) is Decimal and value.is_finite():
        return F(value)
    if type(value) is float and math.isfinite(value):
        return F(repr(value))
    raise DesorptionError('finite_explicit_number_required')


def _fraction(record: dict) -> Fraction:
    return F(int(record['numerator']), int(record['denominator']))


def _plain(value):
    if isinstance(value, Fraction):
        return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    return value


def _log_enclosure(x: Fraction) -> tuple[Fraction, Fraction, Fraction]:
    """Correctly rounded decimal logs bracketed before exact subtraction.

    Integer Decimal construction is exact. Each correctly rounded ln is within
    its adjacent representable decimals; subtraction/product then use rational
    arithmetic. No rounded division is performed on the source activity.
    """
    if x <= 0:
        raise DesorptionError('positive_activity_required')
    # Every field is explicit: Context() otherwise inherits mutable DefaultContext.
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN,
                              Emin=-999999, Emax=999999, capitals=1, clamp=0,
                              flags=[], traps=[InvalidOperation, DivisionByZero, Overflow])):
        a = Decimal(x.numerator).ln()
        b = Decimal(x.denominator).ln()
        return (F(a) - F(b), F(a.next_minus()) - F(b.next_plus()),
                F(a.next_plus()) - F(b.next_minus()))


@dataclass(frozen=True)
class SourceReading:
    value: Fraction | None
    digitization_bounds: tuple[Fraction, Fraction] | None
    unit: str
    node_id: str
    source_locator: str
    unknown_reasons: tuple[str, ...] = ()
    numerical_bounds: tuple[Fraction, Fraction] | None = None
    experimental_uncertainty: None = None


@dataclass(frozen=True)
class DesorptionPoint:
    moisture_kg_water_per_kg_dry_matter: Fraction
    temperature_K: Fraction
    activity: SourceReading
    total_desorption_heat: SourceReading
    chemical_potential_shift: SourceReading
    source_sha256: str = SOURCE_SHA256
    continuous_domain_admitted: None = None
    material_qualified: bool = False
    full_firing_cycle: bool = False
    training_eligible: bool = False
    qualification: str = 'reviewed_published_curve_reading_not_independent_experimental_validation'
    input_policy: str = 'exact_values_float_shortest_decimal_readout_v1'

    def to_record(self) -> dict:
        """JSON-safe exact rationals; browser parsing cannot round integer limbs."""
        return _plain(asdict(self))


@dataclass(frozen=True)
class ArlabosseDesorption95:
    """Use explicit asset root; hash-check reviewed source and assets every call.

    Raw publisher assets are privately cached, not distributed with the wheel.
    Missing assets fail closed. An input float is interpreted as its shortest
    decimal readout; Fraction.from_float requests exact binary interpretation.
    """
    source_path: Path
    repository_root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, 'source_path', Path(self.source_path).resolve())
        object.__setattr__(self, 'repository_root', Path(self.repository_root).resolve())
        self._load()

    def _load(self) -> tuple[dict, dict, Fraction]:
        try:
            raw = self.source_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
                raise DesorptionError('reviewed_source_metadata_changed')
            source = json.loads(raw)
            # Parse the same bytes that were checked, avoiding a second read.
            verified = {}
            for asset in source['assets']:
                path = (self.repository_root / asset['path']).resolve()
                if not path.is_relative_to(self.repository_root):
                    raise DesorptionError('source_asset_outside_repository')
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != asset['sha256']:
                    raise DesorptionError('reviewed_source_asset_changed')
                verified[asset['path']] = data
            facts = json.loads(verified[source['facts_path']])
            codata = json.loads(verified[source['codata_path']])
            constants = codata['values']
            r = F(constants['N_A_per_mol']) * F(constants['k_B_j_per_k'])
            if r != F(constants['R_j_per_mol_k']):
                raise DesorptionError('inconsistent_gas_constant_source')
            return source, facts, r
        except OSError as exc:
            raise DesorptionError('reviewed_source_asset_unavailable') from exc

    def at_moisture(self, moisture: int | float | Decimal | Fraction, *,
                    temperature: int | float | Decimal | Fraction, unit: str) -> DesorptionPoint:
        """Read one extracted W node at95°C; q_total includes vaporization heat.

        The chemical potential shift is in J/mol water relative to the activity's
        own standard state. It is not absolute mu, J/kg, or an energy-source term.
        """
        source, facts, r = self._load()
        if type(unit) is not str or unit not in ('degC', 'K'):
            raise DesorptionError('explicit_K_or_degC_required')
        t = _exact(temperature) + (F('273.15') if unit == 'degC' else 0)
        if t != F(source['temperature_K']):
            raise DesorptionError('temperature_outside_single_95_degC_isotherm')
        w = _exact(moisture)
        observations = [o for o in facts['observations']
                        if F(o['requested_moisture_kg_water_per_kg_dry_matter']) == w]
        if len(observations) != 2:
            raise DesorptionError('moisture_not_an_extracted_discrete_node')

        def reading(figure: int, node_id: str, reading_unit: str) -> SourceReading:
            row = next(o for o in observations if o['figure'] == figure)
            value = _fraction(row['value']) if row['value'] is not None else None
            bounds = (tuple(_fraction(b) for b in row['digitization_bounds'])
                      if row['digitization_bounds'] is not None else None)
            return SourceReading(value, bounds, reading_unit, node_id,
                                 f'Arlabosse2005 Figure{figure}; W={w}; facts.json observations',
                                 tuple(row['unknown_reasons']))

        aw = reading(1, AW_NODE_ID, 'dimensionless')
        heat = reading(2, HEAT_NODE_ID, 'J/kg removed water')
        if aw.value is None or aw.digitization_bounds is None:
            raise DesorptionError('reviewed_activity_missing')
        nominal, lo, hi = _log_enclosure(aw.value)
        low_aw, high_aw = aw.digitization_bounds
        read_lo = _log_enclosure(low_aw)[1]
        read_hi = _log_enclosure(high_aw)[2]
        rt = r * t
        shift = SourceReading(
            rt * nominal, (rt * read_lo, rt * read_hi), 'J/mol water', MU_NODE_ID,
            'Arlabosse2005 Figure1; Hack2011 p1033; NIST CODATA2022 constants',
            numerical_bounds=(rt * lo, rt * hi))
        return DesorptionPoint(w, t, aw, heat, shift)

    def registry_payload(self) -> dict:
        """Use the existing evidence registry to trace each equation's inputs."""
        source, facts, r = self._load()
        common = {
            'role': 'equation', 'basis': source['material']['description'],
            'evidence_kind': 'derived_from_evidence',
            'applicability': {'status': 'conditional', 'rationale': source['activity_semantics']},
            'uncertainty': {'status': 'unquantified', 'rationale': source['bounds_semantics']},
            'domain': {'temperature_K': [368.15, 368.15],
                       'material_classes': [source['material']['class']],
                       'notes': 'Discrete extracted W nodes only; no continuous interval or interpolation.'},
            'source_metadata_sha256': SOURCE_SHA256,
        }
        nodes = []
        for node_id, unit, figure in ((AW_NODE_ID, '1', 1), (HEAT_NODE_ID, 'J/kg', 2)):
            source_node_id = f'ARLABOSSE2005_FIG{figure}_SOURCE_TRACE'
            nodes.append({**common, 'id': source_node_id, 'role': 'output',
                          'evidence_kind': 'measured_public_data', 'unit': unit,
                          'value': 'Published continuous raster trace; original experimental markers unavailable',
                          'dependencies': [],
                          'citations': [{'source_id': facts['source_id'], 'locator': f'Figure{figure},95degC', 'support': 'value'}],
                          'original_asset_sha256': next(s['sha256'] for s in facts['sources'] if s['figure'] == figure)})
            nodes.append({**common, 'id': node_id, 'unit': unit,
                          'value': f'Exact lookup of Figure{figure} reviewed nodes; unreadable heat remains null',
                          'dependencies': [source_node_id],
                          'derivation': 'extract_pixels.py plus independent_check.py; facts.json preserved byte-identical',
                          'citations': [{'source_id': facts['source_id'], 'locator': f'Figure{figure},95degC', 'support': 'value'}],
                          'quantity_basis': 'dimensionless activity' if figure == 1 else 'J/kg removed water; latent contribution already included'})
        nodes[-1]['citations'].append({'source_id': 'FERRASSE_LECOMTE_2004',
                                      'locator': 'p1366 Eq4,p1368-1369 Eqs21-24', 'support': 'context'})
        law = {**common, 'evidence_kind': 'physical_law_or_constant',
               'domain': {'universal': True},
               'applicability': {'status': 'matched', 'rationale': 'SI constant or defining thermodynamic identity; no material-specific closure.'},
               'uncertainty': {'status': 'exact', 'rationale': 'Exact SI defining constants or mathematical identity; evaluated logarithm error is recorded separately.'}}
        nodes.extend([
            {**law, 'id': R_NODE_ID, 'role': 'physical_parameter', 'unit': 'J/(mol*K)',
             'basis': 'SI amount of substance', 'value': float(r),
             'exact_value': _plain(r), 'dependencies': [],
             'citations': [{'source_id': 'nist-codata-2022', 'locator': 'Avogadro and Boltzmann constant rows; exact R=kB*NA', 'support': 'value'}]},
            {**law, 'id': ACTIVITY_NODE_ID, 'unit': 'J/mol',
             'basis': 'mole of species under its chosen activity reference', 'value': 'mu-mu_reference=R*T*ln(a)',
             'dependencies': [], 'citations': [{'source_id': 'HACK_2011_ACTIVITY', 'locator': 'p1033 first paragraph', 'support': 'equation'}]},
            {**common, 'id': MU_NODE_ID, 'unit': 'J/mol',
             'value': 'R*(95+273.15)*ln(aw(W)); relative to the source activity standard state',
             'dependencies': [AW_NODE_ID, R_NODE_ID, ACTIVITY_NODE_ID],
             'derivation': '50-digit correctly-rounded logs of rational numerator/denominator; exact rational subtraction and RT product; adjacent-decimal numerical enclosures',
             'citations': [{'source_id': 'HACK_2011_ACTIVITY', 'locator': 'p1033 first paragraph', 'support': 'context'}]},
        ])
        sources = [{**s, 'year': 2022} if s['id'] == 'nist-codata-2022' else s
                   for s in source['sources']]
        return {'schema_version': '1.0', 'sources': sources, 'nodes': nodes}
