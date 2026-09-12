"""Conditional pure-gas pressure bounds for source states with exactly no liquid.

The ideal-gas law, declared caloric errors and original available-volume interval
are hypotheses. A dry pressure enclosure alone admits no event or material.
"""
from collections.abc import Mapping
from dataclasses import dataclass, fields
from fractions import Fraction as F
import math

from .deforming_solid_storage import _digest
from .mass_wet_storage import WetMixedState, wet_fluid_pressure_bounds
from .rigid_storage import ClosedStorageState, _sum_upper
from .rigid_water_gas import RigidWaterGasState, closure_diagnostics
from .source_inverse_pressure import _require, _validate_source_inverse_record
from .source_net_prefix import _same
from .source_wet_storage import SourceWetStorage, SourceWetInverse
from .water_properties import _MIN_T, _MAX_T, _MAX_PRESSURE_PA


DRY_ASSUMPTIONS = (
    'ideal_gas_pressure_law_on_entire_declared_temperature_volume_box',
    'original_positive_available_fluid_volume_interval',
    'retained_reported_pressure_and_saved_representation_error_contract',
    'declared_source_caloric_and_inverse_temperature_error_contract',
)


@dataclass(frozen=True)
class DryPressureContinuation:
    inputs: tuple[F, ...]
    temperature_domain_k: tuple[F, F]
    pressure_domain_pa: tuple[F, F]
    temperature_interval_k: tuple[F, F]
    volume_interval_m3: tuple[F, F]
    analytic_interval_pa: tuple[F, F] | None
    slope_pa_k: F | None
    candidate_interval_pa: tuple[F, F] | None
    interval_pa: tuple[F, F] | None
    radius_pa: F | None
    status: str
    reason: str | None
    assumptions: tuple[str, ...] = DRY_ASSUMPTIONS
    qualification: str = 'conditional_dry_ideal_gas_pressure_not_phase_or_material_admission'
    source_certified: bool = False

    def check(self) -> None:
        expected = propagate_declared_dry_pressure(*self.inputs,
            temperature_domain_k=self.temperature_domain_k,
            pressure_domain_pa=self.pressure_domain_pa)
        _require(_same(self, expected), 'source_dry_pressure_continuation_changed')


def propagate_declared_dry_pressure(ng: F, gas_constant: F, temperature: F,
        temperature_error: F, volume: F, volume_error: F, pressure: F,
        pressure_error: F, *, temperature_domain_k: tuple[F, F],
        pressure_domain_pa: tuple[F, F]) -> DryPressureContinuation:
    """Bound P=Ng*R*T/V exactly while retaining the entire original pressure error.

    The reported radius already covers nominal-temperature closure and volume
    errors. Ng*R/(V-eV) bounds dP/dT for every allowed volume. Taking the hull
    with the direct T/V corner interval also preserves that analytic evidence;
    no shared-input uncertainty is cancelled or replaced with a smaller value.
    """
    inputs = (ng, gas_constant, temperature, temperature_error,
              volume, volume_error, pressure, pressure_error)
    _require(all(type(value) is F for value in inputs), 'exact_dry_pressure_inputs_required')
    for domain in (temperature_domain_k, pressure_domain_pa):
        _require(type(domain) is tuple and len(domain) == 2
                 and all(type(value) is F for value in domain)
                 and 0 < domain[0] < domain[1], 'exact_dry_pressure_domains_required')
    _require(ng > 0 and gas_constant > 0 and temperature > 0 and temperature_error >= 0
             and volume > 0 and 0 <= volume_error < volume and pressure > 0
             and pressure_error >= 0, 'invalid_dry_pressure_inputs')
    tbox = (temperature-temperature_error, temperature+temperature_error)
    vbox = (volume-volume_error, volume+volume_error)
    analytic = slope = candidate = interval = radius = None

    def finish(reason: str | None) -> DryPressureContinuation:
        return DryPressureContinuation(inputs, temperature_domain_k, pressure_domain_pa,
            tbox, vbox, analytic, slope, candidate, interval, radius,
            'conditional_dry_pressure_enclosure' if reason is None else 'unresolved', reason)

    if not temperature_domain_k[0] <= tbox[0] <= tbox[1] <= temperature_domain_k[1]:
        return finish('temperature_interval_outside_declared_domain')
    analytic = (ng*gas_constant*tbox[0]/vbox[1], ng*gas_constant*tbox[1]/vbox[0])
    slope = ng*gas_constant/vbox[0]
    retained_radius = pressure_error+slope*temperature_error
    candidate = (min(analytic[0], pressure-retained_radius),
                 max(analytic[1], pressure+retained_radius))
    if not pressure_domain_pa[0] <= candidate[0] <= candidate[1] <= pressure_domain_pa[1]:
        return finish('dry_pressure_interval_outside_declared_domain')
    interval = candidate
    radius = max(pressure-interval[0], interval[1]-pressure)
    return finish(None)


@dataclass(frozen=True)
class SourceDryPressure:
    storage: SourceWetStorage
    state: WetMixedState
    inverse: SourceWetInverse
    storage_identity: str
    input_binding: str
    # Original nominal-fluid, global-volume, local extra and total pressure bounds.
    initial_bounds_pa: tuple[F, F, F, F]
    continuation: DryPressureContinuation
    qualification: str = 'source_dry_inverse_with_original_temperature_and_volume_uncertainty'
    source_certified: bool = False
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self) -> None:
        _require(_digest((self.state, self.inverse)) == self.input_binding,
                 'source_dry_pressure_input_changed')
        expected = enclose_source_dry_pressure(self.storage, self.state, self.inverse)
        _require(all(_same(getattr(self, field.name), getattr(expected, field.name))
                     for field in fields(self) if field.name != 'storage'),
                 'source_dry_pressure_result_changed')


def enclose_source_dry_pressure(storage: SourceWetStorage, state: WetMixedState,
        inverse: SourceWetInverse) -> SourceDryPressure:
    """Check an actual source dry inverse using saved records and pure arithmetic.

    No source storage evaluation, inverse solve, or native EOS call occurs here.
    Wet inverse-pressure admission retains its separate positive-liquid guard.
    """
    point, fluid, mechanical, template = _validate_source_inverse_record(storage, state, inverse)
    _require(state.liquid_water_mol == 0. and mechanical.liquid_pressure_pa is None
             and _same(mechanical.liquid_volume_m3, 0.)
             and mechanical.pressure_solution_path == 'pure_gas_analytic_rounded',
             'actual_source_dry_branch_required')
    _require(all(_same(getattr(fluid, field.name), field.default)
                 for field in fields(ClosedStorageState) if field.name in ('qualification', 'energy_scope'))
             and _same(mechanical.qualification,
                       RigidWaterGasState.__dataclass_fields__['qualification'].default)
             and mechanical.pressure_bracket_qualification == 'numerical_forward_function_only_excludes_eos_error'
             and _same(mechanical.source_ids, storage.water.source_ids+template.mechanical.constant_source_ids)
             and _same(mechanical.liquid_native_molar_gas_constant_j_mol_k,
                       storage.water.reference.native_molar_gas_constant_j_mol_k),
             'source_dry_qualification_or_source_changed')
    # Match RigidStorage's original provider sequence. A restored inventory
    # mapping may have a different iteration order from the actual operator.
    source_ids = list(mechanical.source_ids)+list(template.envelope.source_ids)
    for key, amount in zip(storage.gas_ids, state.gas_amounts_mol):
        if amount:
            source_ids.extend(template.gas_phases[key].metadata.source_ids)
    _require(_same(fluid.source_ids, tuple(dict.fromkeys(source_ids))),
             'source_dry_fluid_sources_changed')
    bracket = inverse.final_temperature_bracket_k
    _require(type(bracket) is tuple and len(bracket) == 2
             and all(type(value) is float and math.isfinite(value) for value in bracket)
             and storage.temperature_domain_k[0] <= bracket[0] < bracket[1] <= storage.temperature_domain_k[1]
             and bracket[0] <= point.temperature_k <= bracket[1]
             and type(inverse.iterations) is int and inverse.iterations > 0,
             'source_dry_inverse_bracket_or_iterations_changed')
    ng = math.fsum(state.gas_amounts_mol)
    _require(ng > 0, 'positive_source_dry_gas_inventory_required')
    r, t, p = mechanical.gas_constant_j_mol_k, point.temperature_k, point.pressure_pa
    nrt = ng*r*t
    nrt_resolution = math.fsum((math.ulp(ng)*r*t, math.ulp(ng*r)*t, math.ulp(nrt)))
    volume = storage.volume.value_m3
    vg, ideal_p, rp, rv, vr, pr = closure_diagnostics(volume, 0., p, nrt, nrt_resolution)
    _require(_same(p, ideal_p)
             and _same((mechanical.gas_volume_m3, mechanical.pressure_residual_pa,
                        mechanical.volume_residual_m3, mechanical.volume_resolution_m3,
                        mechanical.pressure_resolution_pa), (vg, rp, rv, vr, pr))
             and _same(mechanical.iterations, 0)
             and _same(mechanical.final_numerical_pressure_bracket_pa, (p, p))
             and _same(mechanical.final_bracket_volume_residuals_m3, (rv, rv))
             and _same(mechanical.pressure_trial_ledger, None if template.mechanical.policy.strategy is None else ()),
             'source_dry_closure_evidence_changed')
    partial = {key: float(F(n)*F(p)/F(ng)) for key, n in zip(storage.gas_ids, state.gas_amounts_mol)}
    _require(isinstance(mechanical.partial_pressures_pa, Mapping)
             and all(type(key) is str for key in mechanical.partial_pressures_pa)
             and _same(dict(mechanical.partial_pressures_pa), partial), 'source_dry_partial_pressures_changed')
    nominal = F(_sum_upper((pr, abs(rp))))
    _require(F(fluid.pressure_error_bound_pa) >= nominal, 'underreported_dry_fluid_pressure_error')
    global_error, extra, local_error = wet_fluid_pressure_bounds(template, fluid,
        state.gas_amounts_mol, t, F(storage.volume.error_m3))
    _require(F(point.global_pressure_error_pa) >= global_error
             and F(point.extra_pressure_error_pa) >= extra
             and F(point.pressure_error_pa) >= F(local_error), 'underreported_dry_volume_pressure_error')
    env = template.envelope
    tdomain = (max(F(storage.temperature_domain_k[0]), F(env.temperature_range_k[0]), F(_MIN_T)),
               min(F(storage.temperature_domain_k[1]), F(env.temperature_range_k[1]), F(_MAX_T)))
    pdomain = (F(template.mechanical.pressure_bracket_pa[0]),
               min(F(template.mechanical.pressure_bracket_pa[1]), F(_MAX_PRESSURE_PA)))
    continuation = propagate_declared_dry_pressure(sum(map(F, state.gas_amounts_mol), F()),
        F(r), F(t), F(inverse.temperature_error_bound_k), F(volume), F(storage.volume.error_m3),
        F(p), F(point.pressure_error_pa), temperature_domain_k=tdomain, pressure_domain_pa=pdomain)
    return SourceDryPressure(storage, state, inverse, storage.model_identity, _digest((state, inverse)),
                             (nominal, global_error, extra, F(local_error)), continuation)
