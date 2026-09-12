"""Reduced common-tangent slab mechanics with explicit local constraint work.

This manufactured diagonal ansatz balances normal traction in each cell and
aggregate transverse virtual work. It does not enforce pointwise free traction
on every lateral surface of a heterogeneous three-dimensional brick.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from .reacting_skeleton_energy import ManufacturedReactingSkeletonEnergy
from .skeleton_energy import DiagonalSkeletonEnergy,SkeletonEnergyState,_iv,_number,_output
from .free_skeleton_rates import FreeSkeletonRatesError,_enclosure,_upper


@dataclass(frozen=True)
class FreeSlabRates:
    rates: tuple[float,...]
    rate_error_bounds: tuple[float,...]
    states: tuple[SkeletonEnergyState,...]
    normal_traction_residuals_pa: tuple[float,...]
    normal_traction_residual_errors_pa: tuple[float,...]
    tangential_constraint_piola_pa: tuple[float,...]
    tangential_constraint_errors_pa: tuple[float,...]
    weighted_tangential_residual_j: float
    weighted_tangential_residual_error_j: float
    volume_rates_m3_s: tuple[float,...]
    volume_rate_errors_m3_s: tuple[float,...]
    external_powers_w: tuple[float,...]
    external_power_errors_w: tuple[float,...]
    constraint_powers_w: tuple[float,...]
    constraint_power_errors_w: tuple[float,...]
    constraint_power_sum_w: float
    constraint_power_sum_error_w: float
    cell_power_residuals_w: tuple[float,...]
    cell_power_residual_errors_w: tuple[float,...]
    global_power_residual_w: float
    global_power_residual_error_w: float
    pore_pressures_pa: tuple[float,...]
    external_pressure_pa: float
    zero_balance_enclosed: bool
    model_identity: tuple
    source_ids: tuple[str,...]
    qualification: str='manufactured_fixed_solid_reduced_common_tangent_slab_instantaneous_rates'
    error_scope: str=(
        'Bounds enclose arithmetic at represented inputs. Balance errors include '
        'solved-rate representation enclosures. Local tangential constraint and '
        'constraint-power errors are fixed represented-rate evaluation bounds; '
        'these physical reactions need not vanish. No pressure/geometry/parameter '
        'uncertainty, constitutive accuracy, trajectory or material admission.')


def _field(state,name,index=None):
    value=getattr(state,name);error=state.numerical_error_bounds[name]
    if index is not None:value,error=value[index],error[index]
    return _enclosure(value,error)


def _pairs(values):
    return tuple(v for v,_ in values),tuple(e for _,e in values)


def solve_free_slab_rates(skeletons,*,normal_stretches,tangential_stretch,
                         pore_pressures_pa,external_pressure_pa,solid_inventories_mol,solid_inventory_regime='fixed_solid'):
    """Solve n_i rates and one common t rate, retaining per-cell reaction power.

    R_i = P_t_i - (p_i-pe)*n_i*t is the generalized constraint reaction.
    sum(V0_i*R_i)=0; C_i=2*V0_i*R_i*tdot must enter each total-energy RHS.
    The local power identity is Erec_dot+D-p_i*Vdot_i = -pe*Vdot_i+C_i.
    """
    if solid_inventory_regime not in ('fixed_solid','reacting_manufactured'):
        raise FreeSkeletonRatesError('explicit_solid_inventory_regime_required')
    reacting=solid_inventory_regime=='reacting_manufactured'
    expected_type=ManufacturedReactingSkeletonEnergy if reacting else DiagonalSkeletonEnergy
    if (type(skeletons) is not tuple or not skeletons or
            any(type(s) is not expected_type for s in skeletons)):
        raise FreeSkeletonRatesError('explicit_ordered_slab_skeletons_required')
    count=len(skeletons);reference=skeletons[0].reference
    if reference.cells!=count or any(s.reference!=reference or s.cell_index!=i
                                     for i,s in enumerate(skeletons)):
        raise FreeSkeletonRatesError('matching_complete_reference_cell_order_required')
    if any(type(v) is not tuple or len(v)!=count for v in
           (normal_stretches,pore_pressures_pa,solid_inventories_mol)):
        raise FreeSkeletonRatesError('complete_slab_state_tuples_required')
    n=tuple(_number(v,'normal_stretch',positive=True) for v in normal_stretches)
    t=_number(tangential_stretch,'tangential_stretch',positive=True)
    pores=tuple(_number(v,'pore_pressure',nonnegative=True) for v in pore_pressures_pa)
    pe=_number(external_pressure_pa,'external_pressure',nonnegative=True)
    eta=tuple(F(_number((s.reference_model if reacting else s).viscosity_pa_s,'viscosity',positive=True)) for s in skeletons)
    volumes=tuple(F(s.reference_volume_m3) for s in skeletons)
    static=tuple(s.evaluate(normal_stretch=ni,tangential_stretch=t,
        normal_rate_per_s=0.,tangential_rate_per_s=0.,solid_inventory_mol=inventory)
        for s,ni,inventory in zip(skeletons,n,solid_inventories_mol,strict=True))
    if reacting:
        # The actual provider above validates complete current N/domain. Retain
        # exact binary q and eta multiplication; no rounded coefficient or
        # off-domain probe is introduced into the positive denominator.
        eta=tuple(viscosity*(F(s.composition_offset)+sum(
            (F(weight)*F(_number(inventory[key],'solid_mol',nonnegative=True))
             for key,weight in s.composition_weights_per_mol),F()))
            for s,inventory,viscosity in zip(skeletons,solid_inventories_mol,eta,strict=True))
    tangent=F(t);normals=tuple(map(F,n));normal_solutions=[];tangent_drive=_iv(0)
    for state,ni,p,v,viscosity in zip(static,normals,pores,volumes,eta,strict=True):
        normal_drive=(F(p)-F(pe))*tangent**2-_field(state,'elastic_piola_pa',0)-_field(state,'interface_piola_pa',0)
        normal_solutions.append(_output(ni**2/viscosity*normal_drive))
        tangent_drive+=v*((F(p)-F(pe))*ni*tangent-_field(state,'elastic_piola_pa',1)-_field(state,'interface_piola_pa',1))
    weighted_eta=sum((v*e for v,e in zip(volumes,eta,strict=True)),F())
    tangent_solution=_output(tangent**2/weighted_eta*tangent_drive)
    rates,rate_errors=_pairs(tuple(normal_solutions)+(tangent_solution,))
    states=tuple(s.evaluate(normal_stretch=ni,tangential_stretch=t,
        normal_rate_per_s=rate,tangential_rate_per_s=rates[-1],solid_inventory_mol=inventory)
        for s,ni,rate,inventory in zip(skeletons,n,rates[:-1],solid_inventories_mol,strict=True))
    td=F(rates[-1]);te=F(rate_errors[-1])
    normal_residuals=[];constraints=[];vdots=[];external=[];constraint_powers=[];local_powers=[]
    weighted_tangent=_iv(0);global_power=_iv(0);normal_power_error=F()
    for i,(state,ni,p,v,viscosity) in enumerate(zip(states,normals,pores,volumes,eta,strict=True)):
        nd=F(rates[i]);ne=F(rate_errors[i])
        stresses=tuple(sum((_field(state,key,j) for key in
            ('elastic_piola_pa','interface_piola_pa','viscous_piola_pa')),_iv(0)) for j in (0,1))
        rn=stresses[0]-(F(p)-F(pe))*tangent**2
        rt=stresses[1]-(F(p)-F(pe))*ni*tangent
        rn_value,rn_error=_output(rn)
        normal_residuals.append((rn_value,_upper(F(rn_error)+viscosity*ne/ni**2)))
        constraints.append(_output(rt));weighted_tangent+=v*rt
        vdot=v*(tangent**2*nd+2*ni*tangent*td)
        vdots.append(_output(vdot));external.append(_output(-F(pe)*vdot))
        constraint_powers.append(_output(2*v*td*rt))
        # Re-evaluate the actual final-state power identity, not a forced zero.
        power=sum((_field(state,key) for key in
                   ('elastic_rate_w','interface_rate_w','dissipation_w')),_iv(0))
        power-=F(p)*_enclosure(*vdots[-1])+_enclosure(*external[-1])
        global_power+=power
        local=power-_enclosure(*constraint_powers[-1])
        local_value,local_error=_output(local)
        rate_power_error=v*abs(nd)*viscosity*ne/ni**2
        normal_power_error+=rate_power_error
        local_powers.append((local_value,_upper(F(local_error)+rate_power_error)))
    wt,wte=_output(weighted_tangent)
    tangent_force_error=weighted_eta*te/tangent**2
    wte=_upper(F(wte)+tangent_force_error)
    constraint_sum=sum((_enclosure(*item) for item in constraint_powers),_iv(0))
    cp,cpe=_output(constraint_sum)
    tangent_power_error=2*abs(td)*tangent_force_error
    cpe=_upper(F(cpe)+tangent_power_error)
    gp,gpe=_output(global_power)
    gpe=_upper(F(gpe)+normal_power_error+tangent_power_error)
    normal_values,normal_errors=_pairs(normal_residuals)
    constraint_values,constraint_errors=_pairs(constraints)
    volume_values,volume_errors=_pairs(vdots)
    external_values,external_errors=_pairs(external)
    cp_values,cp_errors=_pairs(constraint_powers)
    local_values,local_errors=_pairs(local_powers)
    checks=normal_residuals+local_powers+[(wt,wte),(cp,cpe),(gp,gpe)]
    enclosed=all(abs(F(value))<=F(error) for value,error in checks)
    result=FreeSlabRates(rates,rate_errors,states,normal_values,normal_errors,
        constraint_values,constraint_errors,wt,wte,volume_values,volume_errors,
        external_values,external_errors,cp_values,cp_errors,cp,cpe,local_values,local_errors,
        gp,gpe,pores,pe,enclosed,
        ('manufactured_common_tangent_slab_v1',tuple(s.identity for s in skeletons),
         'normal_local_transverse_weighted_virtual_work_positive_viscosity',
         'local_constraint_power_required_no_pointwise_lateral_traction_claim'),
        tuple(sorted({source for s in skeletons for source in s.source_ids})))

    if reacting:
        return replace(result,
            model_identity=('manufactured_reacting_common_tangent_slab_v1',tuple(s.identity for s in skeletons),
                'effective_viscosity=q_current_N_times_reference_eta_exact_fraction',
                'fixed_composition_deformation_balance_local_constraint_work_no_chemical_external_heat'),
            qualification='manufactured_reacting_reduced_common_tangent_fixed_composition_instantaneous_rates')
    return result
