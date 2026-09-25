"""Caloric and composition derivatives in the coupled phase assemblages."""
import argparse
import json
import math
from pathlib import Path

from mpmath import mp

from carbon_calcium_setup import build
from carbon_calcium_decimal_reference import reconstruct


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());policy=json.loads((root/settings['model_parameters']).read_text())
    model,_=build(root,policy);mp.dps=settings['decimal_digits'];budget=settings['budgets'];records=[]
    for inventory in policy['inventories']:
        inputs=[inventory[name] for name in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
        for t in settings['temperature_points_k']:
            candidate=model.at_temperature(t,*inputs);cp=candidate['equilibrium_cp_j_k'];derivatives=candidate['amount_temperature_derivatives_mol_k']
            de={'Ca':derivatives['calcite']+derivatives['lime'],
                'C':math.fsum(derivatives[name] for name in ['calcite','C','CO','CO2']),
                'O':math.fsum((3*derivatives['calcite'],derivatives['lime'],derivatives['CO'],2*derivatives['CO2'],2*derivatives['O2'])),'N':2*derivatives['N2']}
            for width in settings['temperature_difference_steps_k']:
                step=mp.mpf(width);states=[];same=True;constraints=True
                for sign in [-1,1]:
                    at=mp.mpf(t)+sign*step;actual=model.at_temperature(float(at),*inputs)
                    same=same and actual['calcium_phase']==candidate['calcium_phase'] and actual['carbon_phase']==candidate['carbon_phase']
                    state=reconstruct(model,at,inventory,candidate,settings);states.append(state);mu=state['mu'];amounts=state['amounts']
                    constraints=constraints and all(n>=0 for n in amounts.values())
                    cal=mu['lime']+mu['CO2']-mu['calcite']
                    if candidate['calcium_phase']=='calcite':constraints=constraints and cal>=0
                    if candidate['calcium_phase']=='lime':constraints=constraints and cal<=0
                    if candidate['carbon_phase']=='graphite_exhausted':constraints=constraints and mu['CO']-mu['C']-mu['O2']/2<=0 and mu['CO2']-mu['C']-mu['O2']<=0
                dh=(states[1]['enthalpy']-states[0]['enthalpy'])/(2*step);tds=mp.mpf(t)*(states[1]['entropy']-states[0]['entropy'])/(2*step)
                dn={name:(states[1]['amounts'][name]-states[0]['amounts'][name])/(2*step) for name in derivatives}
                errors={name:float(abs(mp.mpf(derivatives[name])-value)) for name,value in dn.items()}
                relative={name:float(abs(mp.mpf(derivatives[name])/value-1)) for name,value in dn.items() if value!=0}
                dh_error=float(abs(mp.mpf(cp)-dh));ds_error=float(abs(mp.mpf(cp)-tds))
                flags={'same_phases':bool(same),'reference_phase_constraints':bool(constraints),
                    'positive_capacity':cp>=candidate['frozen_cp_j_k']>0,
                    'enthalpy_derivative':dh_error<=budget['enthalpy_derivative_j_k'],'entropy_identity':ds_error<=budget['entropy_identity_j_k'],
                    'species_derivative':max(errors.values())<=budget['species_derivative_mol_k'],
                    'element_derivative':max(abs(v) for v in de.values())<=budget['element_derivative_mol_k']}
                row={'inventory':inventory,'temperature_k':t,'calcium_phase':candidate['calcium_phase'],'carbon_phase':candidate['carbon_phase'],'width_k':width,
                    'equilibrium_cp_j_k':cp,'frozen_cp_j_k':candidate['frozen_cp_j_k'],'source_enthalpy_derivative_j_k':str(dh),'temperature_times_entropy_derivative_j_k':str(tds),
                    'enthalpy_derivative_error_j_k':dh_error,'entropy_identity_error_j_k':ds_error,'species_derivative_absolute_errors_mol_k':errors,
                    'species_derivative_relative_errors_unbudgeted':relative,'element_derivatives_mol_k':de,'within_budgets':flags}
                records.append(row)
            print(json.dumps({'inventory':inventory['name'],'temperature_k':t,'last_width_passed':all(records[-1]['within_budgets'].values())}),flush=True)
    result={'settings':settings,'records':records,'all_requested_caloric_budgets_met':all(all(r['within_budgets'].values()) for r in records),
        'material_qualified':False,'training_eligible':False,'scope':settings['scope']}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
