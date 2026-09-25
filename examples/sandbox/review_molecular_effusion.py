"""Velocity-moment, caloric, thermal-transpiration and entropy source review."""
import argparse
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.molecular_effusion import EffusionGasState, effusive_exchange
from sludge_sandbox.thermochemistry import load_thermochemistry


def mp_state(temperature, pressures, pack, names, standard_pressure):
    t = mp.mpf(str(temperature))
    r = mp.mpf(str(pack['gas_constant']['value_j_mol_k']))
    by_name = {row['species_id']: row for row in pack['species']}
    h, s, cp = [], [], []
    for name, pressure in zip(names, pressures, strict=True):
        gas = by_name[name]
        segment = next(row for row in gas['segments'] if row['temperature_range_k'][0] <= t <= row['temperature_range_k'][1])
        a,b,c,d,e,f,g,z = map(lambda value: mp.mpf(str(value)), segment['coefficients'])
        theta = t/1000
        h.append(mp.mpf(str(gas['formation_enthalpy_298_j_mol']))
                 + 1000*(a*theta+b*theta**2/2+c*theta**3/3+d*theta**4/4-e/theta+f-z))
        s.append(a*mp.log(theta)+b*theta+c*theta**2/2+d*theta**3/3-e/(2*theta**2)+g
                 - r*mp.log(mp.mpf(str(pressure))/standard_pressure))
        cp.append(a+b*theta+c*theta**2+d*theta**3+e/theta**2)
    return {'temperature': t, 'h': h, 's': s, 'cp': cp,
            'mu': [hi-t*si for hi,si in zip(h,s,strict=True)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    pack = json.loads((root/p['thermochemistry_file']).read_text())
    molecular = json.loads((root/p['molecular_constants_file']).read_text())
    q = p['review']
    mp.mp.dps = q['decimal_precision']
    names = p['species_order']
    masses = [mp.mpf(molecular['species'][name]['molar_mass_g_mol'])*mp.mpf(molecular['constants']['gram_kg']) for name in names]
    r = mp.mpf(str(pack['gas_constant']['value_j_mol_k']))
    area, p0 = mp.mpf(str(p['area_m2'])), mp.mpf(str(p['reference_pressure_pa']))
    model = EffusionGasState(load_thermochemistry(root/p['thermochemistry_file']), names, p['reference_pressure_pa'])
    # Independent Cartesian Maxwell integrals, before restoring dimensional scale.
    normal = mp.quad(lambda z: z*mp.exp(-z*z), [0, mp.inf])
    normal_energy = mp.quad(lambda z: z**3*mp.exp(-z*z), [0, mp.inf])
    transverse = mp.quad(lambda z: mp.exp(-z*z), [-mp.inf, mp.inf])
    transverse_energy = mp.quad(lambda z: z*z*mp.exp(-z*z), [-mp.inf, mp.inf])
    kinetic_multiplier = normal_energy/normal+2*transverse_energy/transverse
    low,high = [mp.mpf(str(t))/1000 for t in p['source_temperature_interval_k']]
    capacity_bounds = []
    for name in names:
        gas = next(row for row in pack['species'] if row['species_id']==name)
        segment = next(row for row in gas['segments']
            if row['temperature_range_k'][0]<=1000*low and 1000*high<=row['temperature_range_k'][1])
        a,b,c,d,e,_,_,_ = [mp.mpf(str(v)) for v in segment['coefficients']]
        lower = a-r/2+min(b*low,b*high)+min(c*low**2,c*high**2)+min(d*low**3,d*high**3)+min(e/low**2,e/high**2)
        capacity_bounds.append({'species':name,'source_segment_k':segment['temperature_range_k'],
            'crossing_energy_temperature_derivative_lower_bound_j_mol_k':float(lower),
            'positive_entire_declared_interval':lower>0})
    records = []
    for case in p['cases']:
        supplied = [case['left'], case['right']]
        states = [model.at_temperature_pressure(s['temperature_k'], s['partial_pressures_pa']) for s in supplied]
        production = effusive_exchange(*states, list(map(float,masses)), float(r), float(area))
        source = [mp_state(s['temperature_k'], s['partial_pressures_pa'], pack, names, p0) for s in supplied]
        one_way, crossing = [], []
        for state, values in zip(source, supplied, strict=True):
            t = state['temperature']
            one_way.append([area*mp.mpf(str(pressure))/(r*t)*mp.sqrt(2*r*t/mass)*normal/transverse
                            for pressure,mass in zip(values['partial_pressures_pa'],masses,strict=True)])
            crossing.append([hi-r*t-mp.mpf('1.5')*r*t+kinetic_multiplier*r*t for hi in state['h']])
        flow = [a-b for a,b in zip(*one_way,strict=True)]
        energy_species = [one_way[0][i]*crossing[0][i]-one_way[1][i]*crossing[1][i] for i in range(len(names))]
        energy = mp.fsum(energy_species)
        beta_left, beta_right = [1/s['temperature'] for s in source]
        production_source = energy*(beta_right-beta_left)+mp.fsum(
            flow[i]*(source[0]['mu'][i]*beta_left-source[1]['mu'][i]*beta_right) for i in range(len(names)))
        positive_parts = []
        for i,name in enumerate(names):
            gamma_left, gamma_right = one_way[0][i], one_way[1][i]
            integral = mp.quad(lambda beta: (mp_state(1/beta, [p0], pack, [name], p0)['h'][0]-r/(2*beta)),
                               [beta_left,beta_right]) if beta_left != beta_right else mp.mpf(0)
            positive_parts.append([r*(gamma_left-gamma_right)*mp.log(gamma_left/gamma_right),
                gamma_left*(crossing[0][i]*(beta_right-beta_left)-integral),
                gamma_right*(integral-crossing[1][i]*(beta_right-beta_left))])
        shifted = []
        shift = np.asarray(q['gauge_energy_shifts_j_mol'])
        for state in states:
            shifted.append(dict(state, enthalpies_j_mol=state['enthalpies_j_mol']+shift,
                                chemical_potentials_j_mol=state['chemical_potentials_j_mol']+shift))
        gauge = effusive_exchange(*shifted, list(map(float,masses)), float(r), float(area))
        reverse = effusive_exchange(*states[::-1], list(map(float,masses)), float(r), float(area))
        errors = {
            'species_mol_s': max(float(abs(mp.mpf(actual)-expected)) for actual,expected in zip(production['species_mol_s'],flow,strict=True)),
            'energy_w': float(abs(mp.mpf(production['energy_w'])-energy)),
            'entropy_w_k': float(abs(mp.mpf(production['entropy_production_w_k'])-production_source)),
            'positive_decomposition_w_k': float(abs(production_source-mp.fsum(value for row in positive_parts for value in row))),
            'gauge_entropy_w_k': abs(gauge['entropy_production_w_k']-production['entropy_production_w_k']),
            'gauge_energy_relation_w': abs(gauge['energy_w']-production['energy_w']-float(np.dot(shift,production['species_mol_s']))),
            'reverse_species_mol_s': float(np.max(np.abs(reverse['species_mol_s']+production['species_mol_s']))),
            'reverse_energy_w': abs(reverse['energy_w']+production['energy_w']),
            'reverse_entropy_w_k': abs(reverse['entropy_production_w_k']-production['entropy_production_w_k']),
        }
        flags = {'species': errors['species_mol_s'] <= q['absolute_species_flux_budget_mol_s'],
            'energy': errors['energy_w'] <= q['absolute_energy_flux_budget_w'],
            'entropy': max(errors[k] for k in ['entropy_w_k','positive_decomposition_w_k','reverse_entropy_w_k']) <= q['absolute_entropy_rate_budget_w_k'],
            'gauge': errors['gauge_entropy_w_k'] <= q['gauge_entropy_rate_budget_w_k'] and errors['gauge_energy_relation_w'] <= q['absolute_energy_flux_budget_w'],
            'reverse': errors['reverse_species_mol_s'] <= q['absolute_species_flux_budget_mol_s'] and errors['reverse_energy_w'] <= q['absolute_energy_flux_budget_w'],
            'nonnegative_entropy': production['entropy_production_w_k'] >= -q['nonnegative_entropy_allowance_w_k'],
            'nonnegative_decomposition': all(v >= -mp.mpf(str(q['nonnegative_entropy_allowance_w_k'])) for row in positive_parts for v in row)}
        if case['name'] == 'thermal_mass_stationary':
            flags['zero_species_flow'] = max(abs(v) for v in production['species_mol_s']) <= q['thermal_mass_stationary_flux_budget_mol_s']
            flags['nonzero_heat_transfer'] = production['energy_w'] > q['absolute_energy_flux_budget_w']
        flags = {name: bool(value) for name,value in flags.items()}
        records.append({'case':case, 'production':{k:v.tolist() if isinstance(v,np.ndarray) else float(v) for k,v in production.items()},
            'source_entropy_production_decimal':str(production_source), 'nonnegative_species_entropy_components_decimal':[[str(v) for v in row] for row in positive_parts],
            'errors':errors, 'within_budgets':flags})
    result = {'settings':p, 'thermochemistry':pack, 'velocity_moments_decimal':{'normal':str(normal),'normal_energy':str(normal_energy),
        'transverse':str(transverse),'transverse_energy':str(transverse_energy),'crossing_translational_energy_over_RT':str(kinetic_multiplier)},
        'crossing_energy_monotonicity_bounds':capacity_bounds,
        'all_velocity_moment_budgets_met': abs(kinetic_multiplier/2-1) <= q['velocity_moment_relative_budget'],
        'records':records, 'all_requested_budgets_met': all(all(row['within_budgets'].values()) for row in records)
            and all(row['positive_entire_declared_interval'] for row in capacity_bounds)
            and abs(kinetic_multiplier/2-1) <= q['velocity_moment_relative_budget'],
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_budgets_met':result['all_requested_budgets_met'],
        'cases':[{'name':row['case']['name'],'within_budgets':row['within_budgets']} for row in records]}))


if __name__ == '__main__':
    main()
