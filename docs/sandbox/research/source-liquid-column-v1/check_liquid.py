"""Independent source+artificial-liquid column RHS and bounded DOP853 oracle."""
from pathlib import Path
from fractions import Fraction as F
import json, math, hashlib, time, signal
import numpy as np
from scipy.optimize import brentq
from scipy.integrate import solve_ivp
from pytest import MonkeyPatch
from test_source_liquid_column import setup
from dataclasses import replace
from sludge_sandbox.gas_transport import ideal_gas_state, face_exchange
from sludge_sandbox.source_wet_column import integrate_source_column
ROOT=Path('/Users/wanggaoying/Desktop/brickmodel-github'); OUT=Path('/private/tmp/brick-source-liquid-physics-v1')
paths=('src/sludge_sandbox/source_wet_column.py','src/sludge_sandbox/mass_wet_transport.py','tests/sandbox/test_source_liquid_column.py','src/sludge_sandbox/liquid_transport_state.py','src/sludge_sandbox/liquid_transport.py')
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
start=time.monotonic(); frozen=hashes(); signal.signal(signal.SIGALRM,lambda *args:(_ for _ in ()).throw(TimeoutError('45_second_cap')));signal.alarm(45)
patch=MonkeyPatch();column,initial=setup(patch)
relations=tuple(replace(r,relative_permeability=(.25,.75),relation_kind="tabulated_saturation_relation") for r in column.liquid_transport.relations)
column=replace(column,liquid_transport=replace(column.liquid_transport,relations=relations))
ids=column.gas_ids; curves=[column.storages[0].fluid_template.gas_phases[k]._curve for k in ids]
R=column.chemical.gas_constant_j_mol_k
m=float(column.storages[0].dry_mass_kg); a=1434-3.29*273.15; t0=313.15
masses={k:column.storages[0].fluid_template.gas_phases[k].molar_mass_kg_mol for k in ids}
def pack(states):return np.array([[s.liquid_water_mol,*s.gas_amounts_mol,s.internal_energy_j] for s in states]).ravel()
# Independent printed solid polynomial and exact artificial liquid from test source.
def energy(t,nl,ng):return nl*(75*t-300000)+math.fsum(n*c.internal_energy_j_mol(t) for n,c in zip(ng,curves))+m*(a*(t-t0)+1.645*(t*t-t0*t0))
def rhs(t,y):
    cells=np.reshape(y,(3,5));gases=[];phase=[];liquid_props=[]
    for i,row in enumerate(cells):
        nl,*other=row; ng=other[:3];u=other[3]
        T=brentq(lambda T:energy(T,nl,ng)-u,310,350,xtol=1e-11,rtol=1e-14)
        vg=.001-nl*1.8e-5;p=sum(ng)*R*T/vg
        eq=column.chemical.equilibrium_at_liquid_tp(T,p)
        phase.append(1e-9*(eq.equilibrium_partial_pressure_pa-ng[2]*R*T/vg))
        liquid_props.append((p,nl*1.8e-5/.001,75*T-300000+p*1.8e-5))
        gases.append(ideal_gas_state(dict(zip(ids,ng)),temperature_k=T,gas_volume_m3=vg,molar_masses_kg_mol=masses,gas_constant_j_mol_k=R))
    face=np.zeros((4,4));liquid_face=np.zeros(4)
    for f in range(1,3):
        spec=column.faces[f-1];dl,dr=spec.half_widths_m;left,right=gases[f-1:f+1]
        ex=face_exchange(left,right,area_m2=spec.area_m2,distance_m=dl+dr,face_left_weight=dr/(dl+dr),effective_diffusivities_m2_s=dict(zip(ids,spec.diffusivities_m2_s)),permeability_m2=spec.permeability_m2,relative_permeability=1.,viscosity_pa_s=spec.viscosity_pa_s)
        face[f,:3]=[ex.net_mol_s[k] for k in ids]
        heat=spec.area_m2*(left.temperature_k-right.temperature_k)/(dl/spec.conductivities_w_m_k[0]+dr/spec.conductivities_w_m_k[1])
        powers=[heat]
        for k,c in zip(ids,curves):
            powers.append(ex.diffusive_mol_s[k]*c.enthalpy_j_mol(ex.face_temperature_k))
            if ex.advective_mol_s[k]:powers.append(ex.advective_mol_s[k]*c.enthalpy_j_mol(ex.advective_donor_temperature_k))
        pL,sL,hL=liquid_props[f-1];pR,sR,hR=liquid_props[f]
        ml=1e-15*(.25+.5*sL)/.001;mr=1e-15*(.25+.5*sR)/.001
        ql=spec.area_m2*(pL-pR)/(dl/ml+dr/mr)
        liquid_face[f]=ql/1.8e-5
        powers.append(liquid_face[f]*(hL if ql>0 else hR))
        face[f,3]=math.fsum(powers)
    rates=np.zeros((3,5));rates[:,0]=-np.array(phase)+liquid_face[:-1]-liquid_face[1:]
    rates[:,1:4]=face[:-1,:3]-face[1:,:3];rates[:,3]+=phase
    rates[:,4]=face[:-1,3]-face[1:,3]
    return rates.ravel()
y0=pack(initial); probe_start=time.monotonic();r0=rhs(0,y0);probe=time.monotonic()-probe_start
# Duration chosen before inspecting convergence errors. Manufactured seam only.
duration=.25
reference=solve_ivp(rhs,(0,duration),y0,method='DOP853',rtol=2e-12,atol=np.tile([1e-13]*4+[1e-8],3),max_step=duration/2)
assert reference.success
results=[]
for steps in (2,4,8):
    run=integrate_source_column(column,initial,duration_s=duration,steps=steps,maximum_wall_seconds=18.)
    assert run.status=='completed',run.reason
    yf=pack(run.states[-1]); diff=(yf-reference.y[:,-1]).reshape(3,5)
    # Per-step exact telescoping balances, not a float residual threshold.
    for old,new,ledger in zip(run.states,run.states[1:],run.ledgers):
        assert sum(F(s.internal_energy_j) for s in new)-sum(F(s.internal_energy_j) for s in old)==sum(ledger.roundoff.energy_j)
        for k in (0,1):
            assert sum(F(s.gas_amounts_mol[k]) for s in new)-sum(F(s.gas_amounts_mol[k]) for s in old)==sum(row[k] for row in ledger.roundoff.gas_mol)
        water=lambda ss:sum(F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in ss)
        assert water(new)-water(old)==sum(ledger.roundoff.liquid_mol)+sum(row[2] for row in ledger.roundoff.gas_mol)
        assert sum(F(v.liquid_water_mol) for v in new)-sum(F(v.liquid_water_mol) for v in old)==-sum(ledger.phase_water_mol)+sum(ledger.roundoff.liquid_mol)
        lf=lambda face:getattr(face,'liquid_mol',F())
        for i in range(3):
            assert F(new[i].liquid_water_mol)-F(old[i].liquid_water_mol)==lf(ledger.faces[i])-lf(ledger.faces[i+1])-ledger.phase_water_mol[i]+ledger.roundoff.liquid_mol[i]
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j)==ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i]
            assert F(new[i].liquid_water_mol)+F(new[i].gas_amounts_mol[2])-F(old[i].liquid_water_mol)-F(old[i].gas_amounts_mol[2])==lf(ledger.faces[i])-lf(ledger.faces[i+1])+ledger.faces[i].gas_mol[2]-ledger.faces[i+1].gas_mol[2]+ledger.roundoff.liquid_mol[i]+ledger.roundoff.gas_mol[i][2]
        for face in ledger.faces[1:-1]:
            assert face.liquid_mol!=0 and face.liquid_enthalpy_j!=0
            assert face.energy_j==face.conduction_j+sum(face.diffusive_enthalpy_j)+sum(face.advective_enthalpy_j)+face.liquid_enthalpy_j+face.energy_decomposition_roundoff_j
        assert new[1].solid_mass_kg==old[1].solid_mass_kg
        assert F(new[1].internal_energy_j)-F(old[1].internal_energy_j)==ledger.faces[1].energy_j-ledger.faces[2].energy_j+ledger.roundoff.energy_j[1]
    results.append({'steps':steps,'seconds':run.elapsed_seconds,'energy_error_max_j':float(np.max(abs(diff[:,4]))),'inventory_error_max_mol':float(np.max(abs(diff[:,:4]))),'energy_roundoff_j':str(run.energy_roundoff_used_j),'inventory_roundoff_mol':str(run.inventory_roundoff_used_mol)})
assert results[2]['energy_error_max_j']<results[1]['energy_error_max_j']<results[0]['energy_error_max_j']
assert results[2]['inventory_error_max_mol']<results[1]['inventory_error_max_mol']<results[0]['inventory_error_max_mol']
result={'elapsed_seconds':time.monotonic()-start,'oracle_rhs_probe_seconds':probe,'dop853_nfev':reference.nfev,'duration_s':duration,'results':results,'energy_error_ratios':[results[i]['energy_error_max_j']/results[i+1]['energy_error_max_j'] for i in (0,1)],'inventory_error_ratios':[results[i]['inventory_error_max_mol']/results[i+1]['inventory_error_max_mol'] for i in (0,1)],'initial_middle_rhs':r0.reshape(3,5)[1].tolist(),'source_hashes':frozen,'source_hashes_unchanged':frozen==hashes(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'limits':'Oracle never calls column evaluate, source storage evaluate/invert, wet phase/face or liquid_face_exchange/decoded_liquid_state helpers or production integrator for reference; liquid Darcy and donor enthalpy hand assembled. Reuses source gas caloric, chemical equilibrium and gas face primitive. Artificial liquid; no native-water or material validation.'}
assert all(3<r<5 for r in result['energy_error_ratios']+result['inventory_error_ratios']);assert result['source_hashes_unchanged'];(OUT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));patch.undo();signal.alarm(0)
