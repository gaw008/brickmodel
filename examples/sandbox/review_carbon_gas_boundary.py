"""Graphite exhaustion from independent four-variable chemical equilibrium."""
import argparse
import json
from pathlib import Path

from mpmath import mp
from scipy.optimize import brentq

from carbon_gas_setup import build
from carbon_gas_decimal_reference import reconstruct,source_thermal


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    policy=json.loads((root/settings['model_parameters']).read_text());model,_=build(root,policy);mp.dps=settings['decimal_digits'];budget=settings['budgets']
    inventory=next(i for i in policy['inventories'] if i['name']==settings['inventory_name'])
    inputs=[inventory[k] for k in ['carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']];ct,ot,nn=map(mp.mpf,inputs);r=mp.mpf(model.r)
    def required(t):return model.at_temperature(t,*inputs)['graphite_branch_required_carbon_mol']-inputs[0]
    boundary=brentq(required,*settings['temperature_bracket_k'],xtol=settings['temperature_root_absolute_tolerance_k'],
        rtol=settings['temperature_root_relative_tolerance'],maxiter=settings['maximum_root_iterations'])
    candidate=model.at_temperature(boundary,*inputs);names=['CO','CO2','O2']
    def equations(t,*logarithms):
        thermal=source_thermal(model,t);gas=dict(zip(names,map(mp.exp,logarithms)));gas['N2']=nn;ng=mp.fsum(gas.values())
        mu={name:thermal[name][2]+r*t*mp.log(n/ng) for name,n in gas.items()};mu['C']=thermal['C'][2]
        return ((gas['CO']+gas['CO2'])/ct-1,(gas['CO']+2*gas['CO2']+2*gas['O2'])/ot-1,
            (mu['CO']-mu['C']-mu['O2']/2)/(r*t),(mu['CO2']-mu['C']-mu['O2'])/(r*t))
    initial=(mp.mpf(boundary),*(mp.log(mp.mpf(candidate['amounts_mol'][name])) for name in names))
    solution=mp.findroot(equations,initial,tol=mp.mpf(settings['root_tolerance']),maxsteps=settings['maximum_root_iterations'])
    tstar=solution[0];at_boundary=reconstruct(model,tstar,inventory,'graphite_present',candidate['amounts_mol'],settings)
    errors={'boundary_temperature_k':float(abs(mp.mpf(boundary)-tstar)),
        'vanishing_solid_mol':float(abs(at_boundary['amounts']['C'])),
        'source_enthalpy_j':float(abs(mp.mpf(candidate['enthalpy_j'])-at_boundary['enthalpy'])),
        'source_entropy_j_k':float(abs(mp.mpf(candidate['entropy_j_k'])-at_boundary['entropy']))}
    rows=[]
    for offset in settings['one_sided_offsets_k']:
        for sign,phase in [(-1,'graphite_present'),(1,'graphite_exhausted')]:
            at=tstar+sign*mp.mpf(offset);seed=model.at_temperature(float(at),*inputs)
            current=reconstruct(model,at,inventory,phase,seed['amounts_mol'],settings)
            step=mp.mpf(offset)*mp.mpf(settings['one_sided_derivative_step_fraction'])
            left=reconstruct(model,at-step,inventory,phase,seed['amounts_mol'],settings)
            right=reconstruct(model,at+step,inventory,phase,seed['amounts_mol'],settings)
            cp=(right['enthalpy']-left['enthalpy'])/(2*step)
            projected_h=current['enthalpy']+cp*(tstar-at)
            projected_s=current['entropy']+cp/at*(tstar-at)
            h_error=float(abs(projected_h-at_boundary['enthalpy']));s_error=float(abs(projected_s-at_boundary['entropy']))
            cp_error=float(abs(mp.mpf(seed['equilibrium_cp_j_k'])-cp))
            mu=current['mu'];condition=current['amounts']['C']>0 if sign<0 else mu['CO']-mu['C']-mu['O2']/2<0 and mu['CO2']-mu['C']-mu['O2']<0
            rows.append({'side':phase,'offset_k':offset,'temperature_k':str(at),'source_cp_j_k':str(cp),
                'candidate_cp_j_k':seed['equilibrium_cp_j_k'],'source_cp_error_j_k':cp_error,
                'projected_enthalpy_error_j':h_error,'projected_entropy_error_j_k':s_error,
                'within_budgets':{'expected_phase':seed['phase']==phase,'phase_constraint':bool(condition),
                    'enthalpy_continuity':h_error<=budget['projected_enthalpy_continuity_j'],
                    'entropy_continuity':s_error<=budget['projected_entropy_continuity_j_k'],'one_sided_cp':cp_error<=budget['one_sided_cp_j_k']}})
    flags={name:value<=budget[name] for name,value in errors.items()}
    result={'settings':settings,'inventory':inventory,'candidate_boundary_temperature_k':boundary,'reference_boundary_temperature_k':str(tstar),
        'reference_boundary_enthalpy_j':str(at_boundary['enthalpy']),'reference_boundary_entropy_j_k':str(at_boundary['entropy']),
        'boundary_errors':errors,'boundary_within_budgets':flags,'one_sided_records':rows,
        'all_requested_phase_boundary_budgets_met':all(flags.values()) and all(all(row['within_budgets'].values()) for row in rows),
        'material_qualified':False,'training_eligible':False,
        'scope':'Source Gibbs restricted minimum at standard pressure; H/S continuous at graphite exhaustion with distinct one-sided heat capacities. No finite-rate solid burnout or sludge-char equivalence.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'boundary_temperature_k':boundary,'all_requested_phase_boundary_budgets_met':result['all_requested_phase_boundary_budgets_met']}))


if __name__=='__main__':main()
