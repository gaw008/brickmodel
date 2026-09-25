"""Independent finite-inventory equilibrium caloric derivatives at fixed pressure."""
import argparse
import json
from pathlib import Path

from mpmath import mp

from carbon_gas_setup import build
from carbon_gas_decimal_reference import reconstruct


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    policy=json.loads((root/settings['model_parameters']).read_text());model,_=build(root,policy);mp.dps=settings['decimal_digits'];budget=settings['budgets'];records=[]
    for inventory in policy['inventories']:
        inputs=[inventory[k] for k in ['carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
        for t in settings['temperature_points_k']:
            candidate=model.at_temperature(t,*inputs);phase=candidate['phase'];cp=candidate['equilibrium_cp_j_k'];derivatives=candidate['amount_temperature_derivatives_mol_k']
            element_derivatives={'C':derivatives['C']+derivatives['CO']+derivatives['CO2'],
                'O':derivatives['CO']+2*derivatives['CO2']+2*derivatives['O2'],'N':2*derivatives['N2']}
            for width in settings['temperature_difference_steps_k']:
                h=mp.mpf(width);states=[];phases_agree=[];phase_constraints=[]
                for sign in [-1,1]:
                    at=mp.mpf(t)+sign*h;seed=model.at_temperature(float(at),*inputs)
                    phases_agree.append(seed['phase']==phase)
                    state=reconstruct(model,at,inventory,phase,seed['amounts_mol'],settings);states.append(state)
                    if phase=='graphite_present':
                        phase_constraints.append(state['amounts']['C']>=0)
                    else:
                        mu=state['mu'];phase_constraints.append(mu['CO']-mu['C']-mu['O2']/2<=0 and mu['CO2']-mu['C']-mu['O2']<=0)
                dh=(states[1]['enthalpy']-states[0]['enthalpy'])/(2*h)
                tds=mp.mpf(t)*(states[1]['entropy']-states[0]['entropy'])/(2*h)
                dn={name:(states[1]['amounts'][name]-states[0]['amounts'][name])/(2*h) for name in derivatives}
                errors={name:float(abs(mp.mpf(derivatives[name])-value)) for name,value in dn.items()}
                relative={name:float(abs(mp.mpf(derivatives[name])/value-1)) for name,value in dn.items() if value!=0}
                dh_error=float(abs(mp.mpf(cp)-dh));ds_error=float(abs(mp.mpf(cp)-tds))
                flags={'same_phase':all(phases_agree),'reference_phase_constraints':all(phase_constraints),
                    'positive_equilibrium_cp':cp>=candidate['frozen_cp_j_k']>0,
                    'enthalpy_derivative':dh_error<=budget['enthalpy_derivative_j_k'],
                    'entropy_identity':ds_error<=budget['entropy_identity_j_k'],
                    'species_derivative':max(errors.values())<=budget['species_derivative_mol_k'],
                    'element_derivative':max(abs(v) for v in element_derivatives.values())<=budget['element_derivative_mol_k']}
                records.append({'inventory':inventory,'temperature_k':t,'phase':phase,'width_k':width,
                    'frozen_cp_j_k':candidate['frozen_cp_j_k'],'equilibrium_cp_j_k':cp,
                    'reaction_capacity_j_k':candidate['reaction_capacity_j_k'],
                    'source_enthalpy_derivative_j_k':str(dh),'temperature_times_entropy_derivative_j_k':str(tds),
                    'enthalpy_derivative_error_j_k':dh_error,'entropy_identity_error_j_k':ds_error,
                    'species_derivative_absolute_errors_mol_k':errors,'species_derivative_relative_errors_unbudgeted':relative,
                    'element_derivatives_mol_k':element_derivatives,'within_budgets':flags})
    result={'settings':settings,'records':records,'all_requested_caloric_budgets_met':all(all(r['within_budgets'].values()) for r in records),
        'material_qualified':False,'training_eligible':False,
        'scope':'Independent source quadrature and simultaneous log-mole equations at both perturbations. Same-phase central derivatives only; graphite-exhaustion derivatives require separate one-sided review.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'records':len(records),'all_requested_caloric_budgets_met':result['all_requested_caloric_budgets_met']}))


if __name__=='__main__':main()
