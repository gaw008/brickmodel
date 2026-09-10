"""Single frozen native artifact replay. No provider construction/evaluation."""
from collections.abc import Mapping
from dataclasses import fields,is_dataclass
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch
import hashlib,json,math,time,signal
import numpy as np
from sludge_sandbox.integration import ConservedState,Rates
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.exact_source_column import ExactSourceColumn,SourceExactEvaluation
from sludge_sandbox.mass_wet_storage import WetMixedState
from sludge_sandbox.programmed_source_wet_column import ProgrammedLiquidSourceRates,SourceSurfaceObservation
from sludge_sandbox.source_wet_column import SourceColumnCell,ColumnFaceRate,LiquidColumnFaceRate
from sludge_sandbox.source_wet_storage import SourceWetInverse,SourceWetPoint,SourceWetStorage
from sludge_sandbox.rigid_storage import ClosedStorageState,DeclaredNumericalEnvelope,RigidStorage
from sludge_sandbox.rigid_water_gas import RigidWaterGasState,PressurePolicy,RigidWaterGas
from sludge_sandbox.mass_wet_transport import WetPhaseEvaluation,WetFaceEvaluation
from sludge_sandbox.water_chemical_potential import WaterPhaseEquilibrium,WaterLiquidChemicalState,WaterVaporChemicalState,WaterChemicalPotential
from sludge_sandbox.water_properties import WaterState,WaterReference,WaterProperties
from sludge_sandbox.water_heos import HEOSWaterProperties
from sludge_sandbox.water_implementation import WaterImplementation
from sludge_sandbox.source_mass_caloric import DisabledChemicalRates
from sludge_sandbox.gas_transport import GasState,GasFaceExchange
from sludge_sandbox.liquid_transport import LiquidFaceExchange,LiquidMobility,LiquidConnection,LiquidTransportState
from sludge_sandbox.phase_storage import PhaseMetadata
from sludge_sandbox.exact_boundary_program import ExactBoundaryState
from sludge_sandbox.boundary_program import ProgramIdentity
from sludge_sandbox.exchanges import BoundaryHeat
from sludge_sandbox.source_net_panel import SavedSourceSample,build_source_panel

INPUT_SHA='033dccd09ed268eeb2ce9570a37d52f66d4eb5da18b68f2f44a89bd01054c4f2'
AUDIT_SHA='c705d9410458690d0a8379da59e5a7c86a01fd4f59e2897699a5616e55c1914d'
# Explicit record classes found in selected frozen captures. No import name is
# taken from the input. All constructors are passive numeric/metadata records.
CLASSES=(ConservedState,Rates,ExactEventTime,SourceExactEvaluation,WetMixedState,
 ProgrammedLiquidSourceRates,SourceSurfaceObservation,SourceColumnCell,ColumnFaceRate,LiquidColumnFaceRate,
 SourceWetInverse,SourceWetPoint,ClosedStorageState,DeclaredNumericalEnvelope,RigidWaterGasState,PressurePolicy,
 WetPhaseEvaluation,WetFaceEvaluation,WaterPhaseEquilibrium,WaterLiquidChemicalState,WaterVaporChemicalState,
 WaterState,WaterReference,WaterImplementation,DisabledChemicalRates,GasState,GasFaceExchange,LiquidFaceExchange,
 LiquidMobility,LiquidConnection,LiquidTransportState,PhaseMetadata,ExactBoundaryState,ProgramIdentity,BoundaryHeat)
ALLOW={c.__module__+'.'+c.__qualname__:c for c in CLASSES}


def require(ok,reason):
    if not ok:raise ValueError(reason)


def encode(x):
    if type(x) is F:return {'numerator':x.numerator,'denominator':x.denominator}
    if isinstance(x,np.ndarray):return {'dtype':str(x.dtype),'shape':list(x.shape),'values':encode(x.tolist())}
    if isinstance(x,np.generic):return encode(x.item())
    if is_dataclass(x):return {'type':type(x).__module__+'.'+type(x).__qualname__,'fields':{f.name:encode(getattr(x,f.name)) for f in fields(x)}}
    if isinstance(x,Mapping):return {k:encode(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [encode(v) for v in x]
    return x


def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)


def decode(x):
    if type(x) is list:return tuple(decode(v) for v in x)
    if type(x) is not dict:
        require(x is None or type(x) in (str,int,bool,float),'unknown_primitive')
        require(type(x) is not float or math.isfinite(x),'nonfinite_primitive')
        return x
    if set(x)=={'numerator','denominator'}:
        require(type(x['numerator']) is int and type(x['denominator']) is int and x['denominator']>0,'exact_fraction')
        return F(x['numerator'],x['denominator'])
    if set(x)=={'dtype','shape','values'}:
        require(x['dtype']=='float64','only_saved_float64_arrays')
        a=np.array(x['values'],dtype=np.float64)
        require(list(a.shape)==x['shape'] and np.all(np.isfinite(a)),'actual_array_shape')
        return a
    if set(x)=={'type','fields'}:
        require(x['type'] in ALLOW,'unsupported_record:'+x['type'])
        cls=ALLOW[x['type']];descriptors=fields(cls)
        require(set(x['fields'])=={f.name for f in descriptors},'complete_original_record_fields')
        kwargs={f.name:decode(x['fields'][f.name]) for f in descriptors if f.init}
        value=cls(**kwargs)
        # Derived fields must recompute bit-for-bit; never patch init=False or
        # bypass constructors to make a mismatching saved record appear valid.
        require(canonical(encode(value))==canonical(x),'constructor_replay_mismatch:'+x['type'])
        return value
    return {k:decode(v) for k,v in x.items()}


def reject_physics(*args,**kwargs):raise AssertionError('pure_saved_replay_must_not_evaluate_physics')


def run(root,output):
    from contextlib import ExitStack
    start=time.monotonic();result={'status':'started','scope':'saved_numerical_affine_interpolation_only','input_sha256':INPUT_SHA,'audit_sha256':AUDIT_SHA,'trials':[],'soft_budget_s':30,'outer_budget_s':45}
    def save():Path(output).write_text(json.dumps(encode(result),indent=2,allow_nan=False)+'\n')
    save()
    def guard():require(time.monotonic()-start<30,'pure_replay_soft_budget_exceeded')
    def outer_timeout(*args):raise TimeoutError('pure_replay_outer_45s_budget_exceeded')
    previous=signal.signal(signal.SIGALRM,outer_timeout)
    signal.setitimer(signal.ITIMER_REAL,45.)
    try:
        folder=Path(root)/'docs/sandbox/research/exact-source-column-v1'
        raw=(folder/'native-result.json').read_bytes()
        require(hashlib.sha256(raw).hexdigest()==INPUT_SHA,'frozen_native_hash_mismatch')
        audit_raw=(folder/'native-audit.json').read_bytes()
        require(hashlib.sha256(audit_raw).hexdigest()==AUDIT_SHA,'frozen_audit_hash_mismatch')
        data=json.loads(raw);audit=json.loads(audit_raw)
        require(audit['input_sha256']==INPUT_SHA and len(data['captures'])==47
                and len(audit['trials'])==7,'audited_original_captures')
        targets=((ExactSourceColumn,'evaluate'),(SourceWetStorage,'invert'),(SourceWetStorage,'evaluate'),
                 (RigidStorage,'evaluate_at_temperature'),(WaterProperties,'state_tp'),
                 (HEOSWaterProperties,'state_tp'),(WaterChemicalPotential,'equilibrium_at_liquid_tp'))
        with ExitStack() as stack:
            for cls,name in targets:stack.enter_context(patch.object(cls,name,reject_physics))
            for trial in audit['trials']:
                guard()
                # Full-start and first-half Euler interior for this exact trial.
                # Repeated timestamps never substitute a different stage input.
                indices=(trial['capture_start'],trial['capture_start']+3)
                upper=ExactEventTime(F(trial['end']))
                captures=tuple(decode(data['captures'][i]) for i in indices)
                for c,i in zip(captures,indices):require(canonical(encode(c))==canonical(data['captures'][i]),'full_capture_roundtrip')
                first,interior=(SavedSourceSample(c['packed_input'],c['evaluation'],role)
                                for c,role in zip(captures,('original_trial_full_start','first_half_euler_interior')))
                require(first.evaluation.time==ExactEventTime(F(trial['start'])) and
                        interior.evaluation.time.seconds==(first.evaluation.time.seconds+upper.seconds)/2,'actual_trial_sample_times')
                kwargs=dict(operator_identity=first.evaluation.operator_identity,
                            energy_identity=first.state.energy_model_identity,
                            fixed_dry_mass_kg=tuple(s.solid_mass_kg[0] for s in first.evaluation.source_states))
                panel=build_source_panel(first,interior,upper,**kwargs)
                panel.check();minima=panel.minima()
                hm=interior.evaluation.time.elapsed_since(first.evaluation.time)
                checks=0
                for sample,t in ((first,F()),(interior,hm)):
                    raw_rates=sample.evaluation.source_evaluation
                    for i in range(3):
                        phase=F(raw_rates.cells[i].phase.phase_water_mol_s)
                        for j in range(4):
                            def flux(face):return F(getattr(face,'liquid_mol_s',0.)) if j==0 else F(face.gas_mol_s[j-1])
                            exact=flux(raw_rates.faces[i])-flux(raw_rates.faces[i+1])+(-phase if j==0 else phase if j==3 else F())
                            p=panel.inventories[4*i+j]
                            require(p.linear+2*p.quadratic*t==exact,'inventory_derivative_incidence');checks+=1
                        p=panel.energies[i]
                        require(p.linear+2*p.quadratic*t==F(raw_rates.faces[i].energy_w)-F(raw_rates.faces[i+1].energy_w),'U_derivative_incidence');checks+=1
                    water=sum((p.linear+2*p.quadratic*t for p in panel.inventories if p.index in (0,3)),F())
                    require(water==F(raw_rates.faces[0].gas_mol_s[2])-F(raw_rates.faces[-1].gas_mol_s[2]),'shared_water_telescoping')
                    require(sum((p.linear+2*p.quadratic*t for p in panel.energies),F())==F(raw_rates.faces[0].energy_w)-F(raw_rates.faces[-1].energy_w),'shared_U_telescoping');checks+=2
                result['trials'].append(dict(capture_indices=indices,original_trial=trial,
                    sample_bindings=panel.sample_bindings,inventory_polynomials=panel.inventories,
                    U_polynomials=panel.energies,minima=minima,derivative_checks=checks,
                    selected_capture_roundtrip_sha256=tuple(hashlib.sha256(canonical(encode(c)).encode()).hexdigest() for c in captures),
                    material_qualified=False,physical_trajectory_or_event_admitted=False))
                guard();save()
        result['status']='completed'
        result['elapsed_s']=time.monotonic()-start;save();return 0
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,reason=str(exc),elapsed_s=time.monotonic()-start)
        save();return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL,0.)
        signal.signal(signal.SIGALRM,previous)


if __name__=='__main__':
    import sys
    sys.exit(run(*sys.argv[1:]))
