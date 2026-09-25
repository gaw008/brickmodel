"""Chemical stability, element ledgers and gross heating/cooling observations."""
import argparse
import json
import math
from pathlib import Path

from calcite_affinity_setup import from_records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    with (root/settings['trajectory']).open() as stream:rows=[json.loads(line) for line in stream]
    header=rows[0];config=header['parameters'];initial=rows[1]
    reaction=from_records(header['affinity_parameters'],header['source'],header['reference_facts'])
    n0=config['initial_calcite_mol'];counts={};maxima={'calcium_mol':0.,'carbon_mol':0.,'oxygen_mol':0.,'constitutive_enthalpy_j':0.,'phase_stability_violation_j_mol':0.}
    observed=[r for r in rows if r['kind'] in ('initial','accepted','sample','phase_event')]
    for row in observed:
        s=row['state'];phase=s['phase'];counts[phase]=counts.get(phase,0)+1
        nc=s['calcite_mol'];nl=s['lime_mol'];ng=row['values'][1]
        maxima['calcium_mol']=max(maxima['calcium_mol'],abs(nc+nl-n0))
        maxima['carbon_mol']=max(maxima['carbon_mol'],abs(nc+ng-n0))
        maxima['oxygen_mol']=max(maxima['oxygen_mol'],abs(3*nc+nl+2*ng-3*n0))
        maxima['constitutive_enthalpy_j']=max(maxima['constitutive_enthalpy_j'],abs(s['enthalpy_j']-s['constitutive_enthalpy_j']))
        affinity=reaction.affinity(s['temperature_k'],config['co2_partial_pressure_pa'])['affinity_j_mol_extent']
        violation=abs(affinity) if phase=='coexistence' else (max(0.,affinity) if phase=='calcite' else max(0.,-affinity))
        maxima['phase_stability_violation_j_mol']=max(maxima['phase_stability_violation_j_mol'],violation)
    observations={r['time_s']:r for r in rows if r['kind'] in ('initial','sample')}
    stages=[]
    for segment in config['wall_program']:
        a,b=[observations[segment[k]] for k in ('start_s','end_s')]
        delta=[y-x for x,y in zip(a['values'],b['values'],strict=True)]
        stages.append({**segment,'external_heat_j':delta[2],'solid_enthalpy_change_j':delta[0],
            'co2_out_mol':delta[1],'co2_flow_enthalpy_j':delta[3],'combined_entropy_change_j_k':
                b['state']['entropy_j_k']-a['state']['entropy_j_k']+delta[5]-delta[4]})
    b=config['verification'];flags={'completed':rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        'calcium':maxima['calcium_mol']<=b['balance_co2_mol'],'carbon':maxima['carbon_mol']<=b['balance_co2_mol'],
        'oxygen':maxima['oxygen_mol']<=2*b['balance_co2_mol'],'constitutive_enthalpy':maxima['constitutive_enthalpy_j']<=b['balance_energy_j'],
        'chemical_stability':maxima['phase_stability_violation_j_mol']<=settings['source_affinity_budget_j_mol']}
    result={'settings':settings,'maxima':maxima,'phase_observation_counts':counts,'wall_stages':stages,
        'phase_events':[r for r in rows if r['kind']=='phase_event'],'within_budgets':flags,
        'all_requested_numerical_budgets_met':all(flags.values()),'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'maxima':maxima,'wall_stages':stages,'within_budgets':flags},indent=2))


if __name__=='__main__':main()
