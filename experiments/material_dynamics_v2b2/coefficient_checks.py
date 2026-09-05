"""Independent coefficient and signed single-step raw evidence, no new solves."""
import math
from scenarios import expand_frozen_manifest
from temperature import evaluate
from solver import initial_state, euler, conductance, step
from model import Scenario
from reference.oracle import temperature
from exports import write_json


def record(out):
    records=[]; passed=True
    for s in expand_frozen_manifest():
        d=s.to_dict(); knots=d['temperature']['knots']
        times=sorted(set([k['tau'] for k in knots]+[(a['tau']+b['tau'])/2 for a,b in zip(knots,knots[1:])]))
        for t in times:
            c=evaluate(s,t); T=temperature(knots,t); r=d['reaction']; tr=d['transport']; ell=d['geometry']['length_ratio']; n=d['numerics']['n_cells']
            k=r['K_ref']*math.exp(r['theta']*(1-600/T)); diff=tr['d_ref']*(T/600)**tr['m']; ad=diff/ell**2; b=tr['Bi_ref']/ell
            g=0 if b==0 else 1/(1/b+1/(2*n*ad))
            ref=[T,k,diff,ad,b,g]; actual=[c.T_K,c.K,c.d,c.a_D,c.b,conductance(c.a_D,c.b,1/n)]
            error=max(abs(a-b)/max(1,abs(b)) for a,b in zip(actual,ref)); passed &=error<=1e-12
            records.append({'scenario_id':s.id,'tau':t,'reference_T_K_d_aD_b_g':ref,'actual':actual,'max_scaled_error':error})
    s=next(s for s in expand_frozen_manifest() if s.id=='C03'); transfers=[]
    for body,exterior in ((.2,.8),(.8,.2)):
        state=initial_state(s); n=len(state.u); state.u=[body]*n; state.v=[1-body]*n; state.f=[0.]*n; state.u_res=exterior; state.v_res=1-exterior
        c=evaluate(s,1); g=conductance(c.a_D,c.b,1/n); h=1e-5; nxt=euler(s,state,c,h,g)
        j=g*(body-exterior); err=max(abs(nxt.u_res-exterior-h*j/.25),abs(sum(nxt.u)/n+.25*nxt.u_res-body-.25*exterior),abs(sum(nxt.v)/n+.25*nxt.v_res-(1-body)-.25*(1-exterior)))
        passed &=err<=1e-12
        transfers.append({'body_initial':body,'reservoir_initial':exterior,'tau':1,'h':h,'flux_u':j,'body_u_final':nxt.u,'reservoir_u_final':nxt.u_res,'max_transfer_error':err})
    d=s.to_dict(); d['boundary']={'mode':'sealed','reservoir_ratio':None}; d['transport']['Bi_ref']=0; s=Scenario.from_dict(d)
    a=initial_state(s); t=.75; h=.0001; b=step(s,a,t,h); k0=evaluate(s,t).K; k1=evaluate(s,t+h).K
    u1=1-2*k0*h; f1=1-k0*h; fref=(1+f1-h*k1*u1*f1)/2; wrong=(1+f1-h*k0*u1*f1)/2
    stage={'t0':t,'t1':t+h,'K0':k0,'K1':k1,'actual_f':b.f[0],'correct_reference_f':fref,'wrong_frozen_stage_f':wrong}
    passed &=abs(b.f[0]-fref)<=1e-12 and abs(b.f[0]-wrong)>1e-10
    p=out/'coefficient_and_single_step_checks.json'; write_json(p,{'passed':passed,'coefficient_records':records,'signed_transfers':transfers,'stage_time':stage})
    if not passed: raise ArithmeticError('coefficient_check_failed')
    return p
