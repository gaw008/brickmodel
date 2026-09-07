"""Explicit finite-rate liquid/ideal-water transfer at an existing interface.

The pressure-difference conductance is supplied, not derived from equilibrium.
Only equimolar phase inventories change; stored U receives no second latent heat.
"""
from dataclasses import dataclass
from fractions import Fraction
import math
from numbers import Real

import numpy as np

from .ideal_water_vapor import IdealWaterVapor,IdealWaterVaporError
from .integration import ConservedState,DomainExit,IntegrationError,Rates
from .rigid_fluid_heat import FluidHeatEvaluation,RigidFluidHeat
from .water_chemical_potential import WaterChemicalError,WaterChemicalPotential,WaterPhaseEquilibrium
from .water_properties import WaterDomainError,WaterNumericalError


class WaterPhaseTransferError(IntegrationError):
    """Invalid finite-rate contract or unrepresentable phase-source computation."""


def _num(value,name,*,nonnegative=False):
    try:value=float(value) if isinstance(value,Real) and not isinstance(value,bool) else math.nan
    except (ValueError,OverflowError):value=math.nan
    if not math.isfinite(value) or (nonnegative and value<0):
        raise WaterPhaseTransferError('invalid_'+name)
    return value


def _float_exact(value,name):
    try:result=float(value)
    except OverflowError as exc:raise WaterPhaseTransferError('unrepresentable_'+name) from exc
    if not math.isfinite(result) or (value and result==0):
        raise WaterPhaseTransferError('unrepresentable_'+name)
    return result


def _label(value):
    return isinstance(value,str) and bool(value) and value==value.strip()


@dataclass(frozen=True)
class CellWaterTransfer:
    rate_mol_s: float
    coefficient_mol_s_pa: float
    vapor_partial_pressure_pa: float | None
    equilibrium: WaterPhaseEquilibrium | None
    vapor_chemical_potential_j_mol: float | None
    driving_chemical_potential_j_mol: float | None
    entropy_production_w_k: float | None
    status: str
    driving_force_definition: str = 'R_T_log_of_computed_equilibrium_pressure_over_vapor_pressure'


@dataclass(frozen=True)
class WaterTransferEvaluation:
    rates: Rates
    base_evaluation: FluidHeatEvaluation
    cell_transfers: tuple[CellWaterTransfer,...]
    coefficient_set_id: str
    coefficient_version: str
    coefficient_classification: str
    source_ids: tuple[str,...]
    qualification: str = 'declared_pressure_difference_kinetics_existing_liquid_interface_not_sludge_nucleation'


@dataclass(frozen=True,kw_only=True)
class WaterPhaseTransfer:
    base_model: RigidFluidHeat
    chemical: WaterChemicalPotential
    coefficients_mol_s_pa: tuple[float,...]
    coefficient_set_id: str
    coefficient_version: str
    coefficient_classification: str
    coefficient_source_ids: tuple[str,...]
    allow_manufactured: bool = False

    def __post_init__(self):
        if type(self.base_model) is not RigidFluidHeat or type(self.chemical) is not WaterChemicalPotential:
            raise WaterPhaseTransferError('explicit_fluid_and_chemical_models_required')
        if 'H2O' not in self.base_model.gas_species_order:
            raise WaterPhaseTransferError('explicit_gas_water_species_required')
        values=self.coefficients_mol_s_pa
        if not isinstance(values,(tuple,list)) or len(values)!=len(self.base_model.storages):
            raise WaterPhaseTransferError('explicit_per_cell_rate_coefficients_required')
        coefficients=tuple(_num(v,'phase_transfer_coefficient',nonnegative=True) for v in values)
        object.__setattr__(self,'coefficients_mol_s_pa',coefficients)
        if type(self.allow_manufactured) is not bool:
            raise WaterPhaseTransferError('invalid_manufactured_gate')
        if self.coefficient_classification not in ('manufactured_test_fixture','literature_constitutive_model','derived_from_evidence'):
            raise WaterPhaseTransferError('invalid_coefficient_classification')
        if not _label(self.coefficient_set_id) or not _label(self.coefficient_version):
            raise WaterPhaseTransferError('explicit_coefficient_identity_required')
        sources=self.coefficient_source_ids
        if (not isinstance(sources,(tuple,list)) or not sources or any(not _label(v) for v in sources)
                or len(set(sources))!=len(sources)):
            raise WaterPhaseTransferError('explicit_unique_coefficient_sources_required')
        object.__setattr__(self,'coefficient_source_ids',tuple(sources))
        manufactured=(self.coefficient_classification=='manufactured_test_fixture'
                      or self.base_model.coefficient_classification=='manufactured'
                      or any(p.metadata.classification=='manufactured_test_fixture'
                             for s in self.base_model.storages for p in s.gas_phases.values()))
        if manufactured and not self.allow_manufactured:
            raise WaterPhaseTransferError('manufactured_requires_explicit_test_mode')
        for storage,k in zip(self.base_model.storages,coefficients):
            if k==0:continue
            vapor=storage.gas_phases['H2O'].caloric
            if (type(vapor) is not IdealWaterVapor
                    or vapor.method_id!=self.chemical.caloric_method_id
                    or vapor.reference!=self.chemical.reference
                    or vapor.source_asset_sha256!=self.chemical.source_asset_sha256
                    or vapor.gas_constant_j_mol_k!=self.chemical.gas_constant_j_mol_k
                    or storage.mechanical.water.reference!=self.chemical.reference
                    or storage.mechanical.water.source_asset_sha256!=self.chemical.source_asset_sha256):
                raise WaterPhaseTransferError('phase_transfer_requires_matching_ideal_water_caloric_bridge')

    @property
    def species_order(self):return self.base_model.species_order

    @property
    def material_qualified(self):return False

    @property
    def source_ids(self):
        return tuple(sorted(set(self.base_model.source_ids+self.chemical.source_ids+self.coefficient_source_ids)))

    def evaluate(self,state:ConservedState,time_s:float)->WaterTransferEvaluation:
        self.base_model._check_state(state)
        for row,k in zip(state.amounts_mol,self.coefficients_mol_s_pa):
            if k>0 and row[0]==0:
                raise DomainExit('no_existing_liquid_interface_nucleation_not_modelled')
        base=self.base_model.evaluate(state,time_s)
        water_index=self.species_order.index('H2O')
        reactions=np.array(base.rates.reaction_species_mol_s)
        diagnostics=[]
        for row,closed,k in zip(state.amounts_mol,base.storage_states,self.coefficients_mol_s_pa):
            if k==0:
                diagnostics.append(CellWaterTransfer(0.,k,None,None,None,None,None,'disabled'))
                continue
            mechanical=closed.mechanical
            temperature=mechanical.temperature_k
            # Individual partial pressure from its actual N and current gas V;
            # do not lose a trace species in an intermediate N_water/N_total.
            pressure=_float_exact(Fraction(float(row[water_index]))*Fraction(self.chemical.gas_constant_j_mol_k)
                *Fraction(temperature)/Fraction(mechanical.gas_volume_m3),'water_partial_pressure')
            try:
                equilibrium=self.chemical.equilibrium_at_liquid_tp(temperature,mechanical.liquid_pressure_pa)
                peq=equilibrium.equilibrium_partial_pressure_pa
                rate=_float_exact(Fraction(k)*(Fraction(peq)-Fraction(pressure)),'phase_transfer_rate')
                if pressure==0:
                    mu=delta_mu=entropy=None
                    status='zero_vapor_limit'
                else:
                    mu=self.chemical.ideal_vapor(temperature,pressure).chemical_potential_j_mol
                    difference=peq-pressure
                    logarithm=(math.log1p(difference/pressure) if abs(difference)<.5*pressure
                               else math.log(peq)-math.log(pressure))
                    delta_mu=_float_exact(Fraction(self.chemical.gas_constant_j_mol_k)
                        *Fraction(temperature)*Fraction(logarithm),'chemical_driving_force')
                    if difference and delta_mu==0:
                        raise WaterPhaseTransferError('unresolvable_chemical_driving_force')
                    entropy=_float_exact(Fraction(rate)*Fraction(delta_mu)/Fraction(temperature),'entropy_production')
                    if entropy<0:raise WaterPhaseTransferError('phase_rate_chemical_direction_mismatch')
                    status='equilibrium_at_computed_pressure' if rate==0 else 'finite_vapor_pressure'
            except WaterDomainError as exc:raise DomainExit(str(exc)) from exc
            except (WaterChemicalError,WaterNumericalError,IdealWaterVaporError) as exc:
                raise WaterPhaseTransferError(str(exc)) from exc
            index=len(diagnostics)
            reactions[index,0]-=rate
            reactions[index,water_index]+=rate
            diagnostics.append(CellWaterTransfer(rate,k,pressure,equilibrium,mu,delta_mu,entropy,status))
        rates=Rates(base.rates.face_species_mol_s,base.rates.face_energy_w,reactions,base.rates.cell_power_w)
        return WaterTransferEvaluation(rates,base,tuple(diagnostics),self.coefficient_set_id,self.coefficient_version,
                                       self.coefficient_classification,self.source_ids)

    def __call__(self,state,time_s):return self.evaluate(state,time_s).rates
