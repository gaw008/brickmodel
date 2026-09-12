"""Explicit manufactured free-slab adapter; no change to existing point bounds.

Conditional on reported temperatures and a separately opted-in shared constant
parameter-box interpretation. This is not a joint T/P uncertainty certificate.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from typing import Callable
import math

from sludge_sandbox.current_solid_storage import CurrentSolidStorage, CurrentSolidInverse
from sludge_sandbox.free_solid_slab import FreeSolidSlab
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
from sludge_sandbox.incompressible_solid import IncompressibleSolidPhase
from sludge_sandbox.reacting_skeleton_energy import ManufacturedReactingSkeletonEnergy
from sludge_sandbox.deforming_solid_storage import _digest
from sludge_sandbox.water_properties import WaterState
from sludge_sandbox.integration import ConservedState

CONTRACT = 'manufactured_shared_constant_volume_parameters_v1'
QUALIFICATION = 'conditional_on_reported_temperatures_not_inverse_temperature_tubes'


class PairedPressureHostError(ValueError):
    """The actual host cannot support the requested conditional descriptor."""


def require(condition, reason):
    if not condition:
        raise PairedPressureHostError(reason)


def fraction(value):
    require(type(value) in (int, float) and math.isfinite(value), 'finite_number_required')
    return F(value)


@dataclass(frozen=True)
class SharedConstantParameterBox:
    """New conditional model family, never inferred from generic point errors."""
    point_identity_sha256: str
    species: tuple[str, ...]
    solid_volume_m3_mol: tuple[F, ...]
    solid_error_m3_mol: tuple[F, ...]
    reference_volume_m3: F
    reference_error_m3: F
    schema: str = CONTRACT


@dataclass(frozen=True)
class PairedPressureUnavailable:
    reason: str
    original_pressure_errors_pa: tuple[F, F] | None
    qualification: str = 'original_independent_point_certificate_unchanged'


def declare_manufactured_constant_box(point: CurrentSolidStorage) -> SharedConstantParameterBox:
    """Explicitly instantiate a parameter-box hypothesis from actual constants."""
    require(type(point) is CurrentSolidStorage and point.allow_manufactured is True
            and type(point.skeleton) is ManufacturedReactingSkeletonEnergy,
            'actual_manufactured_reacting_point_required')
    phases = point.template.solid_phases
    require(all(type(p) is IncompressibleSolidPhase and p.allow_manufactured is True for p in phases.values()),
            'manufactured_constant_phases_required')
    species=tuple(phases);ref=point.skeleton.reference
    v0=fraction(ref.reference_area_m2)*fraction(ref.half_thickness_m)/ref.cells
    return SharedConstantParameterBox(_digest(point),species,
        tuple(fraction(phases[k].molar_volume_m3_mol) for k in species),
        tuple(fraction(phases[k].declared_v_error_m3_mol) for k in species),v0,
        fraction(point.template.bulk_volume_error_m3)+abs(fraction(point.template.bulk_volume_m3)-v0))


def _outward_root(pressure, error, domain):
    lower,upper=pressure-error,pressure+error
    low=float(lower);high=float(upper)
    if F(low)>lower:low=math.nextafter(low,-math.inf)
    if F(high)<upper:high=math.nextafter(high,math.inf)
    require(domain[0]<=F(low)<=lower<=upper<=F(high)<=domain[1], 'outward_root_outside_domain')
    return F(low),F(high)


@dataclass(frozen=True)
class PreparedPair:
    """Kernel inputs and disclosed source/cost/absolute-error evidence."""
    a: object
    b: object
    shared: object
    liquid_a: object | None
    liquid_b: object | None
    gas_constant_j_mol_k: F
    pressure_domain_pa: tuple[F, F]
    temperature_domain_k: tuple[F, F]
    endpoint_evaluations: int
    original_pressure_errors_pa: tuple[F, F]
    original_temperature_errors_k: tuple[F, F]
    source_identity: str
    qualification: str = QUALIFICATION
    shared_error_interpretation: str = CONTRACT

    def certify(self):
        from sludge_sandbox.paired_pressure import certify_paired_pressure
        return certify_paired_pressure(self.a, self.b, self.shared,
            gas_constant_j_mol_k=self.gas_constant_j_mol_k,
            pressure_domain_pa=self.pressure_domain_pa,
            temperature_domain_k=self.temperature_domain_k,
            liquid_a=self.liquid_a, liquid_b=self.liquid_b)


def _volume_terms(point, current, solids, jacobian):
    """Preserve independent extras and deterministic representation allowances."""
    reference = point.skeleton.reference
    v0 = fraction(reference.reference_area_m2)*fraction(reference.half_thickness_m)/reference.cells
    shared_error = fraction(point.template.bulk_volume_error_m3)+abs(fraction(point.template.bulk_volume_m3)-v0)
    nominal = fraction(current.bulk_volume_m3)
    exact_available = nominal-sum((fraction(solids[key])*fraction(phase.molar_volume_m3_mol)
                                   for key, phase in current.solid_phases.items()), F())
    require(exact_available > 0, 'positive_available_volume_required')
    independent = (abs(nominal-jacobian*v0)
                   +fraction(point.error_bounds.additional_bulk_volume_error_m3)
                   +abs(F(float(exact_available))-exact_available))
    # _prepare rounds its aggregate bound outward. Keep that enlargement too.
    raw_bulk_error = jacobian*shared_error+abs(nominal-jacobian*v0)+fraction(point.error_bounds.additional_bulk_volume_error_m3)
    require(fraction(current.bulk_volume_error_m3) >= raw_bulk_error, 'prepared_bulk_error_mismatch')
    independent += fraction(current.bulk_volume_error_m3)-raw_bulk_error
    return v0, shared_error, nominal, independent


def _point(host, state, inverse, cell):
    require(type(state) is ConservedState and type(inverse) is CurrentSolidInverse,
            'actual_state_and_inverse_required')
    host._check_state(state)
    point = host.point_storages[cell]
    require(type(point) is CurrentSolidStorage and type(point.skeleton) is ManufacturedReactingSkeletonEnergy
            and point.solid_inventory_regime == 'reacting_manufactured', 'actual_reacting_current_storage_required')
    saved = inverse.state
    require(saved.model_identity == point.identity and inverse.target.model_identity == point.identity,
            'point_identity_mismatch')
    require(inverse.target.value_j == float(state.internal_energy_j[cell]), 'inverse_target_state_mismatch')
    normals = tuple(map(float, state.mechanical_stretches[:-1])); tangent = float(state.mechanical_stretches[-1])
    inputs = host._inputs(state.amounts_mol[cell])
    deformation, skeleton, current, mechanical_error, bulk_error = point._prepare(normals, tangent, inputs['solid_mol'])
    require(_digest(current) == _digest(saved.current_storage), 'actual_prepared_storage_mismatch')
    require(saved.deformation.normal_stretches == normals and saved.deformation.tangential_stretch == tangent
            and saved.deformation.cell_index == cell, 'actual_geometry_mismatch')
    require(_digest(skeleton) == _digest(saved.skeleton_state), 'actual_current_skeleton_mismatch')
    thermal = saved.thermal_state; mechanical = thermal.mechanical
    require(dict(thermal.solid_inventory_mol) == inputs['solid_mol']
            and dict(mechanical.gas_inventory_mol) == inputs['gas_mol']
            and mechanical.liquid_inventory_mol == inputs['liquid_mol'], 'actual_inventory_mismatch')
    temperature = fraction(mechanical.temperature_k); pressure = fraction(mechanical.pressure_pa)
    error = fraction(thermal.pressure_error_bound_pa)
    require(error >= 0 and fraction(inverse.temperature_error_bound_k) >= 0, 'nonnegative_point_errors')
    envelope = current.fluid_template.envelope
    p_domain = tuple(map(fraction, current.fluid_template.mechanical.pressure_bracket_pa))
    t_domain = tuple(map(fraction, envelope.temperature_range_k))
    require(t_domain[0] <= temperature <= t_domain[1], 'reported_temperature_outside_domain')
    require(p_domain[0] <= pressure-error <= pressure+error <= p_domain[1], 'original_root_enclosure_outside_domain')
    jacobian = fraction(normals[cell])*fraction(tangent)**2
    terms = _volume_terms(point, current, inputs['solid_mol'], jacobian)
    return point, current, inputs, temperature, _outward_root(pressure,error,p_domain), jacobian, terms, p_domain, t_domain


def prepare_paired_pressure(operator, state_a, inverse_a, state_b, inverse_b, *,
                            cell_index: int, shared_constant_parameters: SharedConstantParameterBox | None = None,
                            endpoint_observer: Callable | None = None,
                            before_endpoint: Callable[[], None] | None = None) -> PreparedPair | PairedPressureUnavailable:
    """Prepare <=4 endpoint calls for one actual cell and B's original root box.

    Opt-in is a new explicit manufactured parameter-box hypothesis, not inferred
    correlation of arbitrary declared pointwise errors. Unsupported hosts fail.
    before_endpoint runs immediately before each attempted water call and may
    raise to cancel. endpoint_observer runs only after a successful return.
    """
    if shared_constant_parameters is None:
        errors=None
        if type(inverse_a) is CurrentSolidInverse and type(inverse_b) is CurrentSolidInverse:
            errors=tuple(fraction(v.state.thermal_state.pressure_error_bound_pa) for v in (inverse_a,inverse_b))
        return PairedPressureUnavailable('explicit_shared_constant_parameter_box_not_declared',errors)
    require(type(shared_constant_parameters) is SharedConstantParameterBox, 'typed_shared_constant_parameter_box_required')
    require(type(operator) is WaterPhaseTransfer and type(operator.base_model) is FreeSolidSlab,
            'direct_actual_free_water_host_required')
    host = operator.base_model
    require(host.allow_manufactured is True and host.solid_inventory_regime == 'reacting_manufactured',
            'manufactured_reacting_host_required')
    require(type(cell_index) is int and 0 <= cell_index < len(host.point_storages), 'cell_index')
    operator.chemical._check_identity()
    values_a = _point(host, state_a, inverse_a, cell_index)
    values_b = _point(host, state_b, inverse_b, cell_index)
    point, current, _, _, _, _, terms, p_domain, t_domain = values_a
    require(shared_constant_parameters==declare_manufactured_constant_box(point),'actual_shared_parameter_box_binding_mismatch')
    require(values_b[0] is point and values_b[7:] == values_a[7:], 'same_cell_provider_domain_required')
    phases = point.template.solid_phases
    require(all(type(p) is IncompressibleSolidPhase and p.allow_manufactured is True for p in phases.values()),
            'actual_constant_manufactured_solid_required')
    species = tuple(phases)
    water = current.fluid_template.mechanical.water
    require(type(water) is type(operator.chemical.water)
            and _digest(water) == _digest(operator.chemical.water)
            and water.implementation == operator.chemical.water.implementation,
            'actual_water_content_mismatch')
    implementation = water.implementation
    operator_content = _digest(operator)
    source = _digest((CONTRACT, operator_content, point.identity, operator.chemical.method_id,
                      _digest(operator.chemical), None if implementation is None else implementation.sha256,
                      operator.coefficients_mol_s_pa, operator.coefficient_set_id, operator.coefficient_version,
                      operator.source_ids))
    from sludge_sandbox.paired_pressure import PressureState, SharedVolumes, LiquidEndpoints
    shared = SharedVolumes(source, species, tuple(fraction(phases[k].molar_volume_m3_mol) for k in species),
        tuple(fraction(phases[k].declared_v_error_m3_mol) for k in species), terms[0], terms[1])
    def descriptor(values):
        _, _, inputs, temperature, root, jacobian, volumes, _, _ = values
        return PressureState(source, temperature, sum(map(fraction, inputs['gas_mol'].values()), F()),
            fraction(inputs['liquid_mol']), tuple(fraction(inputs['solid_mol'][k]) for k in species),
            volumes[2], jacobian, volumes[3], root)
    a, b = descriptor(values_a), descriptor(values_b)
    endpoint_calls = 0
    def endpoints(state, prepared):
        nonlocal endpoint_calls
        if state.liquid_mol == 0:
            return None  # Exact represented zero annihilates every liquid term.
        samples = []
        for endpoint in b.root_interval_pa:
            represented = float(endpoint)
            require(F(represented) == endpoint, 'endpoint_pressure_not_binary64_representable')
            if before_endpoint is not None:before_endpoint()
            actual = water.state_tp(float(state.temperature_k), represented, phase='liquid')
            if endpoint_observer is not None:endpoint_observer(actual)
            endpoint_calls += 1
            require(type(actual) is WaterState and actual.phase == 'liquid'
                    and fraction(actual.temperature_k) == state.temperature_k
                    and fraction(actual.pressure_pa) == endpoint, 'actual_liquid_endpoint_identity')
            require(actual.reference == water.reference and actual.implementation == implementation, 'endpoint_source_binding')
            exact_volume = fraction(actual.molar_mass_kg_mol)/fraction(actual.density_kg_m3)
            volume = F(float(exact_volume))
            error = fraction(prepared.fluid_template.envelope.liquid_v_error_m3_mol)+abs(volume-exact_volume)
            samples.append((volume, error))
        return LiquidEndpoints(source, state.temperature_k, b.root_interval_pa,
            samples[0][0], samples[1][0], samples[0][1], samples[1][1])
    la = endpoints(a, values_a[1]); lb = endpoints(b, values_b[1])
    require(water.implementation == implementation
            and operator.chemical.water.implementation == implementation
            and _digest(point.template) == point._template_digest and _digest(operator)==operator_content
            and shared_constant_parameters==declare_manufactured_constant_box(point),
            'provider_changed_during_endpoint_evaluation')
    return PreparedPair(a,b,shared,la,lb,fraction(current.fluid_template.mechanical.gas_constant_j_mol_k),
        p_domain,t_domain,endpoint_calls,(fraction(inverse_a.state.thermal_state.pressure_error_bound_pa),
        fraction(inverse_b.state.thermal_state.pressure_error_bound_pa)),
        (fraction(inverse_a.temperature_error_bound_k),fraction(inverse_b.temperature_error_bound_k)),source)
