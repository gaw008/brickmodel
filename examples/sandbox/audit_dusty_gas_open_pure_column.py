"""Independent pure-gas open-column flux, bath, stream and entropy integrals."""
import argparse
from bisect import bisect_left
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_maxwell_stefan_binary_column import polynomial
from review_dusty_gas_open_pure_steady import steady_reference


def audit(path):
    with path.open() as stream:
        rows = [json.loads(line) for line in stream]
    header, initial = rows[:2]
    p, count = header['settings'], header['cell_count']
    budget = p['verification']
    r, temperature = header['gas_constant_j_mol_k'], p['temperature_k']
    rt = r*temperature
    area, width = p['geometry']['area_m2'], p['geometry']['length_m']/count
    volume = p['pore']['porosity']*area*width
    reference_c = p['entropy_reference_pressure_pa']/rt
    u = p['fixed_temperature_molar_internal_energy_reference_j_mol'][0]
    enthalpy = u+rt
    dk = header['effective_knudsen_diffusivities_m2_s'][0]
    alpha = p['pore']['permeability_m2']*rt/header['pure_viscosities_pa_s'][0]
    boundary = np.array([p['boundary_partial_pressures_pa'][side][0]/rt for side in ['left','right']])
    distance = np.full(count+1, width)
    distance[[0,-1]] = width/2
    maxima = dict.fromkeys(['concentration_encoding_mol_m3', 'inventory_encoding_mol', 'energy_encoding_j',
        'entropy_encoding_j_k', 'pressure_encoding_pa', 'source_flux_mol_m2_s', 'source_entropy_rate_w_k',
        'recorded_inventory_rate_mol_s', 'recorded_energy_rate_w', 'recorded_entropy_rate_w_k',
        'energy_identity_w', 'entropy_identity_w_k'], 0.0)
    minima = {'concentration_mol_m3': float('inf'), 'face_entropy_rate_w_k': float('inf')}
    counts = {'recorded': 0, 'dense': 0}

    def reference(values, category):
        counts[category] += 1
        c = np.asarray(values)
        nodes = np.concatenate(([boundary[0]], c, [boundary[1]]))
        jump = np.diff(np.log(nodes/reference_c))
        diffusive = -dk*np.diff(nodes)/distance
        darcy = -alpha*np.diff(nodes**2)/(2*distance)
        flux = diffusive+darcy
        n = volume*c
        s = -r*n*np.log(c/reference_c)
        n_rate = area*(flux[:-1]-flux[1:])
        stream_energy = area*enthalpy*flux
        bath_heat = -rt*n_rate
        s_rate = -r*(np.log(c/reference_c)+1)*n_rate
        reservoir_entropy = float(area*r*(np.log(boundary[0]/reference_c)*flux[0]-np.log(boundary[1]/reference_c)*flux[-1]))
        bath_entropy = -float(bath_heat.sum())/temperature
        production = -r*area*flux*jump
        maxima['energy_identity_w'] = max(maxima['energy_identity_w'], float(np.max(np.abs(
            u*n_rate-(stream_energy[:-1]-stream_energy[1:])-bath_heat))))
        maxima['entropy_identity_w_k'] = max(maxima['entropy_identity_w_k'], abs(float(s_rate.sum())
            +reservoir_entropy+bath_entropy-float(production.sum())))
        minima['concentration_mol_m3'] = min(minima['concentration_mol_m3'], float(c.min()))
        minima['face_entropy_rate_w_k'] = min(minima['face_entropy_rate_w_k'], float(production.min()))
        return {'c':c, 'n':n, 's':s, 'u':u*n, 'flux':flux, 'diffusive':diffusive, 'darcy':darcy,
            'n_rate':n_rate, 'stream_energy':stream_energy, 'bath_heat':bath_heat,
            's_rate':s_rate, 'reservoir_entropy':reservoir_entropy, 'bath_entropy':bath_entropy,
            'production':production, 'wall':-r*area*diffusive*jump, 'darcy_entropy':-r*area*darcy*jump}

    recorded = [row for row in rows if row['kind'] in ('initial','accepted','sample')]+[rows[-1]['final']]
    for row in recorded:
        q = reference(row['values'], 'recorded')
        rates = row['rates']
        errors = {
            'concentration_encoding_mol_m3': np.max(np.abs(q['c']-np.asarray(row['partial_concentrations_mol_m3'])[:,0])),
            'inventory_encoding_mol': np.max(np.abs(q['n']-np.asarray(row['inventories_mol'])[:,0])),
            'energy_encoding_j': np.max(np.abs(q['u']-row['internal_energy_j'])),
            'entropy_encoding_j_k': np.max(np.abs(q['s']-row['relative_ideal_entropy_j_k'])),
            'pressure_encoding_pa': max(np.max(np.abs(rt*q['c']-row['pressure_pa'])),
                np.max(np.abs(rt*q['c']-np.asarray(row['partial_pressures_pa'])[:,0]))),
            'source_flux_mol_m2_s': max(np.max(np.abs(q[k]-[face[f][0] for face in row['faces']]))
                for k,f in [('flux','molar_fluxes_mol_m2_s'),('diffusive','diffusive_fluxes_mol_m2_s'),('darcy','darcy_fluxes_mol_m2_s')]),
            'source_entropy_rate_w_k': max(np.max(np.abs(q[k]-area*np.array([face[f] for face in row['faces']])))
                for k,f in [('production','entropy_from_jump_w_m2_k'),('production','entropy_from_path_w_m2_k'),
                    ('wall','entropy_wall_w_m2_k'),('darcy_entropy','entropy_darcy_w_m2_k')]),
            'recorded_inventory_rate_mol_s': np.max(np.abs(q['n_rate']-np.asarray(rates['inventory_rates_mol_s'])[:,0])),
            'recorded_energy_rate_w': max(np.max(np.abs(q['stream_energy']-rates['stream_energy_fluxes_w'])),
                np.max(np.abs(q['bath_heat']-rates['bath_heat_into_cells_w'])),
                np.max(np.abs(u*q['n_rate']-rates['internal_energy_rates_w']))),
            'recorded_entropy_rate_w_k': max(np.max(np.abs(q['s_rate']-rates['cell_entropy_rates_w_k'])),
                abs(q['reservoir_entropy']-rates['material_reservoir_entropy_rate_w_k']),
                abs(q['bath_entropy']-rates['bath_entropy_rate_w_k']),
                abs(float(q['production'].sum())-rates['all_faces_entropy_production_w_k']))}
        for key,value in errors.items(): maxima[key] = max(maxima[key], float(value))
    initial_n = np.asarray(initial['inventories_mol'])[:,0]
    initial_s, initial_u = np.asarray(initial['relative_ideal_entropy_j_k']), np.asarray(initial['internal_energy_j'])
    limits = {'local_species_mol':budget['local_species_budget_mol'], 'cumulative_species_mol':budget['local_species_budget_mol'],
        'global_boundary_species_mol':budget['global_species_budget_mol'],
        'local_entropy_j_k':budget['local_entropy_budget_j_k'], 'cumulative_cell_entropy_j_k':budget['cumulative_entropy_budget_j_k'],
        'local_combined_entropy_j_k':budget['local_entropy_budget_j_k'], 'cumulative_combined_entropy_j_k':budget['cumulative_entropy_budget_j_k'],
        'local_energy_j':budget['local_energy_budget_j'], 'cumulative_energy_j':budget['cumulative_energy_budget_j']}
    reviews, final_integrals = [], []
    for order in budget['entropy_quadrature_orders']:
        nodes,weights = leggauss(order)
        cumulative = {key:np.zeros(count) for key in ['n','s','stream_u','bath_u']}
        cumulative.update(external_s=0.0,production=0.0,boundary_n=0.0)
        previous_n,previous_s,previous_u = initial_n,initial_s,initial_u
        errors,minimum_step = dict.fromkeys(limits,0.0),float('inf')
        for row in rows:
            if row['kind'] != 'accepted': continue
            dense = row['dense_output']
            left,right = dense['start_time_s'],dense['end_time_s']
            integral = {key:np.zeros(count) for key in ['n','s','stream_u','bath_u']}
            integral.update(external_s=0.0,production=0.0,boundary_n=0.0)
            for node,weight in zip(nodes,weights,strict=True):
                at=(left+right)/2+(right-left)*node/2
                q=reference(polynomial(row,at),'dense')
                factor=weight*(right-left)/2
                integral['n']+=factor*q['n_rate']
                integral['s']+=factor*q['s_rate']
                integral['stream_u']+=factor*(q['stream_energy'][:-1]-q['stream_energy'][1:])
                integral['bath_u']+=factor*q['bath_heat']
                integral['external_s']+=factor*(q['reservoir_entropy']+q['bath_entropy'])
                integral['production']+=factor*float(q['production'].sum())
                integral['boundary_n']+=factor*area*(q['flux'][-1]-q['flux'][0])
            for key,value in integral.items(): cumulative[key]+=value
            n,s,energy=np.asarray(row['inventories_mol'])[:,0],np.asarray(row['relative_ideal_entropy_j_k']),np.asarray(row['internal_energy_j'])
            step_entropy=float(np.sum(s-previous_s)+integral['external_s'])
            residuals={'local_species_mol':np.max(np.abs(n-previous_n-integral['n'])),
                'cumulative_species_mol':np.max(np.abs(n-initial_n-cumulative['n'])),
                'global_boundary_species_mol':abs(float(np.sum(n-initial_n))+cumulative['boundary_n']),
                'local_entropy_j_k':np.max(np.abs(s-previous_s-integral['s'])),
                'cumulative_cell_entropy_j_k':np.max(np.abs(s-initial_s-cumulative['s'])),
                'local_combined_entropy_j_k':abs(step_entropy-integral['production']),
                'cumulative_combined_entropy_j_k':abs(float(np.sum(s-initial_s))+cumulative['external_s']-cumulative['production']),
                'local_energy_j':np.max(np.abs(energy-previous_u-integral['stream_u']-integral['bath_u'])),
                'cumulative_energy_j':np.max(np.abs(energy-initial_u-cumulative['stream_u']-cumulative['bath_u']))}
            for key,value in residuals.items(): errors[key]=max(errors[key],float(value))
            minimum_step=min(minimum_step,step_entropy)
            previous_n,previous_s,previous_u=n,s,energy
        flags={key:value<=limits[key] for key,value in errors.items()}
        flags['nonnegative_combined_step_entropy']=minimum_step>=-budget['negative_step_entropy_budget_j_k']
        final_integrals.append(cumulative)
        reviews.append({'order':order,'maximum_residuals':errors,'minimum_combined_step_entropy_j_k':minimum_step,
            'external_entropy_integral_j_k':float(cumulative['external_s']),
            'production_integral_j_k':float(cumulative['production']),
            'bath_heat_into_column_integral_j':float(cumulative['bath_u'].sum()),
            'boundary_net_outward_inventory_mol':float(cumulative['boundary_n']), 'within_budgets':flags})
    first,last=final_integrals[0],final_integrals[-1]
    differences={key:float(np.max(np.abs(first[key]-last[key]))) for key in first}
    flags={'completed':rows[-1]['status']=='completed','positive_concentrations':minima['concentration_mol_m3']>0,
        'nonnegative_face_entropy':minima['face_entropy_rate_w_k']>=0,
        'source_concentration':maxima['concentration_encoding_mol_m3']<=budget['source_concentration_budget_mol_m3'],
        'source_inventory':maxima['inventory_encoding_mol']<=budget['global_species_budget_mol'],
        'source_energy':maxima['energy_encoding_j']<=budget['local_energy_budget_j'],
        'source_entropy':maxima['entropy_encoding_j_k']<=budget['local_entropy_budget_j_k'],
        'source_pressure':maxima['pressure_encoding_pa']<=rt*budget['source_concentration_budget_mol_m3'],
        'source_flux':maxima['source_flux_mol_m2_s']<=budget['source_flux_absolute_budget_mol_m2_s'],
        'source_entropy_rate':maxima['source_entropy_rate_w_k']<=budget['source_entropy_rate_budget_w_k'],
        'recorded_inventory_rates':maxima['recorded_inventory_rate_mol_s']<=area*budget['source_flux_absolute_budget_mol_m2_s'],
        'recorded_energy_rates':maxima['recorded_energy_rate_w']<=budget['source_energy_rate_budget_w'],
        'recorded_entropy_rates':maxima['recorded_entropy_rate_w_k']<=budget['source_entropy_rate_budget_w_k'],
        'energy_identity':maxima['energy_identity_w']<=budget['source_energy_rate_budget_w'],
        'entropy_identity':maxima['entropy_identity_w_k']<=budget['source_entropy_rate_budget_w_k'],
        'whole_trajectory_balances':all(all(row['within_budgets'].values()) for row in reviews),
        'quadrature_species':max(differences['n'],differences['boundary_n'])<=budget['local_species_budget_mol'],
        'quadrature_entropy':max(differences['s'],differences['external_s'],differences['production'])<=budget['cumulative_entropy_budget_j_k'],
        'quadrature_energy':max(differences['stream_u'],differences['bath_u'])<=budget['cumulative_energy_budget_j']}
    exact=steady_reference(p,header,count)
    final=rows[-1]['final']
    pressure_error=float(np.max(np.abs(np.asarray(final['pressure_pa'])-np.array(exact['averages'],dtype=float)*rt)))
    flux_error=max(abs(face['molar_fluxes_mol_m2_s'][0]-float(exact['flux']))/abs(float(exact['flux'])) for face in final['faces'])
    steady={'maximum_cell_average_pressure_error_pa':pressure_error,'maximum_relative_flux_error':flux_error,
        'pressure_budget_pa':budget['steady_pressure_budget_pa'],'relative_flux_budget':budget['steady_relative_flux_budget'],
        'pressure_within_budget':pressure_error<=budget['steady_pressure_budget_pa'],
        'flux_within_budget':flux_error<=budget['steady_relative_flux_budget']}
    return {'trajectory':str(path),'cell_count':count,'accepted_steps':rows[-1]['steps'],'counts':counts,
        'maxima':maxima,'minima':minima,'integral_reviews':reviews,'quadrature_differences':differences,
        'within_budgets':flags,'all_trajectory_budgets_met':all(flags.values()),'steady_comparison':steady},rows


def time_comparison(base,refined):
    settings=base[0]['settings']
    times={0.0}
    accepted=[]
    for rows in [base,refined]:
        steps=[row for row in rows if row['kind']=='accepted']
        accepted.append(steps)
        times.update(row['time_s'] for row in rows if row['kind'] in ('accepted','sample'))
        for order in settings['verification']['entropy_quadrature_orders']:
            nodes,_=leggauss(order)
            for row in steps:
                left,right=row['dense_output']['start_time_s'],row['dense_output']['end_time_s']
                times.update(float((left+right)/2+(right-left)*node/2) for node in nodes)
    ends=[[row['time_s'] for row in steps] for steps in accepted]
    maximum,when,pressure_error=0.0,None,0.0
    species_count=len(settings['species_order'])
    rt=base[0]['gas_constant_j_mol_k']*settings['temperature_k']
    for at in sorted(times):
        values=[np.asarray(rows[1]['values']) if at==0 else polynomial(steps[bisect_left(right,at)],at)
            for rows,steps,right in zip([base,refined],accepted,ends,strict=True)]
        error=float(np.max(np.abs(values[0]-values[1])))
        if error>maximum: maximum,when=error,at
        delta=values[0].reshape(-1,species_count)-values[1].reshape(-1,species_count)
        pressure_error=max(pressure_error,rt*float(np.max(np.abs(delta.sum(axis=1)))))
    budget=settings['verification']
    return {'times_compared':len(times),'maximum_concentration_difference_mol_m3':maximum,'maximum_at_time_s':when,
        'maximum_pressure_difference_pa':pressure_error,'concentration_budget_mol_m3':budget['time_concentration_budget_mol_m3'],
        'pressure_budget_pa':budget['time_pressure_budget_pa'],
        'within_budget':maximum<=budget['time_concentration_budget_mol_m3'] and pressure_error<=budget['time_pressure_budget_pa'],
        'scope':'Union of both accepted endpoints, both 2/4-point dense quadrature nodes and common observations; compare native BDF polynomials. No continuous-time supremum claim.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    settings=json.loads(args.parameters.read_text())
    root=args.parameters.resolve().parent
    reports,records={},{}
    for key,path in settings['trajectories'].items():
        reports[key],records[key]=audit(root/path)
        print(json.dumps({'trajectory':key,'all_trajectory_budgets_met':reports[key]['all_trajectory_budgets_met']}),flush=True)
    comparison=time_comparison(records['base'],records['refined'])
    result={'settings':settings,'reports':reports,'time_comparison':comparison,
        'all_trajectory_and_time_budgets_met':all(row['all_trajectory_budgets_met'] for row in reports.values()) and comparison['within_budget'],
        'steady_spatial_and_flux_budgets_met':all(row['steady_comparison']['pressure_within_budget'] and row['steady_comparison']['flux_within_budget'] for row in reports.values()),
        'scope':'Exact pure-gas Darcy-Knudsen face reference, pore inventory, isothermal stream/bath energy and combined entropy. Steady analytic spatial qualification only; no whole-transient spatial or material qualification.',
        'material_qualified':False,'training_eligible':False}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({key:result[key] for key in ['all_trajectory_and_time_budgets_met','steady_spatial_and_flux_budgets_met','time_comparison']}),flush=True)


if __name__=='__main__':
    main()
