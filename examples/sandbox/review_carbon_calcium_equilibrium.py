"""Independent source and phase review of coupled Ca/C/O equilibrium."""
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
    model,sources=build(root,policy);mp.dps=settings['decimal_digits'];budget=settings['budgets'];records=[]
    for inventory in policy['inventories']:
        inputs=[inventory[name] for name in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
        for t in policy['temperature_points_k']:
            candidate=model.at_temperature(t,*inputs);reference=reconstruct(model,t,inventory,candidate,settings);n=candidate['amounts_mol'];mu=candidate['chemical_potentials_j_mol']
            elements={'Ca':n['calcite']+n['lime'],'C':math.fsum(n[name] for name in ['calcite','C','CO','CO2']),
                'O':math.fsum((3*n['calcite'],n['lime'],n['CO'],2*n['CO2'],2*n['O2'])),'N':2*n['N2']}
            element_errors={name:abs(value-target) for (name,value),target in zip(elements.items(),[inputs[0],inputs[1],inputs[2],2*inputs[3]],strict=True)}
            gas_names=['CO','CO2','O2','N2'];ng=math.fsum(n[name] for name in gas_names)
            pressure_error=max(abs(math.fsum(candidate['partial_pressures_pa'].values())-model.p0),*(abs(candidate['partial_pressures_pa'][name]-model.p0*n[name]/ng) for name in gas_names))
            absolute={name:float(abs(mp.mpf(n[name])-value)) for name,value in reference['amounts'].items()}
            relative={name:float(abs(mp.mpf(n[name])/reference['amounts'][name]-1)) for name in gas_names}
            h_error=float(abs(mp.mpf(candidate['enthalpy_j'])-reference['enthalpy']));s_error=float(abs(mp.mpf(candidate['entropy_j_k'])-reference['entropy']))
            cal=mu['lime']+mu['CO2']-mu['calcite'];c1=mu['CO']-mu['C']-mu['O2']/2;c2=mu['CO2']-mu['C']-mu['O2'];gas=mu['CO2']-mu['CO']-mu['O2']/2
            calcium_error={'calcite':max(0.,-cal),'lime':max(0.,cal),'coexistence':abs(cal)}[candidate['calcium_phase']]
            carbon_error=max(abs(c1),abs(c2)) if candidate['carbon_phase']=='graphite_present' else max(0.,c1,c2)
            source_mu=reference['mu'];source_cal=source_mu['lime']+source_mu['CO2']-source_mu['calcite']
            reference_constraints=all(value>=0 for value in reference['amounts'].values())
            if candidate['calcium_phase']=='calcite':reference_constraints=reference_constraints and source_cal>=0
            if candidate['calcium_phase']=='lime':reference_constraints=reference_constraints and source_cal<=0
            if candidate['carbon_phase']=='graphite_exhausted':reference_constraints=reference_constraints and source_mu['CO']-source_mu['C']-source_mu['O2']/2<=0 and source_mu['CO2']-source_mu['C']-source_mu['O2']<=0
            flags={'elements':max(element_errors.values())<=budget['element_mol'],'pressure':pressure_error<=budget['pressure_pa'],
                'calcium_complementarity':calcium_error<=budget['chemical_potential_j_mol'],'carbon_complementarity':carbon_error<=budget['chemical_potential_j_mol'],
                'gas_equilibrium':abs(gas)<=budget['chemical_potential_j_mol'],'reference_phase_constraints':bool(reference_constraints),
                'source_enthalpy':h_error<=budget['source_enthalpy_j'],'source_entropy':s_error<=budget['source_entropy_j_k'],
                'amounts':max(absolute.values())<=budget['amount_mol'],'positive_gas_relative':max(relative.values())<=budget['positive_gas_relative'],
                'positive_equilibrium_cp':candidate['equilibrium_cp_j_k']>=candidate['frozen_cp_j_k']>0}
            records.append({'inventory':inventory,'candidate':candidate,'reference_amounts_mol':{name:str(value) for name,value in reference['amounts'].items()},
                'element_errors_mol':element_errors,'pressure_error_pa':pressure_error,'absolute_amount_errors_mol':absolute,'positive_gas_relative_errors':relative,
                'source_enthalpy_error_j':h_error,'source_entropy_error_j_k':s_error,'calcium_complementarity_error_j_mol':calcium_error,
                'carbon_complementarity_error_j_mol':carbon_error,'gas_equilibrium_error_j_mol':abs(gas),'within_budgets':flags})
            print(json.dumps({'inventory':inventory['name'],'temperature_k':t,'calcium_phase':candidate['calcium_phase'],'carbon_phase':candidate['carbon_phase'],'within_budgets':all(flags.values())}),flush=True)
    result={'settings':settings,'model_parameters':policy,'sources':sources,'records':records,'all_requested_static_budgets_met':all(all(r['within_budgets'].values()) for r in records),
        'material_qualified':False,'training_eligible':False,'scope':settings['scope']}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
