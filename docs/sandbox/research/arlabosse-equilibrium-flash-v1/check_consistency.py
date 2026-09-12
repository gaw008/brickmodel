"""Bounded source-implementation differential diagnostic, no material certificate."""
from pathlib import Path
import sys,time,json,math
from fractions import Fraction as F
sys.path.insert(0,'/private/tmp/arlabosse-low-moisture-implicit-v1/long-probe')
from native_case import make_case,serialize
from sludge_sandbox.low_moisture_phase import evaluate_low_moisture_phase
OUT=Path('/private/tmp/arlabosse-equilibrium-flash-v1/consistency01.json')
START=time.monotonic()
plan={'scope':'nominal local derivative diagnostic, not a global bound or material validation','temperature_k':333.,'condensed_mol':.06,'temperature_delta_k':.01,'condensed_delta_mol':1e-5,'relative_diagnostic_tolerance':1e-4,'absolute_Ux_diagnostic_tolerance_j_mol':1.,'wall_limit_s':60.}
Path('/private/tmp/arlabosse-equilibrium-flash-v1/CONSISTENCY_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
opened,initial,points=make_case()
storage=opened.column.storages[1] if hasattr(opened,'column') else opened.base.storages[1]
chemical=storage.wet._chemical
nt=F(initial[1].liquid_water_mol)+F(initial[1].gas_amounts_mol[-1])
carrier=initial[1].gas_amounts_mol[:-1]
observations=[]
def evaluate(t,x):
 if time.monotonic()-START>60:raise RuntimeError('consistency_wall_limit')
 nv=float(nt-F(x));state=storage.state(x,carrier+(nv,),0.)
 point=storage.evaluate(state,t)
 phase=evaluate_low_moisture_phase(storage,chemical,point,nv,0.)
 pv=phase.water_partial_pressure_pa
 vapor=chemical.ideal_vapor(t,pv)
 g=math.fsum((phase.equilibrium.pure_equilibrium.liquid.chemical_potential_j_mol,point.excess.mu_ex_j_mol,-vapor.chemical_potential_j_mol))
 observations.append({'T':t,'Nc':x,'Nv':nv,'water_projection_residual_mol':serialize(F(x)+F(nv)-nt),'U':point.total_internal_energy_j,'U_error':point.energy_error_j,'P':point.pressure_pa,'P_error':point.pressure_error_pa,'Cv':point.closed_heat_capacity_j_k,'g':g,'peq':phase.equilibrium.equilibrium_partial_pressure_pa,'pv':pv,'source_ids':point.source_ids})
 return observations[-1]
try:
 c=evaluate(333.,.06)
 tm=evaluate(332.99,.06);tp=evaluate(333.01,.06)
 # +/-1e-5 would exceed this cell's available vapor on the positive side;
 # use 1e-7 as a separately declared positive-inventory composition probe.
 # Updated before those samples, no observed derivative used for selection.
 plan['condensed_delta_mol']=1e-7
 Path('/private/tmp/arlabosse-equilibrium-flash-v1/CONSISTENCY_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
 xm=evaluate(333.,.06-1e-7);xp=evaluate(333.,.06+1e-7)
 ux=(xp['U']-xm['U'])/(xp['Nc']-xm['Nc'])
 gt=(tp['g']-tm['g'])/(tp['T']-tm['T'])
 cv=(tp['U']-tm['U'])/(tp['T']-tm['T'])
 expected=c['g']-c['T']*gt
 result={'plan':plan,'observations':observations,'U_x_j_mol':ux,'g_minus_T_gT_j_mol':expected,'U_x_identity_residual_j_mol':ux-expected,'U_T_j_k':cv,'closed_Cv_j_k':c['Cv'],'Cv_relative_residual':(cv-c['Cv'])/c['Cv'],'checks':{'U_x_identity':abs(ux-expected)<=max(1.,1e-4*abs(expected)),'fixed_composition_Cv':abs(cv-c['Cv'])<=1e-4*abs(c['Cv'])},'material_qualified':False,'global_thermodynamic_certificate':False,'runtime_seconds':time.monotonic()-START}
 OUT.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('observations','plan')}))
except Exception as e:
 OUT.write_text(json.dumps({'plan':plan,'observations':observations,'failure':type(e).__name__+':'+str(e),'runtime_seconds':time.monotonic()-START},indent=2)+'\n')
 raise
