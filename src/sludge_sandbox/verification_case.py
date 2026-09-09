"""Explicit manufactured verification cases; parsing never imports an EOS.

The case file is evidence of declared manufactured inputs, not material data.
Only build_case/snapshot initialize or evaluate the source-qualified providers.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass, replace
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
from typing import Any


class CaseError(ValueError):
    def __init__(self, message: str, code: str = 'invalid_case') -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class CaseDefinition:
    _payload_json: str
    sha256: str
    path: Path
    case_id: str

    @property
    def payload(self) -> dict[str, Any]:
        """A detached copy; callers cannot mutate the validated definition."""
        return json.loads(self._payload_json)


@dataclass(frozen=True)
class BuiltCase:
    case: CaseDefinition
    operator: Any
    initial: Any
    start_s: float
    end_s: float
    policy: Any
    initialization: dict[str, Any]
    depletion_policy: Any = None


# Exact key sets make misspelled or unsupported settings errors, never defaults.
_KEYS = {
    '': 'schema case_id model_id classification material_qualified training_eligible scope grid profile transport_mode refinement water constants solid carrier reaction mechanics transport initial numerics',
    'grid': 'cells half_thickness_m reference_face_area_m2 parent_cells parent_bulk_volume_error_m3',
    'water': 'classification backend manifest liquid_pressure_model pressure_range_pa',
    'constants': 'gas_constant_j_mol_k gas_constant_source_id',
    'solid': 'classification crystal_phase_id caloric_temperature_range_k molar_mass_kg_mol reference_pressure_pa pressure_range_pa declared_u_error_j_mol declared_v_error_m3_mol A B',
    'solid/A': 'coefficients formation_enthalpy_298_j_mol molar_volume_m3_mol',
    'solid/B': 'coefficients formation_enthalpy_298_j_mol molar_volume_m3_mol',
    'carrier': 'classification species_id temperature_range_k coefficients formation_enthalpy_298_j_mol molar_mass_kg_mol segment_index',
    'reaction': 'classification reaction_id stoichiometry elements_per_species prefactor_mol_m3_s activation_energy_j_mol concentration_reference_mol_m3 concentration_basis orders temperature_range_k reaction_regime',
    'reaction/stoichiometry': 'A B', 'reaction/elements_per_species': 'A B',
    'reaction/elements_per_species/A': 'C', 'reaction/elements_per_species/B': 'C', 'reaction/orders': 'A',
    'mechanics': 'classification knot_times_s normal_stretches_at_knots tangential_stretches_at_knots bulk_modulus_pa shear_modulus_pa viscosity_pa_s interface_energy_j_m2 micro_interface_area_density_m2_m3 composition_offset composition_beta_m3_mol stretch_range maximum_absolute_log_rate_per_s additional_bulk_volume_error_m3 additional_mechanical_energy_error_j',
    'mechanics/composition_beta_m3_mol': 'A B',
    'transport': 'classification coupled_conductivity_w_m_k control_conductivity_w_m_k coupled_water_diffusivity_m2_s control_water_diffusivity_m2_s carrier_diffusivity_m2_s permeability_m2 relative_permeability viscosity_pa_s phase_coefficient_density_mol_s_pa_m3 outer_reservoir outer_surface_temperature_k liquid_transport interfaces',
    'initial': 'species_order parent_amounts_mol parent_temperatures_k energy_initialization',
    'numerics': 'start_s end_s temperature_bracket_k pressure_policy inverse_policy envelope integration',
    'numerics/pressure_policy': 'volume_absolute_m3 pressure_absolute_pa maximum_iterations',
    'numerics/inverse_policy': 'energy_absolute_j temperature_absolute_k maximum_iterations',
    'numerics/envelope': 'liquid_u_error_j_mol liquid_v_error_m3_mol liquid_abs_du_dp_bound_j_mol_pa gas_u_error_j_mol gas_cv_lower_j_mol_k method',
    'numerics/envelope/gas_u_error_j_mol': 'fixture H2O', 'numerics/envelope/gas_cv_lower_j_mol_k': 'fixture H2O',
    'numerics/integration': 'initial_step_s maximum_step_s minimum_step_s relative_tolerance amount_absolute_tolerance_mol energy_absolute_tolerance_j amount_scale_mol energy_scale_j maximum_steps maximum_rejections maximum_wall_seconds',
}


_FREE_MODEL = 'manufactured_reacting_wet_free_slab_v1'
_EVENT_SCHEMA = 'sludge_sandbox_free_event_case_v1'
_EXACT_EVENT_SCHEMA = 'sludge_sandbox_free_exact_event_case_v1'
_DEPLETION_KEYS = 'schema time_absolute_s amount_absolute_mol energy_absolute_j temperature_absolute_k pressure_absolute_pa terminal_window_s maximum_refinements roundoff_policy common_time_horizon_s safe_inventory_fraction nested_approach terminal_method'
_ROUNDOFF_KEYS = 'correction_absolute_mol correction_fraction_evaporated storage_absolute_mol cumulative_storage_absolute_mol element_absolute_mol cumulative_element_absolute_mol mass_absolute_kg cumulative_mass_absolute_kg cumulative_correction_absolute_mol molar_mass_kg_mol'

_FREE_MECHANICS = (_KEYS['mechanics'].split())
_FREE_MECHANICS = ' '.join(k for k in _FREE_MECHANICS if k not in (
    'knot_times_s','normal_stretches_at_knots','tangential_stretches_at_knots',
    'additional_bulk_volume_error_m3','additional_mechanical_energy_error_j')) + (
    ' initial_parent_normal_stretches initial_tangential_stretch external_pressure_pa'
    ' parent_additional_bulk_volume_error_m3 parent_additional_mechanical_energy_error_j')


def _free_normals(payload: dict[str, Any], cells: int) -> tuple[float, ...]:
    parent = payload['mechanics']['initial_parent_normal_stretches']
    return tuple(float(parent[0 if payload['profile']=='uniform' else i//(cells//2)]) for i in range(cells))


def _require(condition: bool, message: str, code: str = 'invalid_case') -> None:
    if not condition:
        raise CaseError(message, code)


def _at(payload: dict[str, Any], pointer: str) -> Any:
    value: Any = payload
    for part in pointer.split('/') if pointer else ():
        value = value[part]
    return value


def _number(value: Any, label: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    _require(type(value) in (int, float), 'number required: '+label)
    try:
        number = float(value)
    except OverflowError as exc:
        raise CaseError('number outside binary64: '+label) from exc
    _require(math.isfinite(number) and not (number == 0 and value != 0), 'finite representable number required: '+label)
    _require(not positive or number > 0, 'positive number required: '+label)
    _require(not nonnegative or number >= 0, 'nonnegative number required: '+label)
    return number


def _range(value: Any, label: str) -> tuple[float, float]:
    _require(type(value) is list and len(value) == 2, 'two endpoints required: '+label)
    lo, hi = (_number(item, label) for item in value)
    _require(lo < hi, 'ordered endpoints required: '+label)
    return lo, hi


def _validate(p: dict[str, Any]) -> None:
    _require(type(p) is dict, 'case must be a JSON object')
    _require(set(p) == set(_KEYS[''].split()), 'exact top-level case keys required')
    def finite_tree(value: Any, pointer: str = '') -> None:
        if type(value) is bool:
            _require(pointer in ('/material_qualified', '/training_eligible') or
                     (p.get('schema') in (_EVENT_SCHEMA,_EXACT_EVENT_SCHEMA) and p.get('model_id') == _FREE_MODEL and
                      pointer == '/numerics/depletion/nested_approach/reuse_ordinary_spine'),
                     'boolean is not a physical number: '+pointer)
        elif type(value) in (int, float):
            _number(value, pointer)
        elif type(value) is dict:
            for key, child in value.items():
                finite_tree(child, pointer+'/'+key)
        elif type(value) is list:
            for index, child in enumerate(value):
                finite_tree(child, pointer+'/'+str(index))
    finite_tree(p)
    if p.get('classification') != 'manufactured_verification' or p.get('material_qualified') is not False or p.get('training_eligible') is not False:
        raise CaseError('Real material or training eligibility is not evidenced by this verification model', 'evidence_incomplete')
    event = p.get('schema') in (_EVENT_SCHEMA,_EXACT_EVENT_SCHEMA)
    _require((p.get('schema') == 'sludge_sandbox_verification_case_v1' and
              p.get('model_id') in ('manufactured_reacting_wet_prescribed_slab_v1', _FREE_MODEL)) or
             (event and p.get('model_id') == _FREE_MODEL), 'unsupported schema/model', 'unsupported_model')
    free = p['model_id'] == _FREE_MODEL
    keys = dict(_KEYS)
    numerics_object = p.get('numerics')
    pressure = numerics_object.get('pressure_policy', {}) if isinstance(numerics_object, dict) else {}
    if isinstance(pressure, dict) and 'strategy' in pressure:
        keys['numerics/pressure_policy'] += ' strategy'
    if free:
        keys['mechanics'] = _FREE_MECHANICS
        keys['numerics/integration'] += ' stretch_absolute_tolerance stretch_scale'
    if event:
        keys['numerics'] += ' depletion'
        keys['numerics/depletion'] = _DEPLETION_KEYS
        if isinstance(p['numerics']['depletion'],dict) and p['numerics']['depletion'].get('schema') in ('sandbox_depletion_policy_v2','sandbox_exact_depletion_policy_v1'):
            keys['numerics/depletion'] += ' pressure_comparison'
        if p.get('schema')==_EXACT_EVENT_SCHEMA:
            keys['numerics/depletion'] += ' ordered_event_policy'
            _require(p['numerics']['depletion'].get('schema')=='sandbox_exact_depletion_policy_v1','explicit exact depletion policy required')
        else:
            _require(p['numerics']['depletion'].get('schema')!='sandbox_exact_depletion_policy_v1','exact policy requires exact case schema')
        keys['numerics/depletion/roundoff_policy'] = _ROUNDOFF_KEYS
    for pointer, names in keys.items():
        try:
            value = _at(p, pointer)
        except (KeyError, TypeError) as exc:
            raise CaseError('missing object: /'+pointer) from exc
        _require(type(value) is dict and set(value) == set(names.split()), 'exact keys required: /'+pointer)
    if event:
        _build_depletion_policy(p['numerics']['depletion'],validation_only=True)
    _require(type(p['case_id']) is str and bool(p['case_id']) and p['case_id'].strip() == p['case_id'], 'nonempty case_id required')
    _require(type(p['scope']) is str and bool(p['scope'].strip()), 'scope required')
    for name, classification in [('solid', 'manufactured_test_fixture'), ('carrier', 'manufactured_test_fixture'),
                                 ('reaction', 'manufactured'), ('mechanics', 'manufactured_test_fixture'), ('transport', 'manufactured')]:
        _require(p[name]['classification'] == classification, 'unsupported material classification: '+name, 'evidence_incomplete')
    grid, water, solid, carrier = (p[key] for key in ('grid', 'water', 'solid', 'carrier'))
    _require(type(grid['cells']) is int and grid['cells'] in ((2, 4, 8) if free else (2, 4)) and type(grid['parent_cells']) is int and grid['parent_cells'] == 2, 'only fixed-domain two/four prescribed or two/four/eight free cells supported', 'unsupported_model')
    _require(_number(grid['half_thickness_m'], 'grid/half_thickness_m', positive=True) == .02 and
             _number(grid['reference_face_area_m2'], 'grid/reference_face_area_m2', positive=True) == .01,
             'this verification model has fixed .02 m/.01 m2 domain', 'unsupported_model')
    _require(_number(grid['parent_bulk_volume_error_m3'], 'bulk error', nonnegative=True) < .0001, 'bulk error exceeds parent volume')
    _require(p['profile'] in ('gradient', 'uniform') and p['transport_mode'] in ('coupled', 'control'), 'unsupported profile/transport mode', 'unsupported_model')
    _require(type(p['refinement']) is int and p['refinement'] in (0, 1), 'only two registered time caps supported')
    _require(water['classification'] == 'source_qualified' and water['backend'] == 'heos' and water['manifest'] == 'heos-8.0.0-approved-manifest.json', 'unsupported water selection', 'unsupported_model')
    _require(water['liquid_pressure_model'] == 'planar_interface_no_capillary_pressure', 'unsupported liquid pressure model', 'unsupported_model')
    pressure = _range(water['pressure_range_pa'], 'water pressure')
    _require(0 < pressure[0] < pressure[1] <= 1e8, 'water pressure domain')
    r = _number(p['constants']['gas_constant_j_mol_k'], 'gas constant', positive=True)
    _require(r == 8.31446261815324 and p['constants']['gas_constant_source_id'] == 'nist-codata-2022', 'unsupported gas constant provenance', 'evidence_incomplete')
    solid_t, carrier_t = _range(solid['caloric_temperature_range_k'], 'solid T'), _range(carrier['temperature_range_k'], 'carrier T')
    _require(solid['crystal_phase_id'] == 'manufactured_single_phase' and carrier['species_id'] == 'fixture', 'unsupported phase/species identity', 'unsupported_model')
    ps = _range(solid['pressure_range_pa'], 'solid pressure')
    pref = _number(solid['reference_pressure_pa'], 'solid reference pressure', positive=True)
    _require(0 < ps[0] <= pressure[0] < pressure[1] <= ps[1] and ps[0] <= pref <= ps[1], 'solid pressure coverage')
    _number(solid['molar_mass_kg_mol'], 'solid mass', positive=True)
    uerror = _number(solid['declared_u_error_j_mol'], 'solid uerror', nonnegative=True)
    verror = _number(solid['declared_v_error_m3_mol'], 'solid verror', nonnegative=True)
    _require(Fraction(uerror) >= Fraction(pref)*Fraction(verror), 'solid energy error omits pressure-volume reference term')
    for name in ('A', 'B'):
        item = solid[name]
        coefficients = item['coefficients']
        _require(type(coefficients) is list and len(coefficients) == 8, 'eight solid coefficients required')
        values = [_number(value, name+' coefficient') for value in coefficients]
        _require(values[0] > 0 and all(values[i] == 0 for i in (1, 2, 3, 4, 6)), 'only declared constant-Cp solid verification supported', 'unsupported_model')
        hf = _number(item['formation_enthalpy_298_j_mol'], name+' formation enthalpy')
        _require(values[5] == values[7] == hf/1000, 'solid reference coefficients must match formation enthalpy')
        _number(item['molar_volume_m3_mol'], name+' volume', positive=True)
    cc = carrier['coefficients']
    _require(type(cc) is list and len(cc) == 8, 'eight carrier coefficients required')
    cv = [_number(value, 'carrier coefficient') for value in cc]
    _require(cv[0] > r and all(value == 0 for value in cv[1:]), 'constant-Cp zero-reference carrier required', 'unsupported_model')
    _require(_number(carrier['formation_enthalpy_298_j_mol'], 'carrier formation') == 0, 'carrier reference must be zero')
    _number(carrier['molar_mass_kg_mol'], 'carrier mass', positive=True)
    _require(type(carrier['segment_index']) is int and carrier['segment_index'] == 0, 'one original carrier caloric segment required')
    rx = p['reaction']
    _require(rx['reaction_id'] == 'A-to-B' and rx['stoichiometry'] == {'A': -1, 'B': 1} and rx['orders'] == {'A': 1} and
             rx['elements_per_species'] == {'A': {'C': 1}, 'B': {'C': 1}}, 'only explicit manufactured A-to-B supported', 'unsupported_model')
    _require(rx['concentration_basis'] == 'current_cell_bulk_volume' and rx['reaction_regime'] == 'oxygen_free_pyrolysis', 'unsupported reaction formulation', 'unsupported_model')
    for key in ('prefactor_mol_m3_s', 'concentration_reference_mol_m3'):
        _number(rx[key], key, positive=True)
    _require(_number(rx['activation_energy_j_mol'], 'activation energy') == 0, 'thermal activation not included in this verification case', 'unsupported_model')
    rt = _range(rx['temperature_range_k'], 'reaction T')
    mech = p['mechanics']
    stretch = _range(mech['stretch_range'], 'stretch bounds')
    _require(stretch[0] > 0, 'positive stretch range')
    if free:
        normals=mech['initial_parent_normal_stretches']
        _require(type(normals) is list and len(normals)==2,'two parent normal stretches required')
        for value in normals+[mech['initial_tangential_stretch']]:
            _require(stretch[0]<=_number(value,'initial stretch',positive=True)<=stretch[1],'initial stretch outside domain')
        _number(mech['external_pressure_pa'],'external pressure',nonnegative=True)
        for key in ('bulk_modulus_pa','shear_modulus_pa','composition_offset','maximum_absolute_log_rate_per_s','viscosity_pa_s'):
            _number(mech[key],key,positive=True)
        for key in ('interface_energy_j_m2','micro_interface_area_density_m2_m3','parent_additional_bulk_volume_error_m3','parent_additional_mechanical_energy_error_j'):
            _number(mech[key],key,nonnegative=True)
    else:
        knots = _range(mech['knot_times_s'], 'motion knots')
        stretch = _range(mech['stretch_range'], 'stretch bounds')
        _require(stretch[0] > 0, 'positive stretch range')
        for key in ('normal_stretches_at_knots', 'tangential_stretches_at_knots'):
            _require(type(mech[key]) is list and len(mech[key]) == 2, 'two motion stretches required')
            for value in mech[key]:
                _require(stretch[0] <= _number(value, key, positive=True) <= stretch[1], 'motion outside stretch range')
        for key in ('bulk_modulus_pa', 'shear_modulus_pa', 'composition_offset', 'maximum_absolute_log_rate_per_s'):
            _number(mech[key], key, positive=True)
        for key in ('normal_stretches_at_knots', 'tangential_stretches_at_knots'):
            left, right = map(float, mech[key])
            log_rate_enclosure = 1.5*abs(right-left)/((knots[1]-knots[0])*min(left, right))
            _require(log_rate_enclosure <= mech['maximum_absolute_log_rate_per_s'], 'declared log rate does not cover motion')
        for key in ('viscosity_pa_s', 'interface_energy_j_m2', 'micro_interface_area_density_m2_m3', 'additional_bulk_volume_error_m3', 'additional_mechanical_energy_error_j'):
            _number(mech[key], key, nonnegative=True)
    for value in mech['composition_beta_m3_mol'].values():
        _number(value, 'composition beta', nonnegative=True)
    transport = p['transport']
    for key in ('coupled_conductivity_w_m_k', 'coupled_water_diffusivity_m2_s', 'phase_coefficient_density_mol_s_pa_m3', 'viscosity_pa_s'):
        _number(transport[key], key, positive=not (free and key=='phase_coefficient_density_mol_s_pa_m3'), nonnegative=free and key=='phase_coefficient_density_mol_s_pa_m3')
    for key in ('control_conductivity_w_m_k', 'control_water_diffusivity_m2_s', 'carrier_diffusivity_m2_s', 'permeability_m2'):
        _require(_number(transport[key], key) == 0, 'unsupported nonzero transport branch: '+key, 'unsupported_model')
    _require(_number(transport['relative_permeability'], 'relative permeability') == 1, 'relative permeability must be1')
    _require(all(transport[key] is None for key in ('outer_reservoir', 'outer_surface_temperature_k', 'liquid_transport')) and
             transport['interfaces'] == 'existing_liquid', 'unsupported boundary/interface physics', 'unsupported_model')
    initial, numerics = p['initial'], p['numerics']
    _require(initial['species_order'] == ['A', 'B', 'H2O', 'H2O_liquid', 'fixture'] and initial['energy_initialization'] == 'conservative_parent_prolongation_with_forward_storage_check', 'unsupported initial formulation', 'unsupported_model')
    _require(type(initial['parent_amounts_mol']) is list and len(initial['parent_amounts_mol']) == 2, 'two parent rows required')
    for row in initial['parent_amounts_mol']:
        _require(type(row) is list and len(row) == 5, 'five species required')
        for index, value in enumerate(row):
            _number(value, 'initial inventory', nonnegative=True)
            _require((index in (1,2,3) if free else index == 1) or value > 0, 'positive initial A/water/carrier required')
        _require(row[1] == 0, 'initial B must be zero for this verification reference')
        volume = sum(Fraction(float(row[i]))*Fraction(float(solid[name]['molar_volume_m3_mol'])) for i, name in ((0, 'A'), (1, 'B')))
        _require(volume < Fraction(.0001), 'solid inventory exceeds parent bulk volume')
    bracket = _range(numerics['temperature_bracket_k'], 'inverse bracket')
    _require(293 <= bracket[0] < bracket[1] <= 500 and all(bounds[0] <= bracket[0] < bracket[1] <= bounds[1] for bounds in (solid_t, carrier_t, rt)), 'temperature coverage incomplete')
    _require(type(initial['parent_temperatures_k']) is list and len(initial['parent_temperatures_k']) == 2, 'two parent temperatures required')
    for value in initial['parent_temperatures_k']:
        _require(bracket[0] <= _number(value, 'initial T') <= bracket[1], 'initial T outside declared domains')
    start, end = _number(numerics['start_s'], 'start'), _number(numerics['end_s'], 'end')
    _require(start < end if free else knots[0] <= start < end <= knots[1], 'invalid time domain')
    for group in ('pressure_policy', 'inverse_policy', 'integration'):
        for key, value in numerics[group].items():
            if group == 'pressure_policy' and key == 'strategy':
                _require(type(value) is str and value == 'guarded_liquid_endpoint_interpolation_v1',
                         'unsupported explicit pressure strategy')
            elif key in ('maximum_iterations', 'maximum_steps', 'maximum_rejections'):
                _require(type(value) is int and value > 0, 'positive integer required: '+key)
            else:
                _number(value, key, positive=True)
    ip = numerics['integration']
    _require(ip['minimum_step_s'] <= ip['initial_step_s']/2**p['refinement'] <= ip['maximum_step_s']/2**p['refinement'] <= end-start, 'inconsistent time step policy')
    env = numerics['envelope']
    _require(env['method'] == 'explicit_manufactured_numerical_verification_envelope_not_eos_certificate', 'unsupported numerical envelope', 'unsupported_model')
    for key in ('liquid_u_error_j_mol', 'liquid_v_error_m3_mol', 'liquid_abs_du_dp_bound_j_mol_pa'):
        _number(env[key], key, nonnegative=True)
    for value in env['gas_u_error_j_mol'].values():
        _number(value, 'gas uerror', nonnegative=True)
    for value in env['gas_cv_lower_j_mol_k'].values():
        _number(value, 'gas cv lower', positive=True)
    _require(env['gas_cv_lower_j_mol_k']['fixture'] <= cv[0]-r, 'carrier cv lower exceeds constant curve')


def _build_depletion_policy(record: dict[str, Any], *, operator: Any = None, validation_only: bool = False) -> Any:
    """Construct a fully explicit numerical policy; imports make no EOS calls."""
    from .depletion_integration import DepletionPolicy, NestedApproachPolicy
    from .depletion_roundoff import DepletionRoundoffPolicy
    _require(type(record) is dict,'depletion policy object required')
    exact=record.get('schema')=='sandbox_exact_depletion_policy_v1'
    paired=exact or record.get('schema')=='sandbox_depletion_policy_v2'
    expected=set(_DEPLETION_KEYS.split()) | ({'pressure_comparison'} if paired else set()) | ({'ordered_event_policy'} if exact else set())
    _require(set(record)==expected,'exact depletion policy keys required')
    _require(record['schema'] in ('sandbox_depletion_policy_v1','sandbox_depletion_policy_v2','sandbox_exact_depletion_policy_v1'), 'unsupported depletion policy schema')
    _require(record['terminal_method'] == 'affine_midpoint', 'event case requires affine_midpoint')
    for key in ('time_absolute_s','amount_absolute_mol','energy_absolute_j','temperature_absolute_k',
                'pressure_absolute_pa','terminal_window_s','common_time_horizon_s','safe_inventory_fraction'):
        _number(record[key], 'depletion/'+key, positive=True)
    _require(type(record['maximum_refinements']) is int and record['maximum_refinements'] >= 2, 'at least two event refinements required')
    rounding = record['roundoff_policy']
    _require(type(rounding) is dict and set(rounding) == set(_ROUNDOFF_KEYS.split()), 'exact roundoff policy keys required')
    for key,value in rounding.items():
        _number(value, 'roundoff/'+key, positive=True)
    nested = record['nested_approach']
    if nested is not None:
        _require(type(nested) is dict and set(nested) == {'maximum_step_s','reuse_ordinary_spine','strategy_id'}, 'exact nested approach keys required')
        _number(nested['maximum_step_s'], 'nested maximum step', positive=True)
        _require(type(nested['reuse_ordinary_spine']) is bool and nested['strategy_id']=='nested_wet_ordinary_spine_v1', 'explicit nested approach strategy required')
    if exact:
        _require(record['ordered_event_policy']=='ordered_affine_packet_v1' and nested is not None and nested['reuse_ordinary_spine'] is False,'explicit exact ordered nested policy required')
    try:
        values = {key:value for key,value in record.items() if key not in ('schema','roundoff_policy','nested_approach')}
        if paired and not (exact and record['pressure_comparison'] is None):
            from .pressure_comparison import PressureComparisonPolicy, SCHEMA
            from .paired_pressure_host import declare_manufactured_constant_box
            declaration=record['pressure_comparison']
            _require(type(declaration) is dict and declaration=={
                'schema':SCHEMA,'constant_box_declaration':'all_actual_declared_constant_volume_errors_are_shared'},
                'explicit shared constant parameter declaration required')
            _require(operator is not None or validation_only,'actual operator required to bind comparison boxes')
            values['pressure_comparison']=(None if operator is None else PressureComparisonPolicy(tuple(
                declare_manufactured_constant_box(point) for point in operator.base_model.point_storages)))
        return DepletionPolicy(**values, roundoff_policy=DepletionRoundoffPolicy(**rounding),
            nested_approach=None if nested is None else NestedApproachPolicy(**nested))
    except ValueError as exc:
        raise CaseError('invalid depletion policy: '+str(exc)) from exc


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate JSON key: '+key)
        result[key] = value
    return result


def _constant(value: str) -> Any:
    raise CaseError('nonfinite JSON constant: '+value)


def read_case(path: str | Path) -> CaseDefinition:
    location = Path(path).resolve()
    try:
        raw = location.read_bytes()
        payload = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
        _validate(payload)
    except CaseError:
        raise
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise CaseError('cannot read/validate case: '+str(exc)) from exc
    return CaseDefinition(json.dumps(payload, allow_nan=False), hashlib.sha256(raw).hexdigest(), location, payload['case_id'])


def encode(value: Any) -> Any:
    """Map model records to JSON without importing optional numerical packages."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        _require(math.isfinite(value), 'nonfinite output cannot be encoded')
        return value
    if isinstance(value, Fraction):
        return {'numerator': value.numerator, 'denominator': value.denominator}
    if is_dataclass(value):
        return {item.name: encode(getattr(value, item.name)) for item in fields(value)
                if not (item.metadata.get('omit_when_none',False) and getattr(value,item.name) is None)}
    if isinstance(value, Mapping):
        return {str(key): encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(item) for item in value]
    if type(value).__module__.startswith('numpy'):
        if hasattr(value, 'tolist'):
            return encode(value.tolist())
        return encode(value.item())
    raise CaseError('unsupported output type: '+type(value).__name__)


def _make_model(case: CaseDefinition, water_dir: Path, cells: int) -> tuple[Any, list[list[float]], list[float]]:
    # Deliberately lazy: source tracing/read_case requires only the standard library.
    from .water_properties import load_water_properties
    from .ideal_water_vapor import IdealWaterVapor
    from .water_chemical_potential import WaterChemicalPotential
    from .thermochemistry import ShomateGas, ShomateSegment
    from .phase_storage import IdealGasPhase, InversePolicy
    from .rigid_water_gas import RigidWaterGas, PressurePolicy
    from .rigid_storage import RigidStorage, DeclaredNumericalEnvelope
    from .rigid_fluid_heat import RigidFluidHeat
    from .incompressible_solid import SolidShomateCaloric, IncompressibleSolidPhase
    from .solid_fluid_storage import SolidFluidStorage
    from .solid_fluid_heat import InventoryLayout, SolidFluidHeat
    from .solid_reactions import SolidReactionConfig, ReactionSpeciesBinding
    from .reactions import SpeciesDefinition, ReactionDefinition, ReactionNetwork, ArrheniusMassAction
    from .geometry import ReferenceSlab
    from .deformation_program import PrescribedSlabMotion
    from .skeleton_energy import DiagonalSkeletonEnergy
    from .reacting_skeleton_energy import ManufacturedReactingSkeletonEnergy
    from .deforming_solid_storage import DeformingSolidStorage, DeformationErrorBounds, solid_provider_identity
    from .deforming_solid_heat import DeformingSolidHeat
    from .current_solid_storage import CurrentSolidStorage
    from .dynamic_solid_storage import DynamicStorageErrorBounds
    from .free_solid_slab import FreeSolidSlab
    from .water_phase_transfer import WaterPhaseTransfer

    p = case.payload
    source = (f'manufactured:{case.case_id}:sha256:{case.sha256}',)
    assets = (('case.json', case.sha256),)
    water_config, grid, n = p['water'], p['grid'], p['numerics']
    selection = dict(backend=water_config['backend'], backend_manifest=water_dir/water_config['manifest'])
    water = load_water_properties(water_dir, **selection)
    vapor = IdealWaterVapor(water_dir, **selection)
    chemical = WaterChemicalPotential(water_dir, **selection)
    gas_r = p['constants']['gas_constant_j_mol_k']
    c = p['carrier']
    curve = ShomateGas(c['species_id'], (ShomateSegment(tuple(c['temperature_range_k']),
        tuple(c['coefficients']), c['formation_enthalpy_298_j_mol'], gas_r, source),), c['classification'], source)
    gases = {'fixture': IdealGasPhase(curve, c['molar_mass_kg_mol'], c['segment_index'], source),
             'H2O': IdealGasPhase(vapor, vapor.molar_mass_kg_mol)}
    volume = grid['half_thickness_m']*grid['reference_face_area_m2']/cells
    scale = grid['parent_cells']/cells
    pressure_policy = n['pressure_policy']
    mechanical = RigidWaterGas(water, ('fixture', 'H2O'), volume, tuple(water_config['pressure_range_pa']),
        water_config['liquid_pressure_model'], PressurePolicy(pressure_policy['volume_absolute_m3'],
        pressure_policy['pressure_absolute_pa'], pressure_policy['maximum_iterations'],
        strategy=pressure_policy.get('strategy')))
    envelope = DeclaredNumericalEnvelope(tuple(n['temperature_bracket_k']), tuple(water_config['pressure_range_pa']),
        **n['envelope'], source_ids=source)
    fluid = RigidStorage(mechanical=mechanical, gas_phases=gases, envelope=envelope, allow_manufactured=True)
    tr = p['transport']
    mode = p['transport_mode']
    transport = RigidFluidHeat(storages=(fluid,)*cells, gas_species_order=('fixture', 'H2O'), liquid_column_id='H2O_liquid',
        face_area_m2=grid['reference_face_area_m2'], cell_widths_m=(grid['half_thickness_m']/cells,)*cells,
        conductivities_w_m_k=(tr[mode+'_conductivity_w_m_k'],)*cells,
        effective_diffusivities_m2_s={'fixture': (tr['carrier_diffusivity_m2_s'],)*cells,
                                    'H2O': (tr[mode+'_water_diffusivity_m2_s'],)*cells},
        permeability_m2=(tr['permeability_m2'],)*cells, relative_permeability=(tr['relative_permeability'],)*cells,
        viscosity_pa_s=(tr['viscosity_pa_s'],)*cells, temperature_brackets_k=(tuple(n['temperature_bracket_k']),)*cells,
        inverse_policy=InversePolicy(n['inverse_policy']['energy_absolute_j'], n['inverse_policy']['temperature_absolute_k'],
                                     n['inverse_policy']['maximum_iterations']), outer_reservoir=tr['outer_reservoir'],
        outer_surface_temperature_k=tr['outer_surface_temperature_k'], coefficient_set_id=source[0]+':transport:'+mode,
        coefficient_version='1', coefficient_classification=tr['classification'], coefficient_source_ids=source,
        allow_manufactured=True)
    s = p['solid']
    solids = {}
    for name in ('A', 'B'):
        caloric = SolidShomateCaloric(species_id=name, crystal_phase_id=s['crystal_phase_id'],
            temperature_range_k=tuple(s['caloric_temperature_range_k']), coefficients=tuple(s[name]['coefficients']),
            formation_enthalpy_298_j_mol=s[name]['formation_enthalpy_298_j_mol'], dataset_id=source[0]+':caloric:'+name,
            version='1', classification=s['classification'], source_ids=source, source_asset_sha256=assets)
        solids[name] = IncompressibleSolidPhase(caloric=caloric, molar_mass_kg_mol=s['molar_mass_kg_mol'],
            molar_volume_m3_mol=s[name]['molar_volume_m3_mol'], reference_pressure_pa=s['reference_pressure_pa'],
            pressure_range_pa=tuple(s['pressure_range_pa']), volume_model_id=source[0]+':constant-volume:'+name,
            volume_version='1', volume_classification=s['classification'], volume_source_ids=source,
            volume_source_asset_sha256=assets, declared_u_error_j_mol=s['declared_u_error_j_mol'],
            declared_v_error_m3_mol=s['declared_v_error_m3_mol'], error_method_id=source[0]+':declared-error',
            error_classification=s['classification'], error_source_ids=source, allow_manufactured=True)
    templates = tuple(SolidFluidStorage(fluid_template=fluid, solid_phases=solids, bulk_volume_m3=volume,
        bulk_volume_error_m3=grid['parent_bulk_volume_error_m3']*scale, geometry_id=source[0]+':bulk',
        geometry_version='1', geometry_classification='manufactured_test_fixture', geometry_source_ids=source,
        allow_manufactured=True) for _ in range(cells))
    layout = InventoryLayout(species_order=tuple(p['initial']['species_order']), liquid_column_id='H2O_liquid',
        gas_species_order=('fixture', 'H2O'), solid_species_order=('A', 'B'))
    rx = p['reaction']
    species = tuple(SpeciesDefinition(name, 'solid', rx['elements_per_species'][name], s['molar_mass_kg_mol'],
        source, rx['classification']) for name in ('A', 'B'))
    kinetics = ArrheniusMassAction(candidate_id=source[0]+':kinetics', version='1',
        prefactor_mol_m3_s=rx['prefactor_mol_m3_s'], activation_energy_j_mol=rx['activation_energy_j_mol'],
        concentration_reference_mol_m3=rx['concentration_reference_mol_m3'], concentration_basis=rx['concentration_basis'],
        orders=rx['orders'], temperature_range_k=tuple(rx['temperature_range_k']), gas_constant_j_mol_k=gas_r,
        constant_source_ids=(p['constants']['gas_constant_source_id'],), source_ids=source, classification=rx['classification'],
        prefactor_unit='mol/(m^3 s)', activation_energy_unit='J/mol', concentration_unit='mol/m^3', gas_constant_unit='J/(mol K)')
    reaction = ReactionDefinition(rx['reaction_id'], '1', rx['stoichiometry'], kinetics, rx['reaction_regime'], source)
    config = SolidReactionConfig(network=ReactionNetwork(species, (reaction,), allow_manufactured=True),
        bindings=tuple(ReactionSpeciesBinding(name, name, solids[name]) for name in ('A', 'B')),
        storages=templates, inventory_layout=layout, allow_manufactured=True, binding_id=source[0]+':binding',
        version='1', source_ids=source)
    base = SolidFluidHeat(storages=templates, inventory_layout=layout, transport=transport,
                          solid_reactions=config, liquid_transport=tr['liquid_transport'])
    m = p['mechanics']
    reference = ReferenceSlab(grid['half_thickness_m'], grid['reference_face_area_m2'], cells)
    free = p['model_id'] == _FREE_MODEL
    if not free:
        motion = PrescribedSlabMotion(reference=reference, knot_times_s=tuple(m['knot_times_s']),
            normal_stretches_at_knots=tuple((value,)*cells for value in m['normal_stretches_at_knots']),
            tangential_stretches_at_knots=tuple(m['tangential_stretches_at_knots']), motion_id=source[0]+':motion',
            version='1', classification=m['classification'], source_ids=source, source_asset_sha256=assets)
    parent_rows = [list(row) for row in p['initial']['parent_amounts_mol']]
    parent_t = list(p['initial']['parent_temperatures_k'])
    if p['profile'] == 'uniform':
        parent_rows[1], parent_t[1] = list(parent_rows[0]), parent_t[0]
    rows = [[value*scale for value in parent_rows[index//(cells//2)]] for index in range(cells)]
    temperatures = [parent_t[index//(cells//2)] for index in range(cells)]
    points = []
    for index, template in enumerate(templates):
        reference_skeleton = DiagonalSkeletonEnergy(reference=reference, cell_index=index,
            fixed_solid_inventory_mol=(('A', rows[index][0]), ('B', rows[index][1])),
            solid_provider_identity=solid_provider_identity(solids), bulk_modulus_pa=m['bulk_modulus_pa'],
            shear_modulus_pa=m['shear_modulus_pa'], viscosity_pa_s=m['viscosity_pa_s'],
            interface_energy_j_m2=m['interface_energy_j_m2'],
            reference_interface_area_m2=m['micro_interface_area_density_m2_m3']*volume,
            stretch_range=tuple(m['stretch_range']), maximum_absolute_log_rate_per_s=m['maximum_absolute_log_rate_per_s'],
            model_id=source[0]+':reference-skeleton', version='1', source_ids=source, classification=m['classification'],
            allow_manufactured=True)
        skeleton = ManufacturedReactingSkeletonEnergy(reference_model=reference_skeleton,
            composition_offset=m['composition_offset'], composition_weights_per_mol=tuple((name, m['composition_beta_m3_mol'][name]/volume) for name in ('A', 'B')),
            model_id=source[0]+':reacting-skeleton', version='1', classification=m['classification'], allow_manufactured=True)
        if free:
            points.append(CurrentSolidStorage(template=template,skeleton=skeleton,
                error_bounds=DynamicStorageErrorBounds(tuple(m['stretch_range']),tuple(m['stretch_range']),
                    m['parent_additional_bulk_volume_error_m3']*scale,m['parent_additional_mechanical_energy_error_j']*scale,
                    source,'conditional_declared_not_material_admission'),
                model_id=source[0]+':point',version='1',allow_manufactured=True,solid_inventory_regime='reacting_manufactured'))
        else:
            points.append(DeformingSolidStorage(template=template, motion=motion, skeleton=skeleton,
                error_bounds=DeformationErrorBounds(tuple(m['knot_times_s']), m['additional_bulk_volume_error_m3'],
                    m['additional_mechanical_energy_error_j'], source, 'conditional_declared_not_material_admission'),
                model_id=source[0]+':point', version='1', allow_manufactured=True))
    if free:
        host=FreeSolidSlab(base_model=base,point_storages=tuple(points),external_pressure_pa=m['external_pressure_pa'],
            mechanical_regime='reduced_common_tangent_quasistatic_reacting_manufactured',
            transport_regime='manufactured_relative_moving_faces',model_id=source[0]+':host',version='1',
            source_ids=source,allow_manufactured=True,solid_inventory_regime='reacting_manufactured')
    else:
        host = DeformingSolidHeat(base_model=base, point_storages=tuple(points),
            mechanical_regime='prescribed_cellwise_quasistatic_incompressible_skeleton',
            transport_regime='manufactured_relative_moving_faces', model_id=source[0]+':host', version='1',
            source_ids=source, allow_manufactured=True, solid_inventory_regime='reacting_manufactured')
    operator = WaterPhaseTransfer(base_model=host, chemical=chemical,
        coefficients_mol_s_pa=(tr['phase_coefficient_density_mol_s_pa_m3']*volume,)*cells,
        coefficient_set_id=source[0]+':interface', coefficient_version='1', coefficient_classification='manufactured_test_fixture',
        coefficient_source_ids=source, allow_manufactured=True, interface_modes=(tr['interfaces'],)*cells)
    return operator, rows, temperatures


def _forward(operator: Any, rows: list[list[float]], temperatures: list[float], start: float, payload: dict[str, Any]) -> tuple[Any, list[dict[str, Any]]]:
    host = operator.base_model
    if payload['model_id']==_FREE_MODEL:
        geometry=dict(normal_stretches=_free_normals(payload,len(rows)),tangential_stretch=payload['mechanics']['initial_tangential_stretch'])
    else:
        geometry=dict(time_s=start)
    state = host.state_from_temperatures(rows, temperatures, **geometry)
    layout = host.base_model.inventory_layout
    records = []
    for index, (row, temperature) in enumerate(zip(rows, temperatures)):
        point = host.point_storages[index].forward(temperature, **geometry,
            liquid_mol=row[layout.liquid_index], gas_mol=layout.gas_inventory(row), solid_mol=layout.solid_inventory(row))
        _require(point.total_energy_j == state.internal_energy_j[index], 'forward initialization is not reproducible')
        records.append(dict(temperature_k=temperature, total_energy_j=point.total_energy_j,
            energy_error_bound_j=point.energy_error_bound_j,
            mechanical_energy_error_bound_j=point.mechanical_energy_error_bound_j,
            total_addition_roundoff_j=point.total_addition_roundoff_j,
            minimum_heat_capacity_j_k=point.thermal_state.minimum_heat_capacity_j_k,
            skeleton=point.skeleton_state))
    return state, records


def build_case(case: CaseDefinition, water_dir: str | Path) -> BuiltCase:
    """Build actual kernel objects; unlike read_case this may perform native EOS work."""
    _require(type(case) is CaseDefinition, 'validated CaseDefinition required')
    actual = read_case(case.path)
    _require(actual.sha256 == case.sha256 and actual.payload == case.payload and actual.case_id == case.case_id,
             'case source changed or definition is not bound to original bytes')
    from .integration import ConservedState, IntegrationPolicy
    p = case.payload
    cells, start, end = p['grid']['cells'], p['numerics']['start_s'], p['numerics']['end_s']
    operator, rows, temperatures = _make_model(case, Path(water_dir), cells)
    depletion = _build_depletion_policy(p['numerics']['depletion'],operator=operator) if p['schema'] in (_EVENT_SCHEMA,_EXACT_EVENT_SCHEMA) else None
    if depletion is not None:
        _require(depletion.roundoff_policy.molar_mass_kg_mol == operator.chemical.reference.molar_mass_kg_mol,
                 'roundoff water molar mass differs from actual source reference')
        if depletion.pressure_comparison is not None:
            from .pressure_comparison import pressure_comparison_binding
            _require(depletion.pressure_comparison.to_record()['cell_boxes']==pressure_comparison_binding(operator)['boxes'],
                     'declared comparison boxes differ from actual model')
    forward_state, fine = _forward(operator, rows, temperatures, start,p)
    if cells == 2:
        parent, coarse = forward_state, fine
    else:
        parent_operator, parent_rows, parent_temperatures = _make_model(case, Path(water_dir), 2)
        parent, coarse = _forward(parent_operator, parent_rows, parent_temperatures, start,p)
    factor = cells//2
    initial = ConservedState(rows, [float(parent.internal_energy_j[index//factor])/factor for index in range(cells)],
                             energy_model_identity=operator.base_model.energy_model_identity,
                             mechanical_stretches=forward_state.mechanical_stretches)
    checks = []
    for parent_index in range(2):
        indexes = range(parent_index*factor, (parent_index+1)*factor)
        for column in range(5):
            _require(sum((Fraction(float(initial.amounts_mol[index, column])) for index in indexes), Fraction()) ==
                     Fraction(float(parent.amounts_mol[parent_index, column])), 'nonconservative inventory prolongation')
        _require(sum((Fraction(float(initial.internal_energy_j[index])) for index in indexes), Fraction()) ==
                 Fraction(float(parent.internal_energy_j[parent_index])), 'nonconservative energy prolongation')
        discrepancy = Fraction(coarse[parent_index]['total_energy_j'])-sum((Fraction(fine[index]['total_energy_j']) for index in indexes), Fraction())
        bound = Fraction(coarse[parent_index]['energy_error_bound_j'])+sum((Fraction(fine[index]['energy_error_bound_j']) for index in indexes), Fraction())
        checks.append(dict(parent=parent_index, signed_forward_discrepancy_j=discrepancy, source_enclosure_j=bound))
        _require(abs(discrepancy) <= bound, 'extensive storage law outside declared source/numerical enclosure')
    child_checks = []
    for index, record in enumerate(fine):
        discrepancy = abs(Fraction(record['total_energy_j'])-Fraction(float(initial.internal_energy_j[index])))
        bound = Fraction(record['energy_error_bound_j'])+Fraction(coarse[index//factor]['energy_error_bound_j'])/factor
        _require(abs(discrepancy) <= bound, 'child storage inconsistent with conservative energy')
        child_checks.append(dict(cell=index, forward_to_conservative_discrepancy_j=discrepancy, source_enclosure_j=bound))
    initialization = encode(dict(temperature_built_state=forward_state, conservative_state=initial,
        inherited_temperatures_k=temperatures, parent_state=parent, parent_forward=coarse,
        child_forward=fine, extensive_storage_checks=checks, child_storage_checks=child_checks,
        qualification='conservative manufactured initialization; forward source checks are not material calibration'))
    policy_values = dict(p['numerics']['integration'])
    for name in ('initial_step_s', 'maximum_step_s'):
        policy_values[name] /= 2**p['refinement']
    policy = IntegrationPolicy(**policy_values)
    _require(read_case(case.path).sha256 == case.sha256, 'case source changed during initialization')
    return BuiltCase(case, operator, initial, start, end, policy, initialization, depletion)


def snapshot(built: BuiltCase, state: Any, time_s: float) -> dict[str, Any]:
    """Evaluate original coupled kernel and encode traceable current-state evidence."""
    _require(type(built) is BuiltCase, 'BuiltCase required')
    _require(read_case(built.case.path).sha256 == built.case.sha256, 'case source changed before evaluation')
    out = built.operator.evaluate(state, time_s)
    return _snapshot_evaluation(built,state,time_s,out,built.operator)


def _snapshot_evaluation(built,state,time_s,out,operator):
    """Serialize an already evaluated actual operator, without repeating inversion."""
    base = out.base_evaluation
    current = base.current_host
    transport = current.transport
    faces = []
    for index in range(len(base.gas_states)-1):
        exchange = transport._face(base.gas_states[index], base.gas_states[index+1], index, index+1)
        enthalpies = {name: transport.storages[0].gas_phases[name]._curve.enthalpy_j_mol(exchange.face_temperature_k)
                     for name in transport.gas_species_order}
        faces.append(dict(face_index=index+1, exchange_reconstructed=exchange,
                          enthalpy_j_mol_at_face_temperature=enthalpies))
    cells = []
    for index, (thermal, inverse) in enumerate(zip(base.storage_states, base.total_inverses)):
        cells.append(dict(thermal=thermal, skeleton=inverse.state.skeleton_state,
            total_energy_residual_j=inverse.total_energy_residual_j,
            inverse_temperature_error_k=inverse.temperature_error_bound_k,
            bulk_volume_m3=current.storages[index].bulk_volume_m3,
            reaction_binding_same_object=current.solid_reactions.storages[index] is current.storages[index],
            current_storage_same_object=current.storages[index] is inverse.state.current_storage,
            thermal_inverse_reused=base.storage_inverses[index] is inverse.thermal_inverse))
    result = encode(dict(state=state, time_s=time_s, case_sha256=built.case.sha256,
        temperature_k=[item.mechanical.temperature_k for item in base.storage_states],
        pressure_pa=[item.mechanical.pressure_pa for item in base.storage_states],
        inverse_temperature_error_k=[item.temperature_error_bound_k for item in base.total_inverses],
        rates=out.rates, base_rates=base.rates, transfers=out.cell_transfers, gas_states=base.gas_states,
        cells=cells, internal_faces=faces, face_area_m2=transport.face_area_m2,
        cell_widths_m=transport.cell_widths_m, conductivities_w_m_k=transport.conductivities_w_m_k,
        diffusivities_m2_s=transport.effective_diffusivities_m2_s,
        gas_constant_j_mol_k=transport.storages[0].mechanical.gas_constant_j_mol_k,
        molar_masses_kg_mol={name: transport.storages[0].gas_phases[name].metadata.molar_mass_kg_mol for name in transport.gas_species_order},
        interfaces=operator.interfaces, energy_identity=operator.base_model.energy_model_identity,
        implementation=json.loads(operator.chemical.water.implementation.canonical_json),
        water_source_asset_sha256=operator.chemical.source_asset_sha256,
        qualification='manufactured verification; repeated face algebra is audit sampling, not independent thermodynamics'))
    if built.case.payload['model_id']==_FREE_MODEL:
        result.update(geometry=encode(base.geometry),free=encode(base.free))
    else:
        result['motion']=encode(base.motion)
    if time_s == built.start_s and result['state'] == encode(built.initial):
        initial_checks = []
        factor = len(cells)//2
        for index, cell in enumerate(cells):
            child = built.initialization['child_forward'][index]
            parent = built.initialization['parent_forward'][index//factor]
            discrepancy = abs(Fraction(child['total_energy_j'])-Fraction(float(state.internal_energy_j[index])))
            energy_bound = Fraction(child['energy_error_bound_j'])+Fraction(parent['energy_error_bound_j'])/factor
            capacity = Fraction(child['minimum_heat_capacity_j_k'])
            _require(capacity > 0, 'positive initial heat capacity required')
            bound = Fraction(cell['inverse_temperature_error_k'])+(discrepancy+energy_bound)/capacity
            difference = abs(Fraction(cell['thermal'].mechanical.temperature_k)-Fraction(built.initialization['inherited_temperatures_k'][index]))
            _require(difference <= bound, 'decoded initial temperature outside source/reconstruction enclosure')
            initial_checks.append(dict(cell=index, absolute_difference_k=difference, inverse_source_reconstruction_bound_k=bound))
        result['initial_temperature_checks'] = encode(initial_checks)
    _require(read_case(built.case.path).sha256 == built.case.sha256, 'case source changed during evaluation')
    return result
