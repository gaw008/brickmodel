"""Declared-input condensed-water transport leaf, without a physical host.

The caller supplies complete molar chemical potentials and enthalpies in one
reference. This leaf checks input correspondence and exact nominal algebra;
it does not authenticate those inputs against actual storage/chemical objects.
Conduction and local evaporation remain separate. No latent source is added.
"""
from dataclasses import dataclass, field, replace
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path


MODEL_ID = 'MAKELA2016_CONDITIONAL_SORPTION_MOISTURE_FACE_V1'
SOURCE_ID = 'SRC_MAKELA_2016_UNTREATED_PAPER_MILL_MOISTURE'
PDF_SHA256 = 'f4200d99c4fa8f3f6585fde9ec2e15455bfa78644a953e52b7311c1df25cba91'
FACTS_PATH = 'data/sandbox/research/makela-moisture-v1/source.json'
FACTS_SHA256 = 'b4f77618270d5e21977eada439af7a55197527b3947c02c79173161dde52c5df'
MODEL_PATH = 'data/sandbox/research/makela-moisture-v1/model.json'
MODEL_SHA256 = '118bf0ec21a5989e20cb3761d0833afb08b4503107219f441b19385f27abb0fe'
CLASSIFICATIONS = ('derived_from_evidence', 'virtual_design_choice', 'manufactured_test_fixture')


class SorptionMoistureError(ValueError):
    """A declared face/input or its binary64 readout cannot be admitted."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise SorptionMoistureError(reason)


def _project(value: F, name: str) -> float:
    try:
        out = float(value)
    except (OverflowError, ValueError) as exc:
        raise SorptionMoistureError(name+'_overflow') from exc
    _require(math.isfinite(out), name+'_overflow')
    _require(value == 0 or out != 0, name+'_underflow')
    return out


def _scalar(value: int | float | F, name: str) -> F:
    _require(type(value) in (int, float, F), name+'_finite_numeric_required')
    if type(value) is float:
        _require(math.isfinite(value), name+'_finite_numeric_required')
    result = F(value)
    _project(result, name)
    return result


def _metadata(source_ids: tuple[str, ...], classification: str) -> None:
    _require(type(source_ids) is tuple and source_ids and
             all(type(s) is str and s.strip() for s in source_ids), 'declared_input_sources_required')
    _require(classification in CLASSIFICATIONS, 'declared_input_classification_required')


def _rat(value: F) -> list[int]:
    return [value.numerator, value.denominator]


@dataclass(frozen=True)
class CondensedWaterPoint:
    temperature_k: F
    moisture_kg_water_per_kg_dry: F
    pressure_pa: F
    chemical_potential_j_mol: F
    partial_molar_enthalpy_j_mol: F
    water_molar_mass_kg_mol: F
    energy_reference_id: str
    source_ids: tuple[str, ...]
    input_classification: str

    def __post_init__(self) -> None:
        for name in ('temperature_k', 'moisture_kg_water_per_kg_dry', 'pressure_pa',
                     'chemical_potential_j_mol', 'partial_molar_enthalpy_j_mol', 'water_molar_mass_kg_mol'):
            object.__setattr__(self, name, _scalar(getattr(self, name), name))
        _metadata(self.source_ids, self.input_classification)
        _require(type(self.energy_reference_id) is str and bool(self.energy_reference_id.strip()),
                 'declared_energy_reference_required')

    def to_record(self) -> dict:
        result = {name: _rat(getattr(self, name)) for name in ('temperature_k',
            'moisture_kg_water_per_kg_dry', 'pressure_pa', 'chemical_potential_j_mol',
            'partial_molar_enthalpy_j_mol', 'water_molar_mass_kg_mol')}
        result.update(energy_reference_id=self.energy_reference_id, source_ids=list(self.source_ids),
                      input_classification=self.input_classification)
        return result


@dataclass(frozen=True)
class MoistureFaceGeometry:
    """Total controlled geometric volume on each side, never fluid pore volume."""
    area_m2: F
    center_distance_m: F
    left_dry_mass_kg: F
    right_dry_mass_kg: F
    left_total_volume_m3: F
    right_total_volume_m3: F
    source_ids: tuple[str, ...]
    input_classification: str

    def __post_init__(self) -> None:
        for name in ('area_m2', 'center_distance_m', 'left_dry_mass_kg', 'right_dry_mass_kg',
                     'left_total_volume_m3', 'right_total_volume_m3'):
            value = _scalar(getattr(self, name), name)
            _require(value > 0, 'positive_'+name+'_required')
            object.__setattr__(self, name, value)
        _metadata(self.source_ids, self.input_classification)

    def to_record(self) -> dict:
        result = {name: _rat(getattr(self, name)) for name in ('area_m2', 'center_distance_m',
            'left_dry_mass_kg', 'right_dry_mass_kg', 'left_total_volume_m3', 'right_total_volume_m3')}
        result.update(source_ids=list(self.source_ids), input_classification=self.input_classification,
                      volume_scope='controlled total specimen geometry, not available fluid volume')
        return result


@dataclass(frozen=True)
class MoistureThermodynamicFactor:
    """A caller-declared secant/limit at the specified face T and W interval."""
    gamma_j_mol: F
    temperature_k: F
    moisture_interval: tuple[F, F]
    method: str
    source_ids: tuple[str, ...]
    input_classification: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'gamma_j_mol', _scalar(self.gamma_j_mol, 'factor_gamma'))
        object.__setattr__(self, 'temperature_k', _scalar(self.temperature_k, 'factor_temperature'))
        _require(type(self.moisture_interval) is tuple and len(self.moisture_interval) == 2,
                 'factor_moisture_interval_required')
        object.__setattr__(self, 'moisture_interval', tuple(_scalar(w, 'factor_moisture')
                                                          for w in self.moisture_interval))
        _metadata(self.source_ids, self.input_classification)

    def to_record(self) -> dict:
        return {'gamma_j_mol': _rat(self.gamma_j_mol), 'temperature_k': _rat(self.temperature_k),
            'moisture_interval': [_rat(w) for w in self.moisture_interval], 'method': self.method,
            'source_ids': list(self.source_ids), 'input_classification': self.input_classification,
            'source_factor_authentication': 'not performed by pure leaf'}


@dataclass(frozen=True)
class EffectiveMoistureDiffusivity:
    value_m2_s: F
    source_ids: tuple[str, ...]
    input_classification: str
    _provenance_json: str = field(repr=False)

    def __post_init__(self) -> None:
        value = _scalar(self.value_m2_s, 'diffusivity')
        _require(value > 0, 'positive_diffusivity_required')
        object.__setattr__(self, 'value_m2_s', value)
        _metadata(self.source_ids, self.input_classification)
        _require(type(self._provenance_json) is str, 'diffusivity_provenance_required')
        try:
            provenance = json.loads(self._provenance_json)
            # Also rejects finite-looking exponent tokens that decode to infinity.
            json.dumps(provenance, allow_nan=False)
        except (ValueError, OverflowError) as exc:
            raise SorptionMoistureError('diffusivity_finite_json_provenance_required') from exc
        _require(type(provenance) is dict, 'diffusivity_provenance_object_required')

    @classmethod
    def manufactured(cls, value_m2_s: int | float | F, rationale: str) -> 'EffectiveMoistureDiffusivity':
        _require(type(rationale) is str and bool(rationale.strip()), 'manufactured_rationale_required')
        return cls(value_m2_s, ('manufactured:moisture_diffusivity',), 'manufactured_test_fixture',
                   json.dumps({'rationale': rationale, 'material_qualified': False}))

    def to_record(self) -> dict:
        return {'value_m2_s': _rat(self.value_m2_s), 'source_ids': list(self.source_ids),
            'input_classification': self.input_classification, 'provenance': json.loads(self._provenance_json)}


def _source_bytes(path: Path, expected: str, kind: str) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SorptionMoistureError('makela_'+kind+'_unavailable') from exc
    _require(hashlib.sha256(raw).hexdigest() == expected, 'makela_'+kind+'_changed')
    return raw


def load_makela_diffusivity(repository_root: Path, original_pdf_path: Path) -> EffectiveMoistureDiffusivity:
    """Verify the already-read source PDF and metadata; return a declared snapshot.

    The pure face function performs no file IO and does not reauthenticate this
    snapshot. An actual host adapter must bind and recheck its source provider.
    """
    root = Path(repository_root)
    facts = json.loads(_source_bytes(root/FACTS_PATH, FACTS_SHA256, 'facts'))
    model = json.loads(_source_bytes(root/MODEL_PATH, MODEL_SHA256, 'model'))
    pdf = _source_bytes(Path(original_pdf_path), PDF_SHA256, 'original_pdf')
    _require(len(pdf) == facts['original_pdf']['bytes'] and facts['original_pdf']['sha256'] == PDF_SHA256
             and model['upstream']['source_facts_sha256'] == FACTS_SHA256
             and model['upstream']['original_pdf_sha256'] == PDF_SHA256, 'makela_metadata_binding')
    value = F(facts['selected_diffusivity_m2_s'])
    _require(value == F(model['D_m2_s']) == F('8.56e-9'), 'makela_selected_diffusivity_changed')
    provenance = {'source_facts': facts, 'model_definition': model,
        'verification': 'original PDF/facts/model SHA checked at snapshot creation; source document was previously read',
        'model_sha256': MODEL_SHA256, 'facts_sha256': FACTS_SHA256, 'original_pdf_sha256': PDF_SHA256,
        'source_state_binding_verified': False, 'material_qualified': False, 'training_eligible': False}
    return EffectiveMoistureDiffusivity(value, (SOURCE_ID, MODEL_ID, PDF_SHA256, FACTS_SHA256, MODEL_SHA256),
                                      'derived_from_evidence', json.dumps(provenance, sort_keys=True))


@dataclass(frozen=True)
class QuantityProjection:
    name: str
    exact: F
    binary64: float
    absolute_projection_error: F

    def to_record(self) -> dict:
        return {'name': self.name, 'exact': _rat(self.exact), 'binary64': self.binary64,
                'absolute_projection_error': _rat(self.absolute_projection_error)}


@dataclass(frozen=True)
class MoistureFaceExchange:
    molar_flow_mol_s: float
    carried_energy_w: float
    moisture_entropy_w_k: float
    exact_molar_flow_mol_s: F
    exact_carried_energy_w: F
    exact_moisture_entropy_w_k: F
    rounded_rate_entropy_balance_w_k: F
    dry_density_kg_m3: F
    chemical_conductance_mol2_j_s: F
    mobility_mol2_k_j_s: F
    driving_force_j_mol_k: F
    numerical_projections: tuple[QuantityProjection, ...]
    source_ids: tuple[str, ...]
    _input_provenance_json: str = field(repr=False)
    material_qualified: bool = False
    training_eligible: bool = False
    source_state_binding_verified: bool = False

    def to_record(self) -> dict:
        return {'molar_flow_mol_s': self.molar_flow_mol_s, 'carried_energy_w': self.carried_energy_w,
            'moisture_entropy_w_k': self.moisture_entropy_w_k,
            'rounded_rate_entropy_balance_w_k': _rat(self.rounded_rate_entropy_balance_w_k),
            'numerical_projections': [item.to_record() for item in self.numerical_projections],
            'source_ids': list(self.source_ids), 'input_provenance': json.loads(self._input_provenance_json),
            'source_state_binding_verified': False, 'material_qualified': False, 'training_eligible': False,
            'conduction_included': False, 'additional_latent_source_w': 0,
            'entropy_scope': 'instantaneous nominal face and rounded-rate balance, not full step entropy proof',
            'errors': {name: None for name in ('D_experimental_uncertainty', 'temperature_extension',
                'moisture_extension', 'pressure_extension', 'cross_material_transfer',
                'cross_effect_model', 'total_model_uncertainty')}}


def sorption_moisture_face(left: CondensedWaterPoint, right: CondensedWaterPoint,
                          geometry: MoistureFaceGeometry, diffusivity: EffectiveMoistureDiffusivity,
                          factor: MoistureThermodynamicFactor) -> MoistureFaceExchange:
    """Return one shared left-to-right molar/energy flux using the declared closure."""
    for value, cls in ((left, CondensedWaterPoint), (right, CondensedWaterPoint),
                       (geometry, MoistureFaceGeometry), (diffusivity, EffectiveMoistureDiffusivity),
                       (factor, MoistureThermodynamicFactor)):
        _require(type(value) is cls, 'explicit_moisture_face_records_required')
    # Revalidate copies without mutating caller records; no external identity is authenticated.
    left, right, geometry, diffusivity, factor = (
        replace(value) for value in (left, right, geometry, diffusivity, factor))
    for point in (left, right):
        _require(F(308.15) <= point.temperature_k <= F(368.15), 'moisture_face_temperature_domain')
        _require(F(.30) <= point.moisture_kg_water_per_kg_dry <= F(.80), 'moisture_face_moisture_domain')
        _require(90000 <= point.pressure_pa <= 110000, 'moisture_face_pressure_domain')
        _require(point.water_molar_mass_kg_mol > 0, 'positive_water_molar_mass_required')
    _require(left.energy_reference_id == right.energy_reference_id, 'moisture_face_energy_reference_mismatch')
    _require(left.water_molar_mass_kg_mol == right.water_molar_mass_kg_mol, 'moisture_face_molar_mass_mismatch')
    rho = geometry.left_dry_mass_kg/geometry.left_total_volume_m3
    _require(rho == geometry.right_dry_mass_kg/geometry.right_total_volume_m3,
             'moisture_face_uniform_dry_density_required')
    tf = (left.temperature_k+right.temperature_k)/2
    interval = tuple(sorted((left.moisture_kg_water_per_kg_dry, right.moisture_kg_water_per_kg_dry)))
    method = 'declared_same_W_limit' if interval[0] == interval[1] else 'declared_secant'
    _require(factor.gamma_j_mol > 0, 'positive_thermodynamic_factor_required')
    _require(factor.temperature_k == tf and factor.moisture_interval == interval and factor.method == method,
             'thermodynamic_factor_state_correspondence')
    conductance = geometry.area_m2*rho*diffusivity.value_m2_s/(
        left.water_molar_mass_kg_mol*geometry.center_distance_m*factor.gamma_j_mol)
    mobility = tf*conductance
    hf = (left.partial_molar_enthalpy_j_mol+right.partial_molar_enthalpy_j_mol)/2
    xt = 1/right.temperature_k-1/left.temperature_k
    xmu = left.chemical_potential_j_mol/left.temperature_k-right.chemical_potential_j_mol/right.temperature_k
    drive = xmu+hf*xt
    n, carried, entropy = mobility*drive, hf*mobility*drive, mobility*drive*drive
    quantities = (('dry_density_kg_m3', rho), ('factor_gamma_j_mol', factor.gamma_j_mol),
        ('face_temperature_k', tf), ('chemical_conductance_mol2_j_s', conductance),
        ('mobility_mol2_k_j_s', mobility), ('face_enthalpy_j_mol', hf),
        ('inverse_temperature_difference_1_k', xt), ('chemical_force_j_mol_k', xmu),
        ('driving_force_j_mol_k', drive), ('molar_flow_mol_s', n),
        ('carried_energy_w', carried), ('moisture_entropy_w_k', entropy))
    projections = tuple(QuantityProjection(name, value, projected, abs(F(projected)-value))
                        for name, value in quantities for projected in (_project(value, name),))
    n_float, h_float, s_float = (item.binary64 for item in projections[-3:])
    rounded_entropy = F(h_float)*xt+F(n_float)*xmu
    _require(rounded_entropy >= 0, 'rounded_moisture_entropy_negative')
    _require(entropy == 0 or rounded_entropy > 0, 'rounded_moisture_entropy_unresolved')
    provenance = {'left': left.to_record(), 'right': right.to_record(), 'geometry': geometry.to_record(),
        'diffusivity': diffusivity.to_record(), 'thermodynamic_factor': factor.to_record(),
        'reference_scope': 'equal caller-declared energy reference and water molar mass; actual provider binding absent',
        'closure': 'arithmetic T/h; zero heat-moisture cross coefficients in Q,n representation assumed',
        'inventory_path': 'same condensed-water inventory; no extra sorbed inventory; no parallel gas transport authenticated'}
    source_ids = tuple(sorted(set(left.source_ids+right.source_ids+geometry.source_ids+
                                  diffusivity.source_ids+factor.source_ids+(MODEL_ID,))))
    return MoistureFaceExchange(n_float, h_float, s_float, n, carried, entropy, rounded_entropy,
        rho, conductance, mobility, drive, projections, source_ids,
        json.dumps(provenance, sort_keys=True, separators=(',', ':')))
