"""Source reconstruction and differential conservation for the coupled pore."""
import argparse
import itertools
import json
import math
from pathlib import Path

import mpmath as mp

from effusive_pore_setup import build
from effusive_pore_reference import EffusivePoreReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text()); policy = p['static_review']
    mp.mp.dps = policy['decimal_digits']
    model,sources = build(args.parameters.resolve().parent,p)
    reference = EffusivePoreReference(p,sources)
    v0 = 4*math.pi*p['model']['reference_radius_m']**3/3
    records = []
    for a,tp,tr,pressures in itertools.product(policy['radii_m'],policy['pore_temperatures_k'],
            policy['reservoir_temperatures_k'],policy['initial_pressures_pa']):
        amounts = [pressures[0]*v0/(model.r*policy['initial_temperature_k']),
                   pressures[1]*p['reservoir']['volume_m3']/(model.r*policy['initial_temperature_k'])]
        x = list(map(mp.mpf,[a,tp,tr,*amounts]))
        actual = model.at_state(a,tp,tr,*amounts,policy['boundary'])
        ref = reference.at_state(*x,policy['boundary'])
        fields = ['radius_rate_m_s','pore_temperature_rate_k_s','reservoir_temperature_rate_k_s',
                  'gas_transfer_mol_s','effusive_energy_w']
        errors = {k:float(abs(mp.mpf(actual[k])-ref[k])) for k in fields}
        errors.update(source_energy_j=float(abs(mp.mpf(actual['internal_energy_j'])-ref['internal_energy_j'])),
                      source_entropy_j_k=float(abs(mp.mpf(actual['entropy_j_k'])-ref['entropy_j_k'])),
                      source_pressure_pa=max(float(abs(mp.mpf(g['pressure_pa'])-ref[name])) for g,name in zip(actual['gases'],['pore_pressure_pa','reservoir_pressure_pa'])))
        rates = [actual['radius_rate_m_s'],actual['pore_temperature_rate_k_s'],actual['reservoir_temperature_rate_k_s'],
                 -actual['gas_transfer_mol_s'],actual['gas_transfer_mol_s']]
        gradients = []
        for component in [0,1]:
            gradient = []
            for index in range(len(x)):
                def component_at(value):
                    changed = x.copy(); changed[index] = value
                    return reference.energy_entropy(*changed)[component]
                gradient.append(mp.diff(component_at,x[index]))
            gradients.append(mp.fsum(g*v for g,v in zip(gradient,rates)))
        errors['energy_rate_w'] = float(abs(gradients[0]-actual['external_work_in_w']-actual['pore_heat_in_w']-actual['reservoir_heat_in_w']))
        errors['entropy_rate_w_k'] = float(abs(gradients[1]+actual['bath_entropy_rate_w_k']-actual['entropy_production_w_k']))
        flags = {k:v<=policy['budgets'][k] for k,v in errors.items()}
        flags.update(nonnegative_effusion=actual['effusion_entropy_production_w_k']>=0,
                     nonnegative_heat=actual['heat_entropy_production_w_k']>=0,
                     nonnegative_viscous=actual['viscous_dissipation_w']>=0)
        records.append({'inputs':{'radius_m':a,'temperatures_k':[tp,tr],'amounts_mol':amounts},
                        'state':actual,'errors':errors,'within_budgets':flags,'all_requested_budgets_met':all(flags.values())})
    result = {'settings':p,'sources':sources,'records':records,
              'maxima':{k:max(r['errors'][k] for r in records) for k in records[0]['errors']},
              'all_requested_budgets_met':all(r['all_requested_budgets_met'] for r in records),
              'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'states':len(records),'all_requested_budgets_met':result['all_requested_budgets_met'],'maxima':result['maxima']}))


if __name__ == '__main__':
    main()
