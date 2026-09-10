"""Conditional inverse-temperature pressure bounds for fixed source wet states.

The declared envelope and a smooth stable liquid branch are hypotheses, not
independent EOS certificates. No event, material or phase-transition authority
is conferred by these bounds.
"""
from collections.abc import Mapping
from dataclasses import dataclass, fields
from fractions import Fraction as F
import math

from .deforming_solid_storage import _digest
from .integration import IntegrationError
from .mass_wet_storage import WetMixedState, wet_fluid_pressure_bounds, lower
from .mass_storage_bridge import upper, number
from .rigid_storage import ClosedStorageState, liquid_pressure_error_bound, _directed, _sum_upper, _product_upper
from .rigid_water_gas import RigidWaterGasState, closure_diagnostics
from .source_wet_storage import SourceWetStorage, SourceWetInverse, SourceWetPoint
from .source_endpoint_comparison import SourceEndpointComparison
from .source_net_prefix import _same

ASSUMPTIONS = ('smooth_stable_planar_liquid_branch_on_entire_declared_box',
               'declared_domain_wide_liquid_volume_and_uP_error_bounds',
               'saved_closure_residual_and_representation_error_contract',
               'declared_caloric_error_and_saved_energy_roundoff_contract')


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise IntegrationError(reason)


@dataclass(frozen=True)
class PressureContinuation:
    inputs: tuple[F, ...]
    temperature_domain_k: tuple[F, F]
    pressure_domain_pa: tuple[F, F]
    temperature_interval_k: tuple[F, F]
    global_slope_pa_k: F | None
    global_radius_pa: F | None
    global_interval_pa: tuple[F, F] | None
    slope_pa_k: F | None
    radius_pa: F | None
    interval_pa: tuple[F, F] | None
    status: str
    reason: str | None
    assumptions: tuple[str, ...] = ASSUMPTIONS
    source_certified: bool = False

    def check(self) -> None:
        expected = propagate_declared_pressure(*self.inputs,
            temperature_domain_k=self.temperature_domain_k,pressure_domain_pa=self.pressure_domain_pa)
        _require(_same(self,expected), 'conditional_pressure_record_changed')


def propagate_declared_pressure(nl: F, ng: F, gas_constant: F, abs_uP_bound: F,
        temperature: F, temperature_error: F, pressure: F, pressure_error: F, *,
        temperature_domain_k: tuple[F, F], pressure_domain_pa: tuple[F, F]) -> PressureContinuation:
    """Exact conditional continuation algebra; inputs are explicit Fractions.

    The gas-only nl=0 limit is algebraically supported here. Source wet callers
    retain their positive-liquid requirement. Domains are caller hypotheses.
    """
    inputs=(nl,ng,gas_constant,abs_uP_bound,temperature,temperature_error,pressure,pressure_error)
    _require(all(type(x) is F for x in inputs), 'exact_pressure_inputs_required')
    for domain in (temperature_domain_k,pressure_domain_pa):
        _require(type(domain) is tuple and len(domain)==2 and all(type(x) is F for x in domain)
                 and 0<domain[0]<domain[1], 'exact_positive_pressure_domains_required')
    _require(nl>=0 and ng>0 and gas_constant>0 and abs_uP_bound>=0 and temperature>0
             and temperature_error>=0 and pressure>0 and pressure_error>=0, 'invalid_pressure_inputs')
    tbox=(temperature-temperature_error,temperature+temperature_error)
    global_slope=global_radius=global_box=slope=radius=box=None
    def finish(reason):
        return PressureContinuation(inputs,temperature_domain_k,pressure_domain_pa,tbox,
            global_slope,global_radius,global_box,slope,radius,box,
            'conditional_pressure_enclosure' if reason is None else 'unresolved',reason)
    if not temperature_domain_k[0]<=tbox[0]<=tbox[1]<=temperature_domain_k[1]:
        return finish('temperature_interval_outside_declared_domain')
    def lipschitz(tmin,pmax):
        return pmax/tmin*(1+nl*abs_uP_bound*pmax/(ng*gas_constant*tmin))
    global_slope=lipschitz(temperature_domain_k[0],pressure_domain_pa[1])
    global_radius=pressure_error+global_slope*temperature_error
    global_box=(pressure-global_radius,pressure+global_radius)
    inside=(pressure_domain_pa[0]<global_box[0]<=global_box[1]<pressure_domain_pa[1]
            if temperature_error else pressure_domain_pa[0]<=global_box[0]<=global_box[1]<=pressure_domain_pa[1])
    if not inside:
        return finish('temperature_continuation_pressure_domain_exit')
    # The global enclosure establishes the entire smaller box first.
    slope=lipschitz(tbox[0],global_box[1])
    radius=pressure_error+slope*temperature_error
    box=(pressure-radius,pressure+radius)
    _require(radius<=global_radius and global_box[0]<=box[0]<=box[1]<=global_box[1],
             'conditional_bootstrap_not_nested')
    return finish(None)


@dataclass(frozen=True)
class SourceInversePressure:
    storage: SourceWetStorage
    state: WetMixedState
    inverse: SourceWetInverse
    storage_identity: str
    input_binding: str
    # Original outward-rounded nominal fluid, global volume and local volume bounds.
    initial_bounds_pa: tuple[F, F, F, F]
    continuation: PressureContinuation
    source_certified: bool = False
    event_admitted: bool = False

    def check(self) -> None:
        _require(_digest((self.state,self.inverse))==self.input_binding, 'source_pressure_input_changed')
        expected=enclose_source_inverse_pressure(self.storage,self.state,self.inverse)
        _require(all(_same(getattr(self,f.name),getattr(expected,f.name))
                     for f in fields(self) if f.name!='storage'), 'source_pressure_result_changed')


def enclose_source_inverse_pressure(storage: SourceWetStorage, state: WetMixedState,
        inverse: SourceWetInverse) -> SourceInversePressure:
    """Bind the conditional algebra to an actual checked source storage record."""
    _require(type(storage) is SourceWetStorage and type(state) is WetMixedState
             and type(inverse) is SourceWetInverse, 'actual_source_pressure_inputs_required')
    storage.check(state)
    point=inverse.point
    _require(type(point) is SourceWetPoint and type(point.fluid) is ClosedStorageState
             and type(point.fluid.mechanical) is RigidWaterGasState, 'actual_source_pressure_point_required')
    fluid=point.fluid; mechanical=fluid.mechanical; template=storage.fluid_template
    _require(type(fluid.source_ids) is tuple and all(type(s) is str for s in fluid.source_ids)
             and _same(point.source_ids,tuple(sorted(set(storage.source_ids+fluid.source_ids))))
             and all(_same(getattr(point,f.name),f.default) for f in fields(SourceWetPoint)
                     if f.name in ('qualification','total_enthalpy_j','solid_volume_m3','fit_error')),
             'source_point_metadata_changed')
    _require(point.model_identity==state.energy_model_identity==storage.model_identity
             and point.material_qualified is False and _same(fluid.envelope,template.envelope)
             # Passive JSON records restore mappings as dict; the live water
             # provider exposes a read-only mapping. Preserve exact contents.
             and all(isinstance(assets,Mapping) and all(type(k) is str for k in assets)
                     for assets in (mechanical.source_asset_sha256,storage.water.source_asset_sha256))
             and _same(dict(mechanical.source_asset_sha256),dict(storage.water.source_asset_sha256))
             and _same(mechanical.policy,template.mechanical.policy)
             and _same(mechanical.pressure_bracket_pa,template.mechanical.pressure_bracket_pa)
             and mechanical.assumption==template.mechanical.assumption
             and _same(mechanical.gas_constant_j_mol_k,template.mechanical.gas_constant_j_mol_k)
             and _same(mechanical.liquid_pressure_pa,mechanical.pressure_pa),
             'source_pressure_model_binding')
    _require(_same(mechanical.liquid_inventory_mol,state.liquid_water_mol) and state.liquid_water_mol>0
             and set(mechanical.gas_inventory_mol)==set(storage.gas_ids)
             and _same(tuple(mechanical.gas_inventory_mol[k] for k in storage.gas_ids),state.gas_amounts_mol)
             and _same(inverse.target_energy_j,state.internal_energy_j)
             and type(inverse.energy_residual_j) is F
             and inverse.energy_residual_j==F(point.total_internal_energy_j)-F(state.internal_energy_j)
             and _same(point.available_pore_volume_m3,storage.volume.value_m3)
             and _same(point.available_volume_error_m3,storage.volume.error_m3), 'source_pressure_state_binding')
    values=(point.temperature_k,point.pressure_pa,inverse.temperature_error_bound_k,
            point.pressure_error_pa,point.global_pressure_error_pa,point.extra_pressure_error_pa,
            fluid.pressure_error_bound_pa,point.energy_error_j,point.minimum_heat_capacity_j_k)
    _require(all(type(x) is float and math.isfinite(x) for x in values)
             and values[0]>0 and values[1]>0 and all(x>=0 for x in values[2:])
             and point.minimum_heat_capacity_j_k>0, 'finite_source_pressure_bounds_required')
    mass=F(storage.dry_mass_kg)
    gas_cmin=_directed(sum((F(n)*F(template.envelope.gas_cv_lower_j_mol_k[k])
                           for k,n in zip(storage.gas_ids,state.gas_amounts_mol)),F()),upper=False)
    source_cmin=lower(F(gas_cmin)+mass*storage.caloric.minimum_specific_heat_capacity(*map(F,storage.temperature_domain_k)))
    solid_u=mass*storage.caloric.specific_internal_energy(F(point.temperature_k))
    total=F(fluid.internal_energy_j)+solid_u
    _require(_same(fluid.minimum_heat_capacity_j_k,gas_cmin)
             and _same(point.minimum_heat_capacity_j_k,source_cmin)
             and _same(point.solid_internal_energy_j,solid_u)
             and _same(point.total_internal_energy_j,number(total)), 'source_caloric_accounting_changed')
    fluid_error_terms=[_product_upper(state.liquid_water_mol,template.envelope.liquid_u_error_j_mol)]
    fluid_error_terms.extend(_product_upper(n,template.envelope.gas_u_error_j_mol[k])
                             for k,n in zip(storage.gas_ids,state.gas_amounts_mol) if n)
    _require(type(fluid.energy_roundoff_j) is float and math.isfinite(fluid.energy_roundoff_j)
             and fluid.energy_roundoff_j>=0, 'finite_saved_energy_roundoff_required')
    fluid_error_terms.extend((fluid.energy_roundoff_j,_product_upper(state.liquid_water_mol,
                              template.envelope.liquid_abs_du_dp_bound_j_mol_pa,fluid.pressure_error_bound_pa)))
    fluid_error=_sum_upper(fluid_error_terms)
    source_error=upper(F(fluid.energy_error_bound_j)+abs(F(point.total_internal_energy_j)-total)
                      +F(state.liquid_water_mol)*F(template.envelope.liquid_abs_du_dp_bound_j_mol_pa)
                      *F(point.extra_pressure_error_pa))
    _require(type(fluid.energy_error_bound_j) is float and math.isfinite(fluid.energy_error_bound_j)
             and fluid.energy_error_bound_j>=fluid_error and point.energy_error_j>=source_error,
             'underreported_source_caloric_error')
    expected_T=F(upper((abs(inverse.energy_residual_j)+F(point.energy_error_j))
                        /F(point.minimum_heat_capacity_j_k)))
    _require(F(inverse.temperature_error_bound_k)>=expected_T, 'underreported_source_temperature_error')
    # Recheck the saved residual/resolution using the original closure arithmetic.
    # The liquid volume's EOS error remains the explicitly declared hypothesis.
    ng=math.fsum(state.gas_amounts_mol);r=mechanical.gas_constant_j_mol_k;t=point.temperature_k
    nrt=ng*r*t
    nrt_resolution=math.fsum((math.ulp(ng)*r*t,math.ulp(ng*r)*t,math.ulp(nrt)))
    vg,_,rp,rv,vr,pr=closure_diagnostics(storage.volume.value_m3,mechanical.liquid_volume_m3,
                                       point.pressure_pa,nrt,nrt_resolution)
    _require(_same((mechanical.gas_volume_m3,mechanical.pressure_residual_pa,mechanical.volume_residual_m3,
                    mechanical.volume_resolution_m3,mechanical.pressure_resolution_pa),(vg,rp,rv,vr,pr)),
             'source_closure_residual_or_resolution_changed')
    nominal=F(liquid_pressure_error_bound(mechanical,template.envelope,mechanical.gas_constant_j_mol_k))
    _require(F(fluid.pressure_error_bound_pa)>=nominal, 'underreported_fluid_pressure_error')
    global_error,extra,local_error=wet_fluid_pressure_bounds(template,fluid,state.gas_amounts_mol,
                                                          point.temperature_k,F(storage.volume.error_m3))
    _require(F(point.global_pressure_error_pa)>=global_error
             and F(point.extra_pressure_error_pa)>=extra and F(point.pressure_error_pa)>=F(local_error),
             'underreported_source_volume_pressure_error')
    env=template.envelope
    # Both admitted water backends enforce 293..500 K and <=100 MPa.
    # Source temperature admission is narrower and is intersected explicitly.
    from .water_properties import _MIN_T, _MAX_T, _MAX_PRESSURE_PA
    tdomain=(max(F(storage.temperature_domain_k[0]),F(env.temperature_range_k[0]),F(_MIN_T)),
             min(F(storage.temperature_domain_k[1]),F(env.temperature_range_k[1]),F(_MAX_T)))
    pdomain=(F(template.mechanical.pressure_bracket_pa[0]),
             min(F(template.mechanical.pressure_bracket_pa[1]),F(_MAX_PRESSURE_PA)))
    continuation=propagate_declared_pressure(F(state.liquid_water_mol),sum(map(F,state.gas_amounts_mol),F()),
        F(mechanical.gas_constant_j_mol_k),F(env.liquid_abs_du_dp_bound_j_mol_pa),
        F(point.temperature_k),F(inverse.temperature_error_bound_k),F(point.pressure_pa),F(point.pressure_error_pa),
        temperature_domain_k=tdomain,pressure_domain_pa=pdomain)
    return SourceInversePressure(storage,state,inverse,storage.model_identity,_digest((state,inverse)),
                                 (nominal,global_error,extra,F(local_error)),continuation)


@dataclass(frozen=True)
class SourceTrialPressure:
    comparison: SourceEndpointComparison
    endpoint_bounds: tuple[tuple[SourceInversePressure, SourceInversePressure], ...]
    conditional_cell_bounds_pa: tuple[F | None, ...]
    maximum_conditional_bound_pa: F | None
    conditional_gate: bool | None
    source_certified: bool = False
    event_admitted: bool = False

    def check(self) -> None:
        _require(type(self.endpoint_bounds) is tuple and bool(self.endpoint_bounds)
                 and all(type(pair) is tuple and len(pair)==2
                         and all(type(v) is SourceInversePressure for v in pair) for pair in self.endpoint_bounds),
                 'complete_source_pressure_endpoint_pairs_required')
        expected=propagate_source_trial_pressure(self.comparison)
        for pair in self.endpoint_bounds:
            for bound in pair:
                bound.check()
        _require(all(_same(getattr(self,f.name),getattr(expected,f.name))
                     for f in fields(self) if f.name not in ('comparison','endpoint_bounds'))
                 and len(self.endpoint_bounds)==len(expected.endpoint_bounds)
                 and all(a.input_binding==b.input_binding and a.storage_identity==b.storage_identity
                         for pair,want in zip(self.endpoint_bounds,expected.endpoint_bounds) for a,b in zip(pair,want)),
                 'source_trial_pressure_changed')


def propagate_source_trial_pressure(comparison: SourceEndpointComparison) -> SourceTrialPressure:
    """Add conditional full-T pressure accounting without replacing event gates."""
    _require(type(comparison) is SourceEndpointComparison, 'actual_source_endpoint_comparison_required')
    comparison.check()
    observations=(comparison.trial.captures[2].evaluation,comparison.trial.captures[-1].evaluation)
    pairs=tuple(tuple(enclose_source_inverse_pressure(storage,obs.source_states[i],
                  obs.source_evaluation.cells[i].inverse) for obs in observations)
                for i,storage in enumerate(comparison.trial.adapter.column.storages))
    differences=[]
    for a,b in pairs:
        if a.continuation.status!=b.continuation.status or a.continuation.status!='conditional_pressure_enclosure':
            differences.append(None)
        else:
            differences.append(abs(F(a.inverse.point.pressure_pa)-F(b.inverse.point.pressure_pa))
                               +a.continuation.radius_pa+b.continuation.radius_pa)
    maximum=max(differences) if all(v is not None for v in differences) else None
    gate=(maximum<=F(comparison.event_policy.pressure_absolute_pa)
          if maximum is not None and comparison.event_policy is not None else None)
    return SourceTrialPressure(comparison,pairs,tuple(differences),maximum,gate)
