"""Source equations, exact inventory/U accounting and dense entropy integration.

Entropy decoding reuses the recorded physical host; entropy, caloric reference
and face transport expressions are independently reconstructed from source
facts. Direct liquid IAPWS shares the source EOS backend. No material proof.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

import numpy as np
from numpy.polynomial.legendre import leggauss

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sorptive_source_formulas import SorptiveSource
from sorptive_gas_cell_setup import restore_sorptive_cell


def polynomial(record,t):
    products=np.cumprod((t-np.array(record['shifts_s']))/np.array(record['denominators_s']))
    differences=np.array(record['differences'])
    return differences[0]+differences[1:].T@products


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',required=True,type=Path)
    parser.add_argument('--trajectory',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    settings=json.loads(args.parameters.read_text());started=time.monotonic()
    rows=[json.loads(line) for line in args.trajectory.read_text().splitlines()]
    header=rows[0];config=header['parameters']
    source=SorptiveSource(header,settings['source_quadrature'])
    species=config['boundary_program']['values']['species_order'];width=len(species)+1
    initial=rows[1];baseline=list(map(Fraction,initial['conserved_state'][:width]))
    balance=[0.]*width;reconstructions=[];face_n=face_u=0.;face_min=None
    accepted=[row for row in rows if row['kind']=='accepted']
    for row in rows:
        if row['kind'] not in ('initial','accepted','sample','moisture_event'):
            continue
        state=row['state'];new=source.reconstruct(state);v=row['conserved_state']
        for i in range(width):
            balance[i]=max(balance[i],abs(float(Fraction(v[i])+Fraction(v[width+i])-baseline[i])))
        reconstructions.append({'kind':row['kind'],'time_s':row['time_s'],
            'source_energy_residual_j':new['internal_energy_j']-state['internal_energy_j'],
            'source_pressure_residual_pa':new['pressure_pa']-state['pressure_pa'],
            'source_mu_residual_j_mol':new['mu_vapor_minus_condensed_j_mol'],
            'source_entropy_j_k':new['entropy_j_k'],'dry_cp_j_kg_k':new['dry_cp_j_kg_k']})
        if row['kind']=='accepted':
            face=source.fluxes(row['time_s'],state)
            face_n=max(face_n,*(abs(value-row['face']['exchange']['net_mol_s'][key]) for key,value in face['net_mol_s'].items()))
            face_u=max(face_u,abs(face['energy_out_w']-row['face']['energy_out_w']))
            face_min=face['production_w_k'] if face_min is None else min(face_min,face['production_w_k'])
    budget=settings['comparison_budgets']
    maxima={key:max(abs(p[key]) for p in reconstructions) for key in
            ('source_energy_residual_j','source_pressure_residual_pa','source_mu_residual_j_mol')}
    entropy_results=[];calorimetry=[]
    with TemporaryDirectory(prefix='brick-sorptive-audit-') as directory:
        cell=restore_sorptive_cell(header,Path(directory))
        initial_inventory=initial['state']['inventories_mol']
        dt=settings['fixed_inventory_calorimetry']['temperature_step_k']
        for t in settings['fixed_inventory_calorimetry']['temperatures_k']:
            states=[cell.at_temperature(initial_inventory,t+d)[1] for d in [-dt,dt]]
            values=[source.reconstruct(s) for s in states]
            cv=(states[1]['constitutive_internal_energy_j']-states[0]['constitutive_internal_energy_j'])/(2*dt)
            tds=t*(values[1]['entropy_j_k']-values[0]['entropy_j_k'])/(2*dt)
            calorimetry.append({'temperature_k':t,'fixed_n_v_dry_mass_cv_j_k':cv,
                't_ds_dt_j_k':tds,'difference_j_k':cv-tds})
        for degree in settings['quadrature_orders']:
            nodes,weights=leggauss(degree);seed=initial['state']['temperature_k']
            s0=source.reconstruct(initial['state'])['entropy_j_k'];previous_s=s0
            external=production=0.;max_residual=0.;minimum_step=None;minimum_rate=None
            steps=[]
            for row in accepted:
                dense=row['dense_output'];left,right=dense['start_time_s'],dense['end_time_s']
                half=(right-left)/2;center=(right+left)/2
                previous_external=external
                for node,weight in zip(nodes,weights,strict=True):
                    t=float(center+half*node);v=polynomial(dense,t)
                    _,p=cell.decode(dict(zip(species,map(float,v[:len(species)]),strict=True)),float(v[len(species)]),seed)
                    seed=p['temperature_k'];rates=source.fluxes(t,p)
                    external+=float(half*weight)*rates['external_entropy_w_k']
                    production+=float(half*weight)*rates['production_w_k']
                    minimum_rate=rates['production_w_k'] if minimum_rate is None else min(minimum_rate,rates['production_w_k'])
                entropy=source.reconstruct(row['state'])['entropy_j_k']
                residual=entropy-s0+external-production
                step_change=entropy-previous_s+external-previous_external
                minimum_step=step_change if minimum_step is None else min(minimum_step,step_change)
                max_residual=max(max_residual,abs(residual));previous_s=entropy
                steps.append({'time_s':right,'entropy_balance_residual_j_k':residual,
                    'system_entropy_j_k':entropy,'external_entropy_integral_j_k':external,
                    'face_production_integral_j_k':production,'step_total_entropy_change_j_k':step_change})
            result={'quadrature_order':degree,'maximum_entropy_balance_residual_j_k':max_residual,
                'minimum_step_total_entropy_change_j_k':minimum_step,'minimum_face_production_w_k':minimum_rate,
                'final_total_entropy_change_j_k':previous_s-s0+external,'steps':steps,
                'within_balance_budget':max_residual<=budget['entropy_balance_j_k'],
                'negative_steps_beyond_budget':sum(p['step_total_entropy_change_j_k'] < -budget['negative_step_entropy_allowance_j_k'] for p in steps)}
            entropy_results.append(result)
            print(json.dumps({k:v for k,v in result.items() if k!='steps'}),flush=True)
    low,high=entropy_results
    quadrature={key:max(abs(a[key]-b[key]) for a,b in zip(low['steps'],high['steps'],strict=True))
                for key in ('external_entropy_integral_j_k','face_production_integral_j_k')}
    result={'trajectory':str(args.trajectory),'settings':settings,
        'completed':rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        'time_interval_s':[initial['time_s'],accepted[-1]['time_s']],
        'balance_observations':len(reconstructions)*width,'max_inventory_balance_residual_mol':max(balance[:-1]),
        'max_energy_balance_residual_j':balance[-1],'source_maxima':maxima,'reconstructions':reconstructions,
        'face_reconstruction':{'accepted_faces':len(accepted),'max_inventory_rate_difference_mol_s':face_n,
            'max_energy_rate_difference_w':face_u,'minimum_nominal_production_w_k':face_min},
        'fixed_inventory_calorimetry':calorimetry,'entropy_results':entropy_results,'quadrature_differences_j_k':quadrature,
        'within_budgets':{'source_energy':maxima['source_energy_residual_j']<=budget['source_energy_j'],
            'source_pressure':maxima['source_pressure_residual_pa']<=budget['source_pressure_pa'],
            'source_chemical_potential':maxima['source_mu_residual_j_mol']<=budget['source_chemical_potential_j_mol'],
            'face_rates':face_n<=budget['face_inventory_mol_s'] and face_u<=budget['face_energy_w'],
            'fixed_inventory_calorimetry':all(p['fixed_n_v_dry_mass_cv_j_k']>0 and abs(p['difference_j_k'])<=budget['calorimetry_j_k'] for p in calorimetry),
            'quadrature':max(quadrature.values())<=budget['entropy_quadrature_j_k']},
        'material_qualified':False,'training_eligible':False,
        'scope':'Saved conditional trajectory; shared state decoder and direct EOS backend. Numerical/source agreement is not experimental accuracy or universal entropy proof.',
        'elapsed_s':time.monotonic()-started}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'within_budgets':result['within_budgets'],'source_maxima':maxima,'quadrature_differences_j_k':quadrature,
                      'elapsed_s':result['elapsed_s']},indent=2))


if __name__ == '__main__':
    main()
