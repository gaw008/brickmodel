"""Explicit finite-rate liquid/ideal-water transfer at an existing interface.

The pressure-difference conductance is supplied, not derived from equilibrium.
Only equimolar phase inventories change; stored U receives no second latent heat.
"""
from .free_solid_cell import ClosedFreeSolidCell,FreeSolidCellEvaluation
from .free_solid_slab import FreeSolidSlab,FreeSolidSlabEvaluation
from .deforming_solid_heat import DeformingSolidHeat,DeformingSolidHeatEvaluation
from dataclasses import dataclass, replace
from fractions import Fraction
import math
from numbers import Real, Integral

import numpy as np

from .ideal_water_vapor import IdealWaterVapor,IdealWaterVaporError
from .joined_water_vapor import JoinedWaterVapor
from .integration import ConservedState,DomainExit,IntegrationError,Rates
from .rigid_fluid_heat import FluidHeatEvaluation,RigidFluidHeat
from .solid_fluid_heat import SolidFluidHeat,SolidFluidHeatEvaluation
from .programmed_solid_fluid_heat import ProgrammedSolidFluidHeat,ProgrammedSolidFluidEvaluation
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
    hypothetical_equilibrium: WaterPhaseEquilibrium | None = None


@dataclass(frozen=True)
class WaterTransferEvaluation:
    rates: Rates
    base_evaluation: FluidHeatEvaluation | SolidFluidHeatEvaluation | ProgrammedSolidFluidEvaluation | DeformingSolidHeatEvaluation | FreeSolidCellEvaluation | FreeSolidSlabEvaluation
    cell_transfers: tuple[CellWaterTransfer,...]
    coefficient_set_id: str
    coefficient_version: str
    coefficient_classification: str
    source_ids: tuple[str,...]
    qualification: str = 'declared_pressure_difference_kinetics_existing_liquid_interface_not_sludge_nucleation'
    interface_modes: tuple[str,...] = ()
    dry_policy: str = 'strict'


@dataclass(frozen=True,kw_only=True)
class WaterPhaseTransfer:
    base_model: RigidFluidHeat | SolidFluidHeat | ProgrammedSolidFluidHeat | DeformingSolidHeat | ClosedFreeSolidCell | FreeSolidSlab
    chemical: WaterChemicalPotential
    coefficients_mol_s_pa: tuple[float,...]
    coefficient_set_id: str
    coefficient_version: str
    coefficient_classification: str
    coefficient_source_ids: tuple[str,...]
    allow_manufactured: bool = False
    interface_modes: tuple[str,...] | None = None
    dry_policy: str = 'strict'

    def __post_init__(self):
        if type(self.base_model) not in (RigidFluidHeat,SolidFluidHeat,ProgrammedSolidFluidHeat,DeformingSolidHeat,ClosedFreeSolidCell,FreeSolidSlab) or type(self.chemical) is not WaterChemicalPotential:
            raise WaterPhaseTransferError('explicit_fluid_and_chemical_models_required')
        if 'H2O' not in self.base_model.gas_species_order:
            raise WaterPhaseTransferError('explicit_gas_water_species_required')
        modes=self.interface_modes
        if modes is None:modes=('existing_liquid',)*len(self._thermal_host.storages)
        if (not isinstance(modes,(tuple,list)) or len(modes)!=len(self._thermal_host.storages)
                or any(m not in ('existing_liquid','depleted_no_nucleation') for m in modes)):
            raise WaterPhaseTransferError('invalid_interface_modes')
        if self.dry_policy not in ('strict','metastable_no_nucleation'):
            raise WaterPhaseTransferError('invalid_dry_policy')
        if self.interface_modes is not None:
            object.__setattr__(self,'interface_modes',tuple(modes))
        values=self.coefficients_mol_s_pa
        if not isinstance(values,(tuple,list)) or len(values)!=len(self._thermal_host.storages):
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
        manufactured=(self._deforming_host is not None or self.coefficient_classification=='manufactured_test_fixture'
                      or self.base_model.coefficient_classification=='manufactured'
                      or self._thermal_host.coefficient_classification=='manufactured'
                      or any(p.metadata.classification=='manufactured_test_fixture'
                             for s in self._fluid_storages for p in s.gas_phases.values()))
        if type(self._thermal_host) is SolidFluidHeat:
            manufactured = manufactured or self._thermal_host.has_manufactured_reactions or self._thermal_host.has_manufactured_liquid_transport or any(
                s.geometry_classification=='manufactured_test_fixture' for s in self._thermal_host.storages) or any(
                p.metadata.classification=='manufactured_test_fixture'
                for s in self._thermal_host.storages for p in s.solid_phases.values())
        if manufactured and not self.allow_manufactured:
            raise WaterPhaseTransferError('manufactured_requires_explicit_test_mode')
        for storage,k,mode in zip(self._fluid_storages,coefficients,self.interfaces):
            if k==0 and mode=='existing_liquid':continue
            caloric=storage.gas_phases['H2O'].caloric
            # Only the exact source-gated low branch supplies liquid chemistry.
            vapor=caloric.low_model if type(caloric) is JoinedWaterVapor else caloric
            if (type(vapor) is not IdealWaterVapor
                    or vapor.method_id!=self.chemical.caloric_method_id
                    or vapor.reference!=self.chemical.reference
                    or vapor.source_asset_sha256!=self.chemical.source_asset_sha256
                    or vapor.gas_constant_j_mol_k!=self.chemical.gas_constant_j_mol_k
                    or storage.mechanical.water.reference!=self.chemical.reference
                    or storage.mechanical.water.source_asset_sha256!=self.chemical.source_asset_sha256):
                raise WaterPhaseTransferError('phase_transfer_requires_matching_ideal_water_caloric_bridge')

    @property
    def _deforming_host(self):
        host=self.base_model.base_model if type(self.base_model) is ProgrammedSolidFluidHeat else self.base_model
        return host if type(host) is DeformingSolidHeat else None

    @property
    def _thermal_host(self):
        host=self.base_model.base_model if type(self.base_model) is ProgrammedSolidFluidHeat else self.base_model
        return host.base_model if type(host) is DeformingSolidHeat else host

    def breakpoints_s(self,start_s,end_s):
        return (self.base_model.breakpoints_s(start_s,end_s)
                if type(self.base_model) in (ProgrammedSolidFluidHeat,DeformingSolidHeat) else ())

    @property
    def _fluid_storages(self):
        return (tuple(s.fluid_template for s in self._thermal_host.storages)
                if type(self._thermal_host) in (SolidFluidHeat,ClosedFreeSolidCell,FreeSolidSlab) else self._thermal_host.storages)

    @property
    def _liquid_index(self):
        return (self._thermal_host.inventory_layout.liquid_index
                if type(self._thermal_host) in (SolidFluidHeat,ClosedFreeSolidCell,FreeSolidSlab) else 0)

    @property
    def liquid_index(self):return self._liquid_index

    @property
    def water_vapor_index(self):return self.species_order.index('H2O')

    @property
    def interfaces(self):
        return (('existing_liquid',)*len(self._thermal_host.storages)
                if self.interface_modes is None else self.interface_modes)

    def with_depleted_cells(self,state,cell_indices):
        """Explicit caller mode switch, not certification of an event location."""
        self.base_model._check_state(state)
        if not isinstance(cell_indices,(tuple,list)):
            raise WaterPhaseTransferError('invalid_depleted_cell_indices')
        if any(isinstance(i,bool) or not isinstance(i,Integral)
               or i<0 or i>=len(self.interfaces) for i in cell_indices):
            raise WaterPhaseTransferError('invalid_depleted_cell_indices')
        if len(set(cell_indices))!=len(cell_indices):
            raise WaterPhaseTransferError('duplicate_depleted_cell_indices')
        modes=list(self.interfaces)
        for i in cell_indices:
            if state.amounts_mol[i,self.liquid_index]!=0:
                raise WaterPhaseTransferError('depleted_cell_requires_exact_zero_liquid')
            modes[i]='depleted_no_nucleation'
        return replace(self,interface_modes=tuple(modes))

    @property
    def species_order(self):return self.base_model.species_order

    @property
    def material_qualified(self):return False

    @property
    def source_ids(self):
        return tuple(sorted(set(self.base_model.source_ids+self.chemical.source_ids+self.coefficient_source_ids)))

    def evaluate(self,state:ConservedState,time_s:float)->WaterTransferEvaluation:
        self.base_model._check_state(state)
        for row,k,mode in zip(state.amounts_mol,self.coefficients_mol_s_pa,self.interfaces):
            if mode=='depleted_no_nucleation':
                if row[self.liquid_index]!=0:raise DomainExit('dry_interface_requires_exact_zero_liquid')
                continue
            if k>0 and row[self._liquid_index]==0:
                raise DomainExit('no_existing_liquid_interface_nucleation_not_modelled')
        base=self.base_model.evaluate(state,time_s)
        water_index=self.species_order.index('H2O')
        reactions=np.array(base.rates.reaction_species_mol_s)
        diagnostics=[]
        for index,(row,closed,k,mode) in enumerate(zip(state.amounts_mol,base.storage_states,self.coefficients_mol_s_pa,self.interfaces)):
            if mode=='depleted_no_nucleation':
                diagnostics.append(self._dry_diagnostic(row,closed,k,base.rates,index))
                continue
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
            reactions[index,self._liquid_index]-=rate
            reactions[index,water_index]+=rate
            diagnostics.append(CellWaterTransfer(rate,k,pressure,equilibrium,mu,delta_mu,entropy,status))
        rates=Rates(base.rates.face_species_mol_s,base.rates.face_energy_w,reactions,base.rates.cell_power_w,
                    cell_power_components_w=base.rates.cell_power_components_w,
                    mechanical_rates_per_s=base.rates.mechanical_rates_per_s)
        sources=tuple(sorted(set(self.source_ids+getattr(base,'source_ids',()))))
        return WaterTransferEvaluation(rates,base,tuple(diagnostics),self.coefficient_set_id,self.coefficient_version,
                                       self.coefficient_classification,sources,
                                       interface_modes=self.interfaces,dry_policy=self.dry_policy,
                                       qualification=('explicit_'+self.dry_policy+'_dry_interface_choice_not_nucleation_model'
                                           if 'depleted_no_nucleation' in self.interfaces else
                                           'declared_pressure_difference_kinetics_existing_liquid_interface_not_sludge_nucleation'))

    def _dry_diagnostic(self,row,closed,k,rates,index):
        # Exact sum of represented net terms; this is not a gross reaction audit.
        net=(Fraction(float(rates.face_species_mol_s[index,self.liquid_index]))
             -Fraction(float(rates.face_species_mol_s[index+1,self.liquid_index]))
             +Fraction(float(rates.reaction_species_mol_s[index,self.liquid_index])))
        if net>0:raise DomainExit('dry_interface_liquid_reappearance_unsupported')
        mechanical=closed.mechanical
        pressure=_float_exact(Fraction(float(row[self.water_vapor_index]))
            *Fraction(self.chemical.gas_constant_j_mol_k)*Fraction(mechanical.temperature_k)
            /Fraction(mechanical.gas_volume_m3),'water_partial_pressure')
        try:
            hypothetical=self.chemical.equilibrium_at_liquid_tp(
                mechanical.temperature_k,mechanical.pressure_pa)
        except WaterDomainError as exc:
            if self.dry_policy=='strict':
                raise DomainExit('dry_interface_condensation_drive_unknown: '+str(exc)) from exc
            hypothetical=None
        except (WaterChemicalError,WaterNumericalError,IdealWaterVaporError) as exc:
            raise WaterPhaseTransferError(str(exc)) from exc
        if hypothetical is None:
            status='metastable_no_nucleation_condensation_drive_unknown'
        elif pressure>hypothetical.equilibrium_partial_pressure_pa:
            if self.dry_policy=='strict':raise DomainExit('dry_interface_condensation_requires_unsupported_nucleation')
            status='metastable_no_nucleation_supersaturated'
        else:
            status=self.dry_policy+'_no_nominal_condensation_demand'
        return CellWaterTransfer(0.,k,pressure,None,None,None,None,status,
                                 hypothetical_equilibrium=hypothetical)

    def __call__(self,state,time_s):return self.evaluate(state,time_s).rates
