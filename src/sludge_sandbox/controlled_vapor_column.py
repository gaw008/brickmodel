"""Controlled vapor contact and a separate heat bath for the low-W column.

The ideal reservoir follows the outer cell temperature and exchanges only
water vapor through a selective contact. Its prescribed partial pressure is
not a full kiln atmosphere. A separate finite heat conductance couples a heat
bath; these explicit virtual devices permit open water/energy ledgers without
asserting a sourced convection coefficient or a complete furnace boundary.
"""
from dataclasses import dataclass, field
from fractions import Fraction as F
import math

from .deforming_solid_storage import _digest
from .mass_storage_bridge import require
from .sorption_moisture_face import _project
from .source_wet_storage import _binary
from .source_wet_column import (
    ColumnFaceRate, ColumnFaceIntegral, ColumnStepLedger, SourceColumnRates,
    LowMoistureSorptionColumn,
)


BOUNDARY_ID='CONTROLLED_ISOTHERMAL_VAPOR_CONTACT_V1'


@dataclass(frozen=True)
class VaporBoundaryControl:
    vapor_pressure_pa: float
    transfer_coefficient_mol_s_pa: float
    heat_bath_temperature_k: float
    heat_conductance_w_k: float
    source_ids: tuple[str,...]
    classification: str='virtual_design_choice'

    def __post_init__(self):
        self.check()

    def check(self):
        for value in (self.vapor_pressure_pa,self.transfer_coefficient_mol_s_pa,self.heat_conductance_w_k):
            require(_binary(value)>=0,'nonnegative_controlled_boundary_value')
        _binary(self.heat_bath_temperature_k,positive=True)
        require(type(self.source_ids) is tuple and bool(self.source_ids) and
                all(type(s) is str and s.strip() for s in self.source_ids),'controlled_boundary_sources')
        require(self.classification=='virtual_design_choice','explicit_virtual_boundary_controls')


@dataclass(frozen=True)
class VaporBoundaryObservation:
    cell_temperature_k: float
    reservoir_temperature_k: float
    cell_vapor_pressure_pa: float
    reservoir_vapor_pressure_pa: float
    outward_water_mol_s: float
    common_vapor_enthalpy_j_mol: float
    outward_carried_energy_w: float
    heat_into_cell_w: float
    vapor_entropy_w_k: float | None
    vapor_entropy_state: str
    heat_entropy_w_k: float
    source_ids: tuple[str,...]
    numerical_log_error: None=None
    model_error: None=None
    material_qualified: bool=False
    training_eligible: bool=False


@dataclass(frozen=True,kw_only=True)
class ControlledVaporFaceRate(ColumnFaceRate):
    exact_water_mol_s: F
    exact_carried_energy_w: F
    exact_heat_into_cell_w: F
    boundary: VaporBoundaryObservation


@dataclass(frozen=True,kw_only=True)
class ControlledVaporFaceIntegral(ColumnFaceIntegral):
    vapor_molar_projection_mol: F
    vapor_enthalpy_projection_j: F
    heat_projection_j: F
    boundary: VaporBoundaryObservation


@dataclass(frozen=True,kw_only=True)
class ControlledVaporRates(SourceColumnRates):
    closed_rates: SourceColumnRates
    boundary: VaporBoundaryObservation


@dataclass(frozen=True,kw_only=True)
class ControlledVaporLedger(ColumnStepLedger):
    boundary: VaporBoundaryObservation
    midpoint_rates: ControlledVaporRates
    predictor_rates: ControlledVaporRates
    predictor_faces: tuple
    predictor_phase_water_mol: tuple


@dataclass(frozen=True)
class ControlledVaporColumn:
    base: LowMoistureSorptionColumn
    control: VaporBoundaryControl
    _identity: str=field(init=False,repr=False)

    def __post_init__(self):
        object.__setattr__(self,'_identity',self.binding())

    @property
    def storages(self): return self.base.storages
    @property
    def interface_modes(self): return self.base.interface_modes
    @property
    def gas_ids(self): return self.base.gas_ids
    @property
    def cell_count(self): return self.base.cell_count

    def binding(self):
        require(type(self.base) is LowMoistureSorptionColumn,'actual_low_moisture_column_required')
        require(type(self.control) is VaporBoundaryControl,'actual_vapor_boundary_control_required')
        self.control.check()
        return _digest((BOUNDARY_ID,self.base.model_identity,self.control))

    def _check(self):
        require(self.binding()==self._identity,'controlled_vapor_column_content_changed')

    @property
    def model_identity(self):
        self._check()
        return self._identity

    def evaluate(self,states):
        self._check()
        closed=self.base.evaluate(states)
        outer=closed.cells[-1]
        t=outer.inverse.point.temperature_k
        pv=outer.phase.water_partial_pressure_pa
        control=self.control
        pe=control.vapor_pressure_pa
        n_exact=F(control.transfer_coefficient_mol_s_pa)*(F(pv)-F(pe))
        n=_project(n_exact,'controlled_vapor_flow')
        # Both directions use the actual common ideal-vapor caloric reference
        # at the same contact T. This does not call ideal_vapor at zero p.
        hv=self.base.chemical.vapor.enthalpy_j_mol(t)
        carried_exact=n_exact*F(hv)
        carried=_project(carried_exact,'controlled_vapor_carried_energy')
        heat_exact=F(control.heat_conductance_w_k)*(F(control.heat_bath_temperature_k)-F(t))
        heat=_project(heat_exact,'controlled_boundary_heat')
        if n==0:
            entropy,entropy_state=0.,'no_exchange'
        elif pv==0 or pe==0:
            entropy,entropy_state=None,'positive_infinite_vacuum_limit'
        else:
            logratio=math.log1p((pv-pe)/pe) if abs(pv-pe)<.5*pe else math.log(pv)-math.log(pe)
            exact_entropy=F(n)*F(self.base.chemical.gas_constant_j_mol_k)*F(logratio)
            require(exact_entropy>0,'controlled_vapor_entropy_nonpositive')
            entropy,entropy_state=_project(exact_entropy,'controlled_vapor_entropy'),'finite'
        heat_entropy=F(heat)*(1/F(t)-1/F(control.heat_bath_temperature_k))
        require(heat_entropy>=0,'controlled_boundary_heat_entropy_negative')
        sources=tuple(sorted(set(closed.source_ids+control.source_ids+(BOUNDARY_ID,))))
        witness=VaporBoundaryObservation(t,t,pv,pe,n,hv,carried,heat,entropy,entropy_state,
            _project(heat_entropy,'controlled_heat_entropy'),sources)
        zeros=(0.,)*len(self.gas_ids)
        gas=(*zeros[:2],n)
        enthalpy=(*zeros[:2],carried)
        face=ControlledVaporFaceRate(face_id=self.cell_count,left_cell=self.cell_count-1,right_cell=None,
            gas_mol_s=gas,energy_w=_project(F(carried)-F(heat),'controlled_boundary_total_energy'),
            conduction_w=-heat,diffusive_enthalpy_w=enthalpy,advective_enthalpy_w=zeros,
            shared_evaluation=witness,exact_water_mol_s=n_exact,exact_carried_energy_w=carried_exact,
            exact_heat_into_cell_w=heat_exact,boundary=witness)
        self._check()
        return ControlledVaporRates(cells=closed.cells,gas_states=closed.gas_states,
            faces=(*closed.faces[:-1],face),model_identity=self._identity,source_ids=sources,
            closed_rates=closed,boundary=witness)

    def step_ledger(self,duration,faces,phase,error,predictor_error,midpoint,middle,*,
                    predictor_rates,predictor_faces,predictor_phase):
        return ControlledVaporLedger(duration,faces,phase,error,predictor_error,midpoint,
            boundary=middle.boundary,midpoint_rates=middle,predictor_rates=predictor_rates,
            predictor_faces=predictor_faces,predictor_phase_water_mol=predictor_phase)

    def provenance(self):
        self._check()
        return {'schema':'controlled_vapor_column_v1','model_identity':self._identity,
            'base':self.base.provenance(),'control':self.control,'source_id':BOUNDARY_ID,
            'equations':{'vapor':'nout=Kv*(pv-pv_env)','vapor_enthalpy':'Hout=nout*hv(Tcell)',
                'heat':'Qin=Gheat*(Tbath-Tcell)','storage':'dU=Qin-Hout; dNv=r-nout; dNc=-r'},
            'reservoir':'ideal infinite selective vapor reservoir follows decoded outer-cell T; no inert exchange',
            'heat_boundary':'separate prescribed heat bath and effective conductance, not resolved convection/radiation',
            'entropy':'instantaneous same-T vapor contact plus separate heat path; logarithmic error unknown',
            'vacuum':'singular ideal chemical potential; named entropy limit, not a finite error bound',
            'material_qualified':False,'training_eligible':False,'model_error':None}
