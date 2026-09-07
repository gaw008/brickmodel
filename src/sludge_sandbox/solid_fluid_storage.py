"""Fixed bulk-volume solid inventories coupled to actual water/gas closure.

All uncertainty conclusions remain conditional on declared global envelopes.
Solid molar volumes are constant in T/P; no deformation or phase change is added.
"""
from dataclasses import dataclass, replace
from fractions import Fraction
import math
from types import MappingProxyType
from typing import Mapping

from .incompressible_solid import IncompressibleSolidPhase
from .phase_storage import PhasePoint, InversePolicy
from .rigid_storage import (RigidStorage, RigidStorageError, ClosedStorageState,
                            _num as _base_num, _range, _sum, _sum_upper, _directed, _product_upper)
from .rigid_water_gas import RigidWaterGasState


class SolidFluidStorageError(RigidStorageError):
    """Invalid complete inventory/geometry or failed conditional inverse budget."""


def _num(*args,**kwargs):
    try:return _base_num(*args,**kwargs)
    except RigidStorageError as exc:raise SolidFluidStorageError(str(exc)) from exc


def _float(x):
    try:v=float(x)
    except OverflowError as exc:raise SolidFluidStorageError('unrepresentable_solid_fluid_value') from exc
    if not math.isfinite(v) or (x and v==0):raise SolidFluidStorageError('unrepresentable_solid_fluid_value')
    return v


@dataclass(frozen=True)
class SolidFluidState:
    mechanical: RigidWaterGasState
    fluid_state: ClosedStorageState
    solid_points: Mapping[str,PhasePoint]
    solid_inventory_mol: Mapping[str,float]
    solid_volume_m3: float
    available_pore_volume_m3: float
    internal_energy_j: float
    enthalpy_j: float
    closed_heat_capacity_j_k: float
    minimum_heat_capacity_j_k: float
    energy_roundoff_j: float
    volume_error_bound_m3: float
    pressure_error_bound_pa: float
    energy_error_bound_j: float
    source_ids: tuple[str,...]
    qualification: str = 'conditional_declared_global_fluid_and_solid_bounds_not_independently_admitted'
    energy_scope: str = 'fixed_bulk_incompressible_solid_and_fluid_thermal_no_strain_or_interface_energy'


@dataclass(frozen=True)
class SolidFluidInverse:
    state: SolidFluidState
    target_energy_j: float
    energy_residual_j: float
    temperature_error_bound_k: float
    final_temperature_bracket_k: tuple[float,float]
    iterations: int
    policy: InversePolicy
    target_energy_error_bound_j: float = 0.


@dataclass(frozen=True,kw_only=True)
class SolidFluidStorage:
    fluid_template: RigidStorage
    solid_phases: Mapping[str,IncompressibleSolidPhase]
    bulk_volume_m3: float
    bulk_volume_error_m3: float
    geometry_source_ids: tuple[str,...]
    geometry_id: str
    geometry_version: str
    geometry_classification: str
    allow_manufactured: bool = False

    def __post_init__(self):
        if type(self.fluid_template) is not RigidStorage or not isinstance(self.solid_phases,Mapping) or not self.solid_phases:
            raise SolidFluidStorageError('explicit_fluid_and_solid_providers_required')
        object.__setattr__(self,'bulk_volume_m3',_num(self.bulk_volume_m3,'bulk_volume',positive=True))
        object.__setattr__(self,'bulk_volume_error_m3',_num(self.bulk_volume_error_m3,'bulk_volume_error',nonnegative=True))
        if self.bulk_volume_error_m3>=self.bulk_volume_m3:raise SolidFluidStorageError('bulk_volume_uncertainty_excludes_positive_domain')
        if (not isinstance(self.geometry_source_ids,tuple) or not self.geometry_source_ids
                or any(not isinstance(v,str) or not v or v!=v.strip() for v in self.geometry_source_ids)
                or len(set(self.geometry_source_ids))!=len(self.geometry_source_ids)):
            raise SolidFluidStorageError('explicit_geometry_sources_required')
        if any(not isinstance(x,str) or not x or x!=x.strip() for x in (self.geometry_id,self.geometry_version)):
            raise SolidFluidStorageError('explicit_geometry_identity_required')
        if self.geometry_classification not in ('manufactured_test_fixture','literature_constitutive_model','derived_from_evidence','virtual_design_choice'):
            raise SolidFluidStorageError('invalid_geometry_classification')
        if type(self.allow_manufactured) is not bool:raise SolidFluidStorageError('invalid_manufactured_gate')
        if self.geometry_classification=='manufactured_test_fixture' and not self.allow_manufactured:
            raise SolidFluidStorageError('manufactured_opt_in_required')
        for key,phase in self.solid_phases.items():
            if not isinstance(key,str) or not key or key!=key.strip() or type(phase) is not IncompressibleSolidPhase:
                raise SolidFluidStorageError('identity_bearing_solid_provider_required')
            m=phase.metadata
            if m.species_id!=key or m.energy_reference_id!='nist_298.15K_element_standard_formation' or m.molar_basis_id!='mol_of_declared_species':
                raise SolidFluidStorageError('solid_identity_or_reference_mismatch')
            if key in self.fluid_template.gas_phases and m.molar_mass_kg_mol!=self.fluid_template.gas_phases[key].metadata.molar_mass_kg_mol:
                raise SolidFluidStorageError('cross_phase_molar_mass_mismatch')
            if key=='H2O' and m.molar_mass_kg_mol!=self.fluid_template.mechanical.water.reference.molar_mass_kg_mol:
                raise SolidFluidStorageError('cross_phase_water_molar_mass_mismatch')
            if m.classification=='manufactured_test_fixture' and not self.allow_manufactured:
                raise SolidFluidStorageError('manufactured_opt_in_required')
            lo,hi=self.fluid_template.mechanical.pressure_bracket_pa
            if not phase.pressure_range_pa[0]<=lo<hi<=phase.pressure_range_pa[1]:
                raise SolidFluidStorageError('fluid_pressure_bracket_outside_solid_domain')
        if not self.allow_manufactured and any(p.metadata.classification=='manufactured_test_fixture' for p in self.fluid_template.gas_phases.values()):
            raise SolidFluidStorageError('manufactured_opt_in_required')
        object.__setattr__(self,'solid_phases',MappingProxyType(dict(self.solid_phases)))

    @property
    def source_ids(self):
        sources=list(self.geometry_source_ids+self.fluid_template.envelope.source_ids+
                     self.fluid_template.mechanical.water.reference.source_ids+
                     self.fluid_template.mechanical.constant_source_ids)
        for p in (*self.solid_phases.values(),*self.fluid_template.gas_phases.values()):sources.extend(p.metadata.source_ids)
        return tuple(sorted(set(sources)))

    @property
    def material_qualified(self):return False

    def evaluate_at_temperature(self,temperature_k,liquid_mol,gas_mol,solid_mol):
        if not isinstance(solid_mol,Mapping) or set(solid_mol)!=set(self.solid_phases):
            raise SolidFluidStorageError('complete_solid_inventory_keys_required')
        amounts={k:_num(n,'solid_inventory',nonnegative=True) for k,n in solid_mol.items()}
        exact_vs=sum((Fraction(n)*Fraction(self.solid_phases[k].molar_volume_m3_mol) for k,n in amounts.items()),Fraction())
        exact_available=Fraction(self.bulk_volume_m3)-exact_vs
        if exact_available<=0:raise SolidFluidStorageError('no_positive_fluid_available_volume')
        available=_float(exact_available)
        error_v=Fraction(self.bulk_volume_error_m3)+abs(Fraction(available)-exact_available)
        error_v+=sum((Fraction(n)*Fraction(self.solid_phases[k].declared_v_error_m3_mol) for k,n in amounts.items()),Fraction())
        if error_v>=exact_available:raise SolidFluidStorageError('available_volume_uncertainty_excludes_positive_domain')
        fluid=replace(self.fluid_template,mechanical=replace(self.fluid_template.mechanical,available_pore_volume_m3=available))
        f=fluid.evaluate_at_temperature(temperature_k,liquid_mol,gas_mol)
        t,p=f.mechanical.temperature_k,f.mechanical.pressure_pa
        ng=sum(map(Fraction,f.mechanical.gas_inventory_mol.values()),Fraction())
        bmin=ng*Fraction(fluid.mechanical.gas_constant_j_mol_k)*Fraction(t)/Fraction(fluid.envelope.pressure_range_pa[1])**2
        if bmin<=0:raise SolidFluidStorageError('no_positive_gas_pressure_slope')
        extra_p=_directed(error_v/bmin,upper=True)
        pressure_error=_sum_upper((f.pressure_error_bound_pa,extra_p))
        plo,phi=fluid.mechanical.pressure_bracket_pa
        if not Fraction(plo)<=Fraction(p)-Fraction(pressure_error)<=Fraction(p)+Fraction(pressure_error)<=Fraction(phi):
            raise SolidFluidStorageError('pressure_uncertainty_outside_envelope')
        points={};ut=[f.internal_energy_j];ht=[f.enthalpy_j];ct=[f.closed_heat_capacity_j_k]
        lower=Fraction(f.minimum_heat_capacity_j_k);rounding=[];errors=[f.energy_error_bound_j]
        for key,n in amounts.items():
            if not n:continue
            phase=self.solid_phases[key]
            point=phase.evaluate(t,p);points[key]=point
            u=_float(Fraction(n)*Fraction(point.internal_energy_j_mol))
            h=_float(Fraction(n)*Fraction(point.enthalpy_j_mol))
            ut.append(u);ht.append(h);ct.append(_float(Fraction(n)*Fraction(phase.cv_j_mol_k(t))))
            lower+=Fraction(n)*Fraction(phase.cp_lower_bound_j_mol_k)
            rounding.extend((_product_upper(n,math.ulp(point.internal_energy_j_mol)),math.ulp(u)))
            errors.append(_product_upper(n,phase.declared_u_error_j_mol))
        total_u,total_h=_sum(ut),_sum(ht)
        added_roundoff=_sum_upper(rounding+[math.ulp(total_u)])
        errors.extend((added_roundoff,_product_upper(f.mechanical.liquid_inventory_mol,
            fluid.envelope.liquid_abs_du_dp_bound_j_mol_pa,extra_p)))
        cmin=_directed(lower,upper=False)
        capacity=_sum(ct)
        if not 0<cmin<=capacity:raise SolidFluidStorageError('invalid_total_heat_capacity_bound')
        return SolidFluidState(f.mechanical,f,MappingProxyType(points),MappingProxyType(amounts),_float(exact_vs),available,
            total_u,total_h,capacity,cmin,_sum_upper((f.energy_roundoff_j,added_roundoff)),
            _directed(error_v,upper=True),pressure_error,_sum_upper(errors),self.source_ids)

    def temperature_from_energy(self,target_energy_j,liquid_mol,gas_mol,solid_mol,temperature_bracket_k,policy,
                                *,target_energy_error_bound_j=0.):
        """Invert a target interval, including upstream energy-subtraction error.

        The bound is additional to the existing target representation budget.
        It participates in bracket signs, residual/radius and acceptance gates.
        """
        target=_num(target_energy_j,'target_energy')
        _num(target_energy_error_bound_j,'target_energy_error_bound',nonnegative=True)
        try:
            exact_error=Fraction(target_energy_error_bound_j)
        except (TypeError,ValueError,OverflowError) as exc:
            raise SolidFluidStorageError('invalid_target_energy_error_bound') from exc
        if exact_error<0:
            raise SolidFluidStorageError('invalid_target_energy_error_bound')
        try:
            target_error=_directed(exact_error,upper=True)
            tr=_sum_upper((math.ulp(target),target_error))
        except RigidStorageError as exc:
            raise SolidFluidStorageError(str(exc)) from exc
        if type(policy) is not InversePolicy:raise SolidFluidStorageError('explicit_inverse_policy_required')
        lo,hi=_range(temperature_bracket_k)
        low=self.evaluate_at_temperature(lo,liquid_mol,gas_mol,solid_mol)
        high=self.evaluate_at_temperature(hi,liquid_mol,gas_mol,solid_mol)
        if not (Fraction(low.internal_energy_j)+Fraction(low.energy_error_bound_j)+Fraction(tr)<Fraction(target)
                <Fraction(high.internal_energy_j)-Fraction(high.energy_error_bound_j)-Fraction(tr)):
            if target<low.internal_energy_j-low.energy_error_bound_j-tr or target>high.internal_energy_j+high.energy_error_bound_j+tr:
                raise SolidFluidStorageError('energy_outside_closed_temperature_bracket')
            raise SolidFluidStorageError('initial_energy_bracket_sign_uncertain')
        mid=lo+(hi-lo)/2
        for iteration in range(policy.maximum_iterations+1):
            point=self.evaluate_at_temperature(mid,liquid_mol,gas_mol,solid_mol)
            residual=_sum((point.internal_energy_j,-target))
            budget=_sum_upper((point.energy_error_bound_j,tr,math.ulp(residual)))
            residual_bound=_sum_upper((abs(residual),budget))
            radius=_directed(Fraction(residual_bound)/Fraction(point.minimum_heat_capacity_j_k),upper=True)
            if residual_bound<=policy.energy_tolerance_j and radius<=policy.temperature_tolerance_k:
                left=_directed(max(Fraction(lo),Fraction(mid)-Fraction(radius)),upper=False)
                right=_directed(min(Fraction(hi),Fraction(mid)+Fraction(radius)),upper=True)
                return SolidFluidInverse(point,target,residual,radius,(left,right),iteration,policy,target_error)
            if budget>policy.energy_tolerance_j or Fraction(budget)/Fraction(point.minimum_heat_capacity_j_k)>Fraction(policy.temperature_tolerance_k):
                raise SolidFluidStorageError('numerical_envelope_or_representation_exceeds_inverse_tolerance')
            if abs(residual)<=budget:raise SolidFluidStorageError('energy_direction_unresolved_by_declared_envelope')
            if mid in (lo,hi):raise SolidFluidStorageError('temperature_bracket_unresolvable')
            if residual>0:hi=mid
            else:lo=mid
            proposed=mid-residual/point.closed_heat_capacity_j_k
            mid=proposed if math.isfinite(proposed) and lo<proposed<hi else lo+(hi-lo)/2
        raise SolidFluidStorageError('inverse_iteration_limit')
