"""Exact represented-coefficient backward Euler for a frozen two-pool system.

This standalone leaf uses only standard-library rational algebra. It neither
loads source data nor authenticates coefficients against actual thermal states.
The map is not the exact frozen-ODE exponential and does not qualify a material.
"""
from dataclasses import dataclass, replace
from decimal import Decimal
from fractions import Fraction as F
import hashlib
import json
import math


NUMERICAL_POLICY_ID = 'FROZEN_LOCAL_MOISTURE_BACKWARD_EULER_V1'
Numeric = int | float | Decimal | F
_CLASSIFICATIONS = ('derived_from_evidence','virtual_design_choice','manufactured_test_fixture')


class ImplicitMoistureError(ValueError):
    """Invalid declared input or a requested finite readout cannot be represented."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ImplicitMoistureError(reason)


def _exact(value: Numeric, name: str, *, nonnegative: bool = False) -> F:
    _require(type(value) in (int,float,Decimal,F),name+'_finite_number_required')
    try:
        result = F(value)
    except (ValueError,OverflowError) as exc:
        raise ImplicitMoistureError(name+'_finite_number_required') from exc
    _require(not nonnegative or result >= 0,name+'_nonnegative_required')
    return result


def _rat(value: F) -> list[str]:
    return [str(value.numerator),str(value.denominator)]


def _identity(record: dict) -> str:
    return hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':'),
                                    allow_nan=False).encode()).hexdigest()


def numerical_policy() -> dict:
    """Explicit discretization choices, distinct from material parameters."""
    return {
        'id':NUMERICAL_POLICY_ID,'classification':'numerical_policy',
        'equations':'Nc_dot=-a*Nc+b*Nv; Nv_dot=a*Nc-(b+c)*Nv+f',
        'method':'one frozen-coefficient backward Euler step',
        'formal_order':1,'exact_frozen_ode_solution':False,
        'determinant':'1+h*(a+b+c)+h*h*a*c; strictly positive for nonnegative inputs',
        'shared_integrals':'Jphase=h*(a*Nc1-b*Nv1); Eout=h*(c*Nv1-f); Hout=hv*Eout',
        'energy':'delta_U=-Hout; local phase only redistributes the same Nc/Nv; no additional latent term',
        'arithmetic':'exact rational operations on the supplied represented values; no initial float projection',
        'projection':'separate optional readout, reject nonzero-to-zero or overflow; independent stock/J/E/H errors retained',
        'positivity':'nonnegative exact inventories for every finite h>=0 in this frozen local system',
        'scope':'no coefficient-state authentication, full host energy acceptance, full-step entropy, or coupled stability proof',
    }


@dataclass(frozen=True)
class FrozenLocalMoistureCoefficients:
    """Declared rates: a,b,c in 1/s, f in mol/s and common-reference hv in J/mol.

    hv is signed. Derivation of a/b from a common Kph, and c/f from a common Kv,
    belongs to the actual host adapter; nonnegative declarations alone do not
    authenticate these relationships or a frozen T/P/Vg approximation.
    """
    a_s_inv: F
    b_s_inv: F
    c_s_inv: F
    forcing_mol_s: F
    vapor_enthalpy_j_mol: F
    energy_reference_id: str
    source_ids: tuple[str,...]
    input_classification: str

    def __post_init__(self) -> None:
        for name in ('a_s_inv','b_s_inv','c_s_inv','forcing_mol_s'):
            object.__setattr__(self,name,_exact(getattr(self,name),name,nonnegative=True))
        object.__setattr__(self,'vapor_enthalpy_j_mol',
                           _exact(self.vapor_enthalpy_j_mol,'vapor_enthalpy_j_mol'))
        _require(type(self.energy_reference_id) is str and bool(self.energy_reference_id.strip()),
                 'common_energy_reference_required')
        _require(type(self.source_ids) is tuple and bool(self.source_ids) and
                 all(type(v) is str and bool(v.strip()) for v in self.source_ids),'coefficient_source_ids_required')
        _require(self.input_classification in _CLASSIFICATIONS,'declared_coefficient_classification_required')

    def to_record(self) -> dict:
        return {**{name:_rat(getattr(self,name)) for name in (
            'a_s_inv','b_s_inv','c_s_inv','forcing_mol_s','vapor_enthalpy_j_mol')},
            'energy_reference_id':self.energy_reference_id,'source_ids':list(self.source_ids),
            'input_classification':self.input_classification,
            'source_state_binding_verified':False,'frozen_coefficient_model_error':None}

    @property
    def identity(self) -> str:
        return _identity(self.to_record())


@dataclass(frozen=True)
class ScalarProjection:
    name: str
    exact: F
    binary64: float
    signed_roundoff: F
    absolute_error: F

    def to_record(self) -> dict:
        return {'name':self.name,'exact':_rat(self.exact),'binary64':self.binary64,
                'signed_roundoff':_rat(self.signed_roundoff),'absolute_error':_rat(self.absolute_error)}


def _project(name: str, value: F) -> ScalarProjection:
    try:
        binary = float(value)
    except (ValueError,OverflowError) as exc:
        raise ImplicitMoistureError(name+'_projection_overflow') from exc
    _require(math.isfinite(binary),name+'_projection_overflow')
    _require(value == 0 or binary != 0,name+'_projection_underflow')
    error = F(binary)-value
    return ScalarProjection(name,value,binary,error,abs(error))


@dataclass(frozen=True)
class LocalMoistureProjection:
    """Independent output readouts and their exact residuals, not host acceptance."""
    nc1_mol: float
    nv1_mol: float
    phase_transfer_mol: float
    outlet_transfer_mol: float
    outlet_enthalpy_j: float
    projections: tuple[ScalarProjection,...]
    condensed_balance_roundoff_mol: F
    vapor_balance_roundoff_mol: F
    carried_enthalpy_roundoff_j: F
    step_identity: str
    full_host_budget_verified: bool = False
    source_state_binding_verified: bool = False

    def to_record(self) -> dict:
        return {**{name:getattr(self,name) for name in (
            'nc1_mol','nv1_mol','phase_transfer_mol','outlet_transfer_mol','outlet_enthalpy_j')},
            'projections':[p.to_record() for p in self.projections],
            'condensed_balance_roundoff_mol':_rat(self.condensed_balance_roundoff_mol),
            'vapor_balance_roundoff_mol':_rat(self.vapor_balance_roundoff_mol),
            'carried_enthalpy_roundoff_j':_rat(self.carried_enthalpy_roundoff_j),
            'step_identity':self.step_identity,'full_host_budget_verified':False,
            'source_state_binding_verified':False,
            'scope':'readouts relative to exact original stocks; not independent permission to replace shared host J/E/H updates'}


@dataclass(frozen=True)
class LocalMoistureStep:
    nc0_mol: F
    nv0_mol: F
    duration_s: F
    coefficients: FrozenLocalMoistureCoefficients
    coefficient_identity: str
    determinant: F
    nc1_mol: F
    nv1_mol: F
    phase_transfer_mol: F
    outlet_transfer_mol: F
    outlet_enthalpy_j: F
    identity: str
    frozen_coefficient_model_error: None = None
    time_discretization_error: None = None
    source_state_binding_verified: bool = False
    material_qualified: bool = False
    training_eligible: bool = False
    full_host_budget_verified: bool = False

    @property
    def energy_change_j(self) -> F:
        return -self.outlet_enthalpy_j

    @property
    def additional_latent_energy_j(self) -> F:
        return F(0)

    @property
    def source_ids(self) -> tuple[str,...]:
        return tuple(sorted(set(self.coefficients.source_ids+(NUMERICAL_POLICY_ID,))))

    def _check(self) -> None:
        _require(self.coefficients.identity == self.coefficient_identity,'frozen_coefficients_changed')
        _require(self.nc1_mol >= 0 and self.nv1_mol >= 0 and
            self.nc1_mol == self.nc0_mol-self.phase_transfer_mol and
            self.nv1_mol == self.nv0_mol+self.phase_transfer_mol-self.outlet_transfer_mol and
            self.outlet_enthalpy_j == self.coefficients.vapor_enthalpy_j_mol*self.outlet_transfer_mol,
            'implicit_shared_integral_identity_failure')

    def project(self) -> LocalMoistureProjection:
        """Project five distinct quantities; exact result survives readout failure.

        The host must choose its actual shared-J/E update and account for final
        state/energy rounding itself. Independent stock and transfer readouts
        are supplied with residuals, never declared to close a host budget.
        """
        self._check()
        p = tuple(_project(name,getattr(self,name)) for name in (
            'nc1_mol','nv1_mol','phase_transfer_mol','outlet_transfer_mol','outlet_enthalpy_j'))
        nc,nv,j,e,hout = (value.binary64 for value in p)
        return LocalMoistureProjection(nc,nv,j,e,hout,p,
            F(nc)-self.nc0_mol+F(j),F(nv)-self.nv0_mol-F(j)+F(e),
            F(hout)-self.coefficients.vapor_enthalpy_j_mol*F(e),self.identity)

    def to_record(self) -> dict:
        self._check()
        return {**{name:_rat(getattr(self,name)) for name in (
            'nc0_mol','nv0_mol','duration_s','determinant','nc1_mol','nv1_mol',
            'phase_transfer_mol','outlet_transfer_mol','outlet_enthalpy_j','energy_change_j')},
            'coefficients':self.coefficients.to_record(),'coefficient_identity':self.coefficient_identity,
            'identity':self.identity,'source_ids':list(self.source_ids),'numerical_policy':numerical_policy(),
            'additional_latent_energy_j':[0,1],'frozen_coefficient_model_error':None,
            'time_discretization_error':None,'source_state_binding_verified':False,
            'full_host_budget_verified':False,'material_qualified':False,'training_eligible':False}


def backward_euler_local_moisture(nc0_mol: Numeric, nv0_mol: Numeric, duration_s: Numeric,
                                 coefficients: FrozenLocalMoistureCoefficients) -> LocalMoistureStep:
    """One nonnegative frozen BE step with one shared Jphase/Eout/Hout ledger."""
    _require(type(coefficients) is FrozenLocalMoistureCoefficients,'explicit_frozen_coefficients_required')
    coefficients = replace(coefficients)  # Revalidate and detach the immutable value record.
    nc,nv,h = (_exact(v,name,nonnegative=True) for v,name in (
        (nc0_mol,'nc0_mol'),(nv0_mol,'nv0_mol'),(duration_s,'duration_s')))
    a,b,c,f = (coefficients.a_s_inv,coefficients.b_s_inv,
               coefficients.c_s_inv,coefficients.forcing_mol_s)
    determinant = 1+h*(a+b+c)+h*h*a*c
    _require(determinant > 0,'implicit_positive_determinant_required')
    nc1 = ((1+h*(b+c))*nc+h*b*(nv+h*f))/determinant
    nv1 = (h*a*nc+(1+h*a)*(nv+h*f))/determinant
    phase = h*(a*nc1-b*nv1)
    outlet = h*(c*nv1-f)
    hout = coefficients.vapor_enthalpy_j_mol*outlet
    identity = _identity({'numerical_policy':NUMERICAL_POLICY_ID,
        'coefficient_identity':coefficients.identity,'nc0_mol':_rat(nc),
        'nv0_mol':_rat(nv),'duration_s':_rat(h)})
    result = LocalMoistureStep(nc,nv,h,coefficients,coefficients.identity,determinant,
                              nc1,nv1,phase,outlet,hout,identity)
    result._check()
    return result
