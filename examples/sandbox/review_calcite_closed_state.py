"""Finite-inventory chemical equilibrium, derivative and element-accounting study."""
import argparse
import json
import math
from pathlib import Path

from scipy.optimize import brentq

from calcite_closed_setup import build_closed
from sludge_sandbox.equilibrium_calcite_closed import ClosedCalciteMixture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    config=json.loads((root/settings['model_parameters']).read_text())
    reaction,nitrogen,affinity,source,facts,nsource=build_closed(root,config)
    model=ClosedCalciteMixture(reaction,nitrogen,config,affinity['root']);records=[];budget=settings['budgets']
    n0=config['initial_calcite_mol'];c0=config['initial_co2_mol'];nn=config['nitrogen_mol'];p=config['total_pressure_pa']
    r=reaction.gas_constant_j_mol_k;dt=settings['temperature_derivative_step_k'];probe=n0*settings['extent_probe_fraction']
    for t in settings['temperatures_k']:
        state=model.at_temperature(t)
        def affinity_at(x):
            return reaction.affinity(t,p*(c0+x)/(c0+x+nn))['affinity_j_mol_extent']
        if affinity_at(0.)<=0.:reference=0.
        elif affinity_at(n0)>=0.:reference=n0
        else:reference=brentq(affinity_at,0.,n0,xtol=settings['extent_root_absolute_mol'],
            rtol=settings['extent_root_relative_tolerance'],maxiter=settings['extent_root_iterations'])
        a,b=[model.at_temperature(u) for u in (t-dt,t+dt)]
        dh=(b['enthalpy_j']-a['enthalpy_j'])/(2*dt);ds=(b['entropy_j_k']-a['entropy_j_k'])/(2*dt)
        back=model.state(state['enthalpy_j']);x=state['extent_mol'];af=affinity_at(x)
        violation=abs(af) if state['phase']=='coexistence' else (max(0.,af) if state['phase']=='calcite' else max(0.,-af))
        def gibbs(extent):
            phases=[model.reactant.standard(t),model.product.standard(t),model.gas.standard(t),nitrogen.standard(t)]
            amounts=[n0-extent,extent,c0+extent,nn];nc=c0+extent;nt=nc+nn
            return math.fsum(q*s['gibbs_j_mol'] for q,s in zip(amounts,phases,strict=True))+r*t*(nc*math.log(p*nc/nt/reaction.standard_pressure_pa)+nn*math.log(p*nn/nt/reaction.standard_pressure_pa))
        probes=[z for z in (x-probe,x+probe) if 0.<=z<=n0]
        increases=[gibbs(z)-gibbs(x) for z in probes]
        elements={'Ca':state['calcite_mol']+state['lime_mol']-n0,
            'C':state['calcite_mol']+state['co2_mol']-(n0+c0),
            'O':3*state['calcite_mol']+state['lime_mol']+2*state['co2_mol']-(3*n0+2*c0),
            'N':2*state['nitrogen_mol']-2*nn}
        errors={'extent_mol':abs(x-reference),'inverse_temperature_k':abs(back['temperature_k']-t),
            'heat_capacity_derivative_j_k':abs(dh-state['equilibrium_cp_j_k']),
            'entropy_enthalpy_derivative_per_k':abs(ds/dh-1/t),'phase_affinity_j_mol':violation}
        flags={key:value<=budget[key] for key,value in errors.items()}
        flags.update(inventory=max(abs(v) for v in elements.values())<=budget['inventory_mol'],
            gibbs_local_minimum=min(increases)>=-budget['gibbs_increase_negative_allowance_j'],positive_capacity=state['equilibrium_cp_j_k']>0)
        records.append({'state':state,'independent_extent_mol':reference,'element_residuals_mol':elements,
            'errors':errors,'gibbs_probe_increases_j':increases,'within_budgets':flags})
    result={'settings':settings,'parameters':config,'nitrogen_source':nsource,'phase_temperatures_k':model.phase_temperatures,
        'phase_enthalpies_j':model.limits,'records':records,'all_requested_numerical_budgets_met':all(all(r['within_budgets'].values()) for r in records),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],
        'phase_temperatures_k':model.phase_temperatures,'records':len(records)}))


if __name__=='__main__':main()
