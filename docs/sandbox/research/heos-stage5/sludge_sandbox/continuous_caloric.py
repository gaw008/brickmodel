"""Explicit derived caloric model: integrate original adjacent Shomate Cp fits.

Original coefficients/domains and Cp jumps remain unchanged. A selected original
h anchor supplies the energy reference; per-segment constant h shifts are public.
No entropy, IAPWS join, material admission, or accuracy improvement is implied.
"""
from dataclasses import dataclass, field
from fractions import Fraction
import math

from .thermochemistry import ShomateGas, ShomateSegment, ThermochemistryError


class ContinuousCaloricError(ThermochemistryError):
    """Invalid source/derivation, unavailable domain or nonfinite derived value."""


def _number(value):
    try:
        result = float(value) if type(value) in (int, float) else math.nan
    except OverflowError:
        result = math.nan
    if not math.isfinite(result):
        raise ContinuousCaloricError('temperature_must_be_finite_number')
    return result


def _float(value):
    try:
        result = float(value)
    except OverflowError as exc:
        raise ContinuousCaloricError('derived_caloric_outside_float_range') from exc
    if not math.isfinite(result):
        raise ContinuousCaloricError('derived_caloric_outside_float_range')
    return result


def _label(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


def _cp_integral(segment, start, end):
    """Exact integral for the binary64 coefficients and endpoints, in J/mol."""
    a, b, c, d, e, _, _, _ = map(Fraction, segment.coefficients)
    x, y = Fraction(start)/1000, Fraction(end)/1000
    return 1000*(a*(y-x) + b*(y*y-x*x)/2 + c*(y**3-x**3)/3
                 + d*(y**4-x**4)/4 + e*(1/x-1/y))


def _source_primitive(segment, temperature):
    """Original h equation, evaluated exactly before comparing its offset."""
    a, b, c, d, e, f, _, h = map(Fraction, segment.coefficients)
    t = Fraction(temperature)/1000
    return (Fraction(segment.formation_enthalpy_298_j_mol)
            + 1000*(a*t+b*t*t/2+c*t**3/3+d*t**4/4-e/t+f-h))


@dataclass(frozen=True)
class SegmentOffset:
    temperature_range_k: tuple[float, float]
    enthalpy_offset_j_mol: float
    reference_temperature_k: float
    source_h_at_reference_j_mol: float
    derived_h_at_reference_j_mol: float
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class CaloricResolution:
    temperature_k: float
    enthalpy_ulp_j_mol: float
    internal_energy_ulp_j_mol: float
    anchor_enthalpy_ulp_j_mol: float


@dataclass(frozen=True)
class ContinuousSegment:
    source_segment: ShomateSegment
    _low_h: Fraction = field(repr=False)

    @property
    def temperature_range_k(self):
        return self.source_segment.temperature_range_k

    @property
    def source_ids(self):
        return self.source_segment.source_ids

    @property
    def gas_constant_j_mol_k(self):
        return self.source_segment.gas_constant_j_mol_k

    def _temperature(self, temperature_k):
        temperature = _number(temperature_k)
        if not self.temperature_range_k[0] <= temperature <= self.temperature_range_k[1]:
            raise ContinuousCaloricError('temperature_out_of_domain')
        return temperature

    def _enthalpy(self, temperature):
        return self._low_h + _cp_integral(self.source_segment, self.temperature_range_k[0], temperature)

    def enthalpy_j_mol(self, temperature_k):
        return _float(self._enthalpy(self._temperature(temperature_k)))

    def internal_energy_j_mol(self, temperature_k):
        temperature = self._temperature(temperature_k)
        return _float(self._enthalpy(temperature)-Fraction(self.gas_constant_j_mol_k)*Fraction(temperature))

    def cp_j_mol_k(self, temperature_k):
        return self.source_segment.cp_j_mol_k(self._temperature(temperature_k))

    def cv_j_mol_k(self, temperature_k):
        return self.cp_j_mol_k(temperature_k)-self.gas_constant_j_mol_k


@dataclass(frozen=True, kw_only=True)
class ContinuousShomateGas:
    source_gas: ShomateGas
    model_id: str
    version: str
    anchor_temperature_k: float
    method_source_ids: tuple[str, ...]
    gas_constant_source_ids: tuple[str, ...]
    allow_manufactured: bool = False
    method_id: str = field(default='piecewise_shomate_cp_integral_v1', init=False)
    segments: tuple[ContinuousSegment, ...] = field(init=False)
    segment_offsets: tuple[SegmentOffset, ...] = field(init=False)
    anchor_enthalpy_j_mol: float = field(init=False)

    def __post_init__(self):
        source = self.source_gas
        if type(source) is not ShomateGas or any(type(s) is not ShomateSegment for s in source.segments):
            raise ContinuousCaloricError('explicit_original_shomate_gas_required')
        if type(self.allow_manufactured) is not bool:
            raise ContinuousCaloricError('invalid_manufactured_gate')
        if source.classification == 'manufactured_test_fixture' and not self.allow_manufactured:
            raise ContinuousCaloricError('manufactured_model_requires_test_mode')
        if not _label(self.model_id) or not _label(self.version):
            raise ContinuousCaloricError('derived_model_identity_required')
        sources = self.method_source_ids
        if (not isinstance(sources, (list, tuple)) or not sources
                or any(not _label(value) for value in sources) or len(set(sources)) != len(sources)):
            raise ContinuousCaloricError('unique_method_source_ids_required')
        object.__setattr__(self, 'method_source_ids', tuple(sources))
        constants = self.gas_constant_source_ids
        if (not isinstance(constants, (list, tuple)) or not constants
                or any(not _label(value) for value in constants) or len(set(constants)) != len(constants)):
            raise ContinuousCaloricError('unique_gas_constant_source_ids_required')
        object.__setattr__(self, 'gas_constant_source_ids', tuple(constants))
        anchor = _number(self.anchor_temperature_k)
        try:
            anchor_segment = source.segment_for(anchor)
            anchor_h = source.enthalpy_j_mol(anchor)
        except ThermochemistryError as exc:
            raise ContinuousCaloricError(str(exc)) from exc
        object.__setattr__(self, 'anchor_temperature_k', anchor)
        object.__setattr__(self, 'anchor_enthalpy_j_mol', anchor_h)
        # Recover the first range's lower h from the chosen original branch.
        # Exact arithmetic keeps every small increment beside a large anchor.
        prior = Fraction(0)
        for segment in source.segments:
            if segment is anchor_segment:
                prior += _cp_integral(segment, segment.temperature_range_k[0], anchor)
                break
            prior += _cp_integral(segment, *segment.temperature_range_k)
        low_h = Fraction(anchor_h)-prior
        derived, offsets = [], []
        for segment in source.segments:
            low, high = segment.temperature_range_k
            derived.append(ContinuousSegment(segment, low_h))
            offsets.append(SegmentOffset(
                segment.temperature_range_k, _float(low_h-_source_primitive(segment, low)),
                low, segment.enthalpy_j_mol(low), _float(low_h), segment.source_ids))
            low_h += _cp_integral(segment, low, high)
        object.__setattr__(self, 'segments', tuple(derived))
        object.__setattr__(self, 'segment_offsets', tuple(offsets))

    @property
    def species_id(self):
        return self.source_gas.species_id

    @property
    def temperature_range_k(self):
        return self.source_gas.temperature_range_k

    @property
    def gas_constant_j_mol_k(self):
        return self.source_gas.segments[0].gas_constant_j_mol_k

    @property
    def source_classification(self):
        return self.source_gas.classification

    @property
    def classification(self):
        return ('manufactured_test_fixture' if self.source_classification == 'manufactured_test_fixture'
                else 'derived_from_evidence')

    @property
    def source_ids(self):
        return tuple(sorted(set(self.source_gas.source_ids+self.method_source_ids+self.gas_constant_source_ids
                                +tuple(s for segment in self.source_gas.segments for s in segment.source_ids))))

    @property
    def provenance_status(self):
        return 'source_links_and_derivation_declared_not_material_admission'

    def segment_for(self, temperature_k):
        temperature = _number(temperature_k)
        for segment in reversed(self.segments):
            if segment.temperature_range_k[0] <= temperature <= segment.temperature_range_k[1]:
                return segment
        raise ContinuousCaloricError('temperature_out_of_domain')

    def enthalpy_j_mol(self, temperature_k):
        return self.segment_for(temperature_k).enthalpy_j_mol(temperature_k)

    def internal_energy_j_mol(self, temperature_k):
        return self.segment_for(temperature_k).internal_energy_j_mol(temperature_k)

    def cp_j_mol_k(self, temperature_k):
        return self.segment_for(temperature_k).cp_j_mol_k(temperature_k)

    def cv_j_mol_k(self, temperature_k):
        return self.segment_for(temperature_k).cv_j_mol_k(temperature_k)

    def resolution_j_mol(self, temperature_k):
        temperature = _number(temperature_k)
        return CaloricResolution(temperature, math.ulp(self.enthalpy_j_mol(temperature)),
                                 math.ulp(self.internal_energy_j_mol(temperature)),
                                 math.ulp(self.anchor_enthalpy_j_mol))

    def _change(self, start_k, end_k):
        self.segment_for(start_k)
        self.segment_for(end_k)
        start, end = _number(start_k), _number(end_k)
        low, high = min(start, end), max(start, end)
        integral = Fraction(0)
        for segment in self.source_gas.segments:
            a, b = max(low, segment.temperature_range_k[0]), min(high, segment.temperature_range_k[1])
            if b > a:
                integral += _cp_integral(segment, a, b)
        return integral if end >= start else -integral

    def enthalpy_change_j_mol(self, start_k, end_k):
        return _float(self._change(start_k, end_k))

    def internal_energy_change_j_mol(self, start_k, end_k):
        integral = self._change(start_k, end_k)
        return _float(integral-Fraction(self.gas_constant_j_mol_k)*(Fraction(end_k)-Fraction(start_k)))
