"""Explicit reported-temperature pressure comparisons; no implicit correlation.

The data auditor proves arithmetic and binding to externally trusted state and
operator descriptors. It does not independently validate recorded native EOS
samples. Generic comparisons remain the integrator's separate default path.
"""
from dataclasses import asdict, dataclass, fields
from fractions import Fraction as F
import json
import math
from typing import Callable, Any

from .paired_pressure import PressureState, SharedVolumes, LiquidEndpoints, certify_paired_pressure
from .paired_pressure_host import SharedConstantParameterBox, declare_manufactured_constant_box, prepare_paired_pressure
from .deforming_solid_storage import _digest
from .water_phase_transfer import WaterPhaseTransfer
from .free_solid_slab import FreeSolidSlab
from .integration import ConservedState

SCHEMA = 'manufactured_shared_constant_reported_temperature_v1'


class PressureComparisonError(ValueError):
    """Unsupported comparison or invalid saved evidence."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise PressureComparisonError(reason)


def _encode(value: Any) -> Any:
    if type(value) is F:
        return {'numerator': value.numerator, 'denominator': value.denominator}
    if isinstance(value, dict):
        return {k: _encode(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_encode(v) for v in value]
    return value


def _decode(value: Any) -> Any:
    if type(value) is dict:
        if set(value) == {'numerator', 'denominator'}:
            n, d = value['numerator'], value['denominator']
            _require(type(n) is int and type(d) is int and d > 0, 'invalid_fraction')
            out = F(n, d)
            _require(out.numerator == n and out.denominator == d, 'noncanonical_fraction')
            return out
        return {k: _decode(v) for k, v in value.items()}
    if type(value) is list:
        return tuple(_decode(v) for v in value)
    _require(value is None or type(value) in (str, int, float, bool), 'invalid_json_value')
    if type(value) is float:
        _require(math.isfinite(value), 'nonfinite_record')
    return value


def _construct(cls: type, data: dict) -> Any:
    _require(type(data) is dict and set(data) == {f.name for f in fields(cls)}, 'record_fields')
    return cls(**data)


@dataclass(frozen=True)
class PressureComparisonPolicy:
    cell_boxes: tuple[SharedConstantParameterBox, ...]
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        _require(type(self.schema) is str and self.schema == SCHEMA, 'comparison_schema')
        _require(type(self.cell_boxes) is tuple and bool(self.cell_boxes), 'complete_immutable_boxes')
        identities = []
        for box in self.cell_boxes:
            _require(type(box) is SharedConstantParameterBox, 'typed_box_required')
            # SharedVolumes supplies strict Fraction/domain/shape validation.
            SharedVolumes(box.point_identity_sha256, box.species, box.solid_volume_m3_mol,
                          box.solid_error_m3_mol, box.reference_volume_m3, box.reference_error_m3, box.schema)
            identities.append(box.point_identity_sha256)
        _require(len(set(identities)) == len(identities), 'duplicate_cell_box')

    def to_record(self) -> dict:
        return _encode(asdict(self))


def restore_pressure_comparison_policy(data: dict) -> PressureComparisonPolicy:
    try:
        parsed = _decode(data)
        _require(type(parsed) is dict and set(parsed) == {'cell_boxes', 'schema'}, 'policy_fields')
        _require(type(parsed['cell_boxes']) is tuple, 'box_array')
        return PressureComparisonPolicy(tuple(_construct(SharedConstantParameterBox, v)
                                              for v in parsed['cell_boxes']), parsed['schema'])
    except (TypeError, KeyError, AttributeError) as exc:
        raise PressureComparisonError('malformed_policy') from exc


def pressure_comparison_binding(operator: WaterPhaseTransfer) -> dict:
    """No EOS: content identity plus explicit inventory and geometry semantics."""
    _require(type(operator) is WaterPhaseTransfer and type(operator.base_model) is FreeSolidSlab,
             'direct_free_water_host_required')
    host = operator.base_model
    operator.chemical._check_identity()
    from .verification_case import encode
    layout = host.inventory_layout
    points = host.point_storages
    return {'operator_sha256': _digest(operator), 'base_sha256': _digest(host), 'interfaces': list(operator.interfaces),
            'layout': _encode(asdict(layout)),
            'sources': [_digest(('manufactured_shared_constant_volume_parameters_v1', _digest(operator), p.identity,
                         operator.chemical.method_id, _digest(operator.chemical),
                         None if operator.chemical.water.implementation is None else operator.chemical.water.implementation.sha256,
                         operator.coefficients_mol_s_pa, operator.coefficient_set_id, operator.coefficient_version, operator.source_ids)) for p in points],
            'water_reference': encode(operator.chemical.water.reference),
            'water_implementation': encode(operator.chemical.water.implementation),
            'domains': [{'liquid_v_error': _encode(F(p.template.fluid_template.envelope.liquid_v_error_m3_mol)), 'pressure': _encode(tuple(F(v) for v in p.template.fluid_template.mechanical.pressure_bracket_pa)),
                         'temperature': _encode(tuple(F(v) for v in p.template.fluid_template.envelope.temperature_range_k)),
                         'gas_constant': _encode(F(p.template.fluid_template.mechanical.gas_constant_j_mol_k))} for p in points],
            'boxes': [PressureComparisonPolicy((declare_manufactured_constant_box(p),)).to_record()['cell_boxes'][0]
                      for p in points],
            'reference': [{'area': _encode(F(p.skeleton.reference.reference_area_m2)),
                           'half_thickness': _encode(F(p.skeleton.reference.half_thickness_m)),
                           'cells': p.skeleton.reference.cells,
                           'additional_bulk_error': _encode(F(p.error_bounds.additional_bulk_volume_error_m3))} for p in points]}


@dataclass(frozen=True)
class PressureComparisonResult:
    bound_pa: float
    record_json: bytes

    def to_record(self) -> dict:
        return json.loads(self.record_json)


def compare_pressure_pair(op_a: WaterPhaseTransfer, state_a: ConservedState, inverses_a: tuple,
                          op_b: WaterPhaseTransfer, state_b: ConservedState, inverses_b: tuple, *,
                          policy: PressureComparisonPolicy,
                          before_endpoint: Callable[[], None] | None = None,
                          after_endpoint: Callable[[Any], None] | None = None) -> PressureComparisonResult:
    _require(type(policy) is PressureComparisonPolicy, 'typed_policy_required')
    ba, bb = pressure_comparison_binding(op_a), pressure_comparison_binding(op_b)
    _require(ba['base_sha256'] == bb['base_sha256'], 'different_closure_hosts')
    _require(policy.to_record()['cell_boxes'] == ba['boxes'] == bb['boxes'], 'cell_box_order_or_identity')
    count = len(policy.cell_boxes)
    _require(type(inverses_a) is tuple and type(inverses_b) is tuple and
             len(inverses_a) == len(inverses_b) == count, 'complete_inverse_tuples')
    op_b.base_model._check_state(state_b)
    from .verification_case import encode
    cells = []
    for i, box in enumerate(policy.cell_boxes):
        samples = []
        def observed(actual: Any) -> None:
            samples.append(encode(actual))
            if after_endpoint is not None:
                after_endpoint(actual)
        prepared = prepare_paired_pressure(op_a, state_a, inverses_a[i], state_b, inverses_b[i],
                                          cell_index=i, shared_constant_parameters=box,
                                          before_endpoint=before_endpoint,
                                          endpoint_observer=observed)
        cert = prepared.certify()
        cells.append({'endpoint_samples': samples, 'cell_index': i, 'certificate': cert.to_record(),
                      'original_pressure_errors_pa': _encode(prepared.original_pressure_errors_pa),
                      'original_temperature_errors_k': _encode(prepared.original_temperature_errors_k),
                      'reported_temperatures_k': _encode(tuple(F(x.state.thermal_state.mechanical.temperature_k)
                                                             for x in (inverses_a[i], inverses_b[i]))),
                      'reported_pressures_pa': _encode(tuple(F(x.state.thermal_state.mechanical.pressure_pa)
                                                            for x in (inverses_a[i], inverses_b[i]))),
                      'endpoint_evaluations': prepared.endpoint_evaluations})
    _require(pressure_comparison_binding(op_a) == ba and pressure_comparison_binding(op_b) == bb,
             'operator_changed_during_comparison')
    from .verification_case import encode
    nominal = max(abs(float(c['reported_pressures_pa'][0]['numerator'] / c['reported_pressures_pa'][0]['denominator']) -
                            float(c['reported_pressures_pa'][1]['numerator'] / c['reported_pressures_pa'][1]['denominator'])) for c in cells)
    independent = nominal + max(float(inverses_a[i].state.thermal_state.pressure_error_bound_pa) for i in range(count)) + max(float(inverses_b[i].state.thermal_state.pressure_error_bound_pa) for i in range(count))
    record = {'states': [encode(state_a), encode(state_b)], 'original_independent_bound_pa': independent,
              'endpoint_evaluations': sum(c['endpoint_evaluations'] for c in cells), 'schema': SCHEMA, 'policy': policy.to_record(), 'bindings_a': ba, 'bindings_b': bb,
              'cells': cells, 'bound_pa': max(c['certificate']['bound_pa'] for c in cells),
              'temperature_uncertainty_included': False, 'material_qualified': False}
    audit_pressure_comparison(record, policy=policy, state_a=state_a, state_b=state_b,
                              bindings_a=ba, bindings_b=bb)
    return PressureComparisonResult(record['bound_pa'], json.dumps(record, sort_keys=True,
                                   separators=(',', ':'), allow_nan=False).encode())


def audit_pressure_comparison(record: dict, *, policy: PressureComparisonPolicy,
                              state_a: ConservedState, state_b: ConservedState,
                              bindings_a: dict, bindings_b: dict) -> float:
    """Replay arithmetic against caller-verified original states and bindings."""
    try:
        return _audit(record, policy, state_a, state_b, bindings_a, bindings_b)
    except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as exc:
        raise PressureComparisonError('malformed_comparison_record') from exc


def _audit(record: dict, policy: PressureComparisonPolicy, state_a: ConservedState,
           state_b: ConservedState, bindings_a: dict, bindings_b: dict) -> float:
    _require(type(policy) is PressureComparisonPolicy, 'typed_policy_required')
    _require(type(record) is dict and set(record) == {'schema', 'policy', 'bindings_a', 'bindings_b',
             'cells', 'bound_pa', 'temperature_uncertainty_included', 'material_qualified',
             'states', 'original_independent_bound_pa', 'endpoint_evaluations'}, 'comparison_fields')
    _require(record['schema'] == SCHEMA and record['policy'] == policy.to_record(), 'policy_binding')
    _require(record['temperature_uncertainty_included'] is False and record['material_qualified'] is False,
             'qualification_changed')
    _require(record['bindings_a'] == bindings_a and record['bindings_b'] == bindings_b and
             bindings_a['base_sha256'] == bindings_b['base_sha256'], 'external_binding_mismatch')
    _require(bindings_a['boxes'] == bindings_b['boxes'] == policy.to_record()['cell_boxes'], 'box_binding')
    count = len(policy.cell_boxes)
    _require(type(record['cells']) is list and len(record['cells']) == count, 'complete_cell_records')
    layout = bindings_a['layout']; order = layout['species_order']
    _require(bindings_b['layout'] == layout, 'layout_mismatch')
    for state in (state_a, state_b):
        _require(type(state) is ConservedState and state.amounts_mol.shape == (count, len(order)) and
                 state.mechanical_stretches is not None and len(state.mechanical_stretches) == count + 1,
                 'complete_mechanical_state')
    from .verification_case import encode
    _require(record['states'] == [encode(state_a), encode(state_b)], 'external_state_binding')
    bounds = []; original_pressures = []; original_errors = []
    for i, cell in enumerate(record['cells']):
        _require(set(cell) == {'cell_index', 'certificate', 'original_pressure_errors_pa',
                 'original_temperature_errors_k', 'reported_pressures_pa', 'reported_temperatures_k', 'endpoint_evaluations', 'endpoint_samples'} and
                 type(cell['cell_index']) is int and cell['cell_index'] == i, 'cell_order')
        raw = cell['certificate']['input_record_json']; data = _decode(raw)
        a, b = (_construct(PressureState, data[k]) for k in ('a', 'b'))
        shared = _construct(SharedVolumes, data['shared'])
        box = policy.cell_boxes[i]
        _require(shared.source_identity == bindings_a['sources'][i], 'source_semantic_binding')
        domain = _decode(bindings_a['domains'][i])
        _require(data['pressure_domain_pa'] == domain['pressure'] and data['temperature_domain_k'] == domain['temperature'] and
                 data['gas_constant_j_mol_k'] == domain['gas_constant'], 'source_domain_binding')
        _require(shared.species == box.species and shared.solid_volume_m3_mol == box.solid_volume_m3_mol and
                 shared.solid_error_m3_mol == box.solid_error_m3_mol and
                 shared.reference_volume_m3 == box.reference_volume_m3 and shared.reference_error_m3 == box.reference_error_m3,
                 'shared_parameter_binding')
        errors = _decode(cell['original_pressure_errors_pa']); temps = _decode(cell['original_temperature_errors_k'])
        pressures = _decode(cell['reported_pressures_pa'])
        reported_t = _decode(cell['reported_temperatures_k'])
        _require(reported_t == (a.temperature_k, b.temperature_k), 'reported_temperature_binding')
        original_pressures.append(pressures); original_errors.append(errors)
        _require(len(errors) == len(temps) == len(pressures) == 2 and
                 all(type(v) is F and v >= 0 for v in (*errors, *temps, *pressures)), 'observation_bounds')
        for j, (point, state) in enumerate(((a, state_a), (b, state_b))):
            row = state.amounts_mol[i]
            _require(point.gas_mol == sum((F(float(row[order.index(s)])) for s in layout['gas_species_order']), F()) and
                     point.liquid_mol == F(float(row[order.index(layout['liquid_column_id'])])) and
                     point.solid_mol == tuple(F(float(row[order.index(s)])) for s in shared.species), 'inventory_binding')
            _require(point.jacobian == F(float(state.mechanical_stretches[i])) *
                     F(float(state.mechanical_stretches[-1])) ** 2, 'geometry_binding')
            reference = _decode(bindings_a['reference'][i])
            _require(reference['cells'] == count and reference['area'] * reference['half_thickness'] / count == shared.reference_volume_m3,
                     'reference_binding')
            from .geometry import ReferenceSlab
            from .deforming_solid_storage import _upper
            geom = ReferenceSlab(float(reference['half_thickness']), float(reference['area']), count).deform(
                state.mechanical_stretches[:-1], tangential_stretch=float(state.mechanical_stretches[-1]))
            bulk = F(float(geom.volumes_m3[i]))
            discrepancy = abs(bulk - point.jacobian * shared.reference_volume_m3)
            extra = reference['additional_bulk_error']
            _require(type(extra) is F and extra >= 0, 'additional_error_domain')
            raw_error = point.jacobian * shared.reference_error_m3 + discrepancy + extra
            available = bulk - sum((n*v for n,v in zip(point.solid_mol, shared.solid_volume_m3_mol)), F())
            independent = discrepancy + extra + abs(F(float(available)) - available) + F(_upper(raw_error)) - raw_error
            _require(point.bulk_volume_m3 == bulk and point.independent_volume_error_m3 == independent,
                     'prepared_volume_error_binding')
            from .paired_pressure_host import _outward_root
            _require(point.root_interval_pa == _outward_root(pressures[j], errors[j], data['pressure_domain_pa']),
                     'root_observation_binding')
        samples = cell['endpoint_samples']
        _require(type(samples) is list, 'endpoint_samples_array')
        expected_samples = []
        for point, key in ((a, 'liquid_a'), (b, 'liquid_b')):
            if point.liquid_mol > 0:
                endpoint = data[key]
                for index, pressure in enumerate(b.root_interval_pa):
                    expected_samples.append((point.temperature_k, pressure, endpoint, index))
        _require(len(samples) == len(expected_samples), 'endpoint_samples_count')
        for sample, (temperature, pressure, endpoint, index) in zip(samples, expected_samples):
            from .water_properties import WaterState
            _require(type(sample) is dict and set(sample) == {f.name for f in fields(WaterState)}, 'endpoint_sample_fields')
            for name in ('temperature_k', 'pressure_pa', 'density_kg_m3'):
                value = sample[name]
                _require(type(value) in (int, float) and math.isfinite(value) and value > 0, 'endpoint_sample_numeric')
            _require(sample['phase'] == 'liquid' and F(sample['temperature_k']) == temperature and
                     F(sample['pressure_pa']) == pressure, 'endpoint_sample_state')
            _require(sample['reference'] == bindings_a['water_reference'] and sample['implementation'] == bindings_a['water_implementation'], 'endpoint_sample_source')
            exact_volume = F(sample['reference']['molar_mass_kg_mol']) / F(sample['density_kg_m3'])
            volume = F(float(exact_volume))
            key = 'volume_at_lower_m3_mol' if index == 0 else 'volume_at_upper_m3_mol'
            _require(volume == endpoint[key], 'endpoint_sample_volume')
            error_key = 'error_at_lower_m3_mol' if index == 0 else 'error_at_upper_m3_mol'
            _require(endpoint[error_key] == domain['liquid_v_error'] + abs(volume - exact_volume), 'endpoint_error_binding')
        cert = certify_paired_pressure(a, b, shared, gas_constant_j_mol_k=data['gas_constant_j_mol_k'],
                 pressure_domain_pa=data['pressure_domain_pa'], temperature_domain_k=data['temperature_domain_k'],
                 liquid_a=None if data['liquid_a'] is None else _construct(LiquidEndpoints, data['liquid_a']),
                 liquid_b=None if data['liquid_b'] is None else _construct(LiquidEndpoints, data['liquid_b']))
        _require(cert.to_record() == cell['certificate'], 'certificate_arithmetic_mismatch')
        _require(type(cell['endpoint_evaluations']) is int and cell['endpoint_evaluations'] ==
                 2 * (int(a.liquid_mol > 0) + int(b.liquid_mol > 0)), 'endpoint_cost_mismatch')
        bounds.append(cert.bound_pa)
    independent = max(abs(float(p[0]) - float(p[1])) for p in original_pressures) + max(float(e[0]) for e in original_errors) + max(float(e[1]) for e in original_errors)
    _require(record['original_independent_bound_pa'] == independent, 'original_independent_bound_mismatch')
    _require(type(record['endpoint_evaluations']) is int and record['endpoint_evaluations'] == sum(c['endpoint_evaluations'] for c in record['cells']), 'total_endpoint_cost')
    bound = max(bounds)
    _require(type(record['bound_pa']) is float and record['bound_pa'] == bound, 'maximum_bound_mismatch')
    return bound
