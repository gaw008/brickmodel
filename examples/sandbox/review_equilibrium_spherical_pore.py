"""Independent caloric-gradient, composition and entropy review of reactive pores."""
import argparse
import itertools
import json
import math
from pathlib import Path

import mpmath as mp

from equilibrium_pore_setup import build
from equilibrium_pore_reference import EquilibriumPoreReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text()); policy = p['static_review']
    mp.mp.dps = policy['decimal_digits']; model,sources = build(root,p)
    a0 = p['model']['reference_radius_m']; v0 = 4*math.pi*a0**3/3
    h = mp.mpf(p['independent_reference']['temperature_difference_k']); records = []
    for pressure0,radius,temperature,bath in itertools.product(policy['initial_pressures_pa'],policy['radii_m'],policy['temperatures_k'],policy['bath_temperatures_k']):
        amount = pressure0*v0/(model.r*policy['initial_temperature_k'])
        initial = {name:amount*fraction for name,fraction in p['gas_feed_fractions'].items()}
        ref = EquilibriumPoreReference(p,sources,initial)
        a,t,tb,g = map(mp.mpf,[radius,temperature,bath,policy['conductance_w_k']])
        actual = model.at_state(radius,temperature,amount,bath,policy['conductance_w_k'])
        independent = ref.at_state(a,t,tb,g)
        fields = {'radius_rate_m_s':'radius_rate_m_s','temperature_rate_k_s':'temperature_rate_k_s',
                  'source_energy_j':'internal_energy_j','source_entropy_j_k':'entropy_j_k',
                  'source_cv_j_k':'cv_j_k','source_pressure_pa':'gas_pressure_pa','dissipation_w':'viscous_dissipation_w'}
        errors = {key:abs(mp.mpf(actual[field])-independent[field]) for key,field in fields.items()}
        samples = {i:ref.energy_entropy(a,t+i*h) for i in [-2,-1,1,2]}
        derivative = lambda index:(samples[-2][index]-8*samples[-1][index]+8*samples[1][index]-samples[2][index])/(12*h)
        du_dt,ds_dt = derivative(0),derivative(1)
        du_da = 8*mp.pi*ref.p['surface_tension_n_m']*a; ds_da = 3*ref.n*ref.r/a
        adot,tdot = mp.mpf(actual['radius_rate_m_s']),mp.mpf(actual['temperature_rate_k_s'])
        errors['energy_rate_w'] = abs(du_da*adot+du_dt*tdot-actual['heat_in_w']-actual['external_work_in_w'])
        errors['entropy_rate_w_k'] = abs(ds_da*adot+ds_dt*tdot+actual['bath_entropy_rate_w_k']-actual['entropy_production_w_k'])
        errors['gas_cv_j_k'] = abs(mp.mpf(actual['gas_equilibrium']['equilibrium_cv_j_k'])-(du_dt-ref.capacity))
        errors['gas_amount_mol'] = max(abs(mp.mpf(actual['gas_amounts_mol'][name])-value) for name,value in independent['gas_amounts_mol'].items())
        atoms = ref.gas.p['atoms']
        errors['element_mol'] = max(abs(mp.fsum(atoms[name].get(element,0)*(mp.mpf(actual['gas_amounts_mol'][name])-value) for name,value in ref.initial.items())) for element in ['C','H','O','N'])
        errors['reaction_gibbs_j_mol'] = abs(mp.mpf(actual['reaction_gibbs_j_mol']))
        flags = {key:bool(value <= policy['budgets'][key]) for key,value in errors.items()}
        flags.update(positive_cv=actual['cv_j_k']>0,
                     positive_gas_amounts=min(actual['gas_amounts_mol'].values())>0,
                     nonnegative_viscous_entropy=actual['viscous_entropy_production_w_k']>=0,
                     nonnegative_heat_entropy=actual['heat_entropy_production_w_k']>=0)
        records.append({'initial_pressure_pa':pressure0,'state':actual,
                        'errors':{key:float(value) for key,value in errors.items()},
                        'within_budgets':flags,'all_requested_budgets_met':all(flags.values())})
    result = {'settings':p,'sources':sources,'records':records,
              'maxima':{key:max(row['errors'][key] for row in records) for key in policy['budgets']},
              'all_requested_budgets_met':all(row['all_requested_budgets_met'] for row in records),
              'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'states':len(records),'all_requested_budgets_met':result['all_requested_budgets_met'],'maxima':result['maxima']}),flush=True)


if __name__ == '__main__':
    main()
