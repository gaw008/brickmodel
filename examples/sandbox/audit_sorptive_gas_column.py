"""Independent source/face equations and whole-column N/U/entropy accounting.

Geometry is reconstructed from root inputs. Entropy state decoding shares the
recorded host; direct liquid properties share IAPWS95. No material certificate.
"""
import argparse
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import time

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_sorptive_gas_cell import polynomial
from sorptive_gas_cell_setup import restore_sorptive_cell
from sorptive_source_formulas import source_for_column


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--trajectory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--local-balance-parameters',type=Path)
    parser.add_argument('--calorimetry-state-parameters',type=Path,
                        help='Use listed saved physical states for fixed-inventory thermal derivatives')
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());started=time.monotonic()
    local_policy=json.loads(args.local_balance_parameters.read_text()) if args.local_balance_parameters else None
    caloric_policy=json.loads(args.calorimetry_state_parameters.read_text()) if args.calorimetry_state_parameters else None
    def read_rows():
        with args.trajectory.open() as stream:
            for line in stream:
                yield json.loads(line)
    def accepted_rows():
        return (row for row in read_rows() if row['kind']=='accepted')
    records=read_rows();header=next(records);initial=next(records);records.close()
    config=header['parameters'];n=header['cell_count']
    species=config['boundary_program']['values']['species_order'];width=len(species)+1
    single=deepcopy(header);single['parameters']=deepcopy(config)
    for key in ('available_fluid_volume_m3','dry_mass_kg'):
        single['parameters']['cell'][key]/=n
    half=config['geometry']['length_m']/(2*n)
    boundary={**config['transfer'],'area_m2':config['geometry']['face_area_m2'],'cell_distance_m':half}
    internal={**boundary,'reservoir_distance_m':half,
              'reservoir_conductivity_w_m_k':config['transfer']['cell_conductivity_w_m_k']}
    single['parameters']['transfer']=boundary
    source=source_for_column(single,settings['source_quadrature'])
    geometry=header['geometry'];deltas={
        'available_fluid_volume_m3_per_cell':geometry['available_fluid_volume_m3_per_cell']-config['cell']['available_fluid_volume_m3']/n,
        'dry_mass_kg_per_cell':geometry['dry_mass_kg_per_cell']-config['cell']['dry_mass_kg']/n,
        'cell_width_m':geometry['cell_width_m']-2*half}
    for label,expected in [('internal_transfer',internal),('boundary_transfer',boundary)]:
        for key,value in expected.items():
            if isinstance(value,dict):
                for name,amount in value.items():
                    deltas[label+'.'+key+'.'+name]=geometry[label][key][name]-amount
            else:
                deltas[label+'.'+key]=geometry[label][key]-value

    def faces(at_time,states):
        return [source.between_states(a,b,internal) for a,b in zip(states[:-1],states[1:],strict=True)]+[
            source.fluxes(at_time,states[-1])]

    baseline=[sum(Fraction(initial['conserved_state'][i*width+k]) for i in range(n)) for k in range(width)]
    maxima={'energy_j':0.,'pressure_pa':0.,'mu_j_mol':0.};worst={}
    balances=[0.]*width;count=0;faces_count=0;face_n=face_u=0.;min_production=None
    entropy_by_time={};branch_counts={};phase_partition_max_mol=0.;caloric_states=[]
    free_water=config['schema']=='sorptive_free_water_column_v1'
    surface_water=config['schema']=='sorptive_evaporating_surface_column_v1'
    mobile_water=config['schema'] in ('source_sorptive_mobile_column_v1','sorptive_evaporating_surface_column_v1')
    surface_max={'inventory_mol_s':0.,'energy_w':0.,'temperature_k':0.,'pressure_pa':0.,'moisture_kg_kg':0.}
    condensed_fields_max={'condensed_chemical_potential_j_mol':0.,'condensed_partial_enthalpy_j_mol':0.}
    for row in read_rows():
        terminal=row
        if row['kind'] not in settings['source_state_kinds']:
            continue
        v=row['conserved_state']
        if caloric_policy is not None and row['kind'] in ('initial','sample') and row['time_s'] in caloric_policy['observation_times_s']:
            caloric_states.extend({'time_s':row['time_s'],'cell':i,'state':p} for i,p in enumerate(row['states']))
        for k in range(width):
            value=sum(Fraction(v[i*width+k]) for i in range(n))+Fraction(v[n*width+k])-baseline[k]
            balances[k]=max(balances[k],abs(float(value)))
        entropy=[]
        for i,p in enumerate(row['states']):
            q=source.reconstruct(p);count+=1;entropy.append(q['entropy_j_k'])
            if mobile_water:
                for key in condensed_fields_max:
                    condensed_fields_max[key]=max(condensed_fields_max[key],abs(q[key]-p[key]))
            branch=p['sorption_phase'] if free_water else ('source' if p['moisture_kg_kg_dry']>header['sorption_source']['join']['moisture_kg_kg'] else 'low')
            branch_counts[branch]=branch_counts.get(branch,0)+1
            if free_water:
                phase_partition_max_mol=max(phase_partition_max_mol,
                    abs(q['sorbed_water_mol']-p['sorbed_water_mol']),abs(q['free_water_mol']-p['free_water_mol']),
                    abs(p['free_water_mol']+p['sorbed_water_mol']-p['condensed_water_mol']))
            errors={'energy_j':q['internal_energy_j']-p['internal_energy_j'],
                    'pressure_pa':q['pressure_pa']-p['pressure_pa'],'mu_j_mol':q['mu_vapor_minus_condensed_j_mol']}
            for key,value in errors.items():
                if abs(value)>maxima[key]:
                    maxima[key]=abs(value);worst[key]={'time_s':row['time_s'],'cell':i,'signed_difference':value}
        entropy_by_time[(row['kind'],row['time_s'])]=math.fsum(entropy)
        if row['kind']=='accepted':
            for face_index,(original,review) in enumerate(zip(row['faces'],faces(row['time_s'],row['states']),strict=True)):
                faces_count+=1
                face_n=max(face_n,*(abs(review['net_mol_s'][k]-original['exchange']['net_mol_s'][k]) for k in species))
                face_u=max(face_u,abs(review['energy_out_w']-original['energy_out_w']))
                min_production=review['production_w_k'] if min_production is None else min(min_production,review['production_w_k'])
                if surface_water and face_index==n-1:
                    surface_max['inventory_mol_s']=max(surface_max['inventory_mol_s'],
                        *map(abs,original['inventory_rate_residuals_mol_s'].values()),
                        *map(abs,review['surface_inventory_residuals_mol_s'].values()))
                    surface_max['energy_w']=max(surface_max['energy_w'],abs(original['energy_rate_residual_w']),abs(review['surface_energy_residual_w']))
                    for key,field in [('temperature_k','temperature_k'),('pressure_pa','pressure_pa'),('moisture_kg_kg','moisture_kg_kg_dry')]:
                        surface_max[key]=max(surface_max[key],abs(original['surface'][field]-review['surface_state'][field]))
                    min_production=min(min_production,*review['individual_productions_w_k'])
    budget=settings['comparison_budgets'];calorimetry=[];entropy_results=[]
    with TemporaryDirectory(prefix='sorptive-column-audit-') as directory:
        host=restore_sorptive_cell(single,Path(directory))
        if caloric_policy is None:
            dt=settings['fixed_inventory_calorimetry']['temperature_step_k']
            probes=[{'temperature_k':t,'inventories_mol':initial['states'][0]['inventories_mol'],
                     'basis':'initial inventories, prescribed temperature'} for t in settings['fixed_inventory_calorimetry']['temperatures_k']]
        else:
            dt=caloric_policy['temperature_step_k']
            probes=[{'temperature_k':p['state']['temperature_k'],'inventories_mol':p['state']['inventories_mol'],
                     'basis':'saved physical trajectory state','time_s':p['time_s'],'cell':p['cell']} for p in caloric_states]
        for probe in probes:
            t=probe['temperature_k']
            states=[host.at_temperature(probe['inventories_mol'],t+d)[1] for d in [-dt,dt]]
            values=[source.reconstruct(p) for p in states]
            cv=(states[1]['constitutive_internal_energy_j']-states[0]['constitutive_internal_energy_j'])/(2*dt)
            tds=t*(values[1]['entropy_j_k']-values[0]['entropy_j_k'])/(2*dt)
            calorimetry.append({**probe,'cell_cv_j_k':cv,'t_ds_dt_j_k':tds,'difference_j_k':cv-tds})
        for degree in settings['quadrature_orders']:
            nodes,weights=leggauss(degree);seeds=[p['temperature_k'] for p in initial['states']]
            s0=entropy_by_time[('initial',initial['time_s'])];previous_s=s0
            external=production=0.;max_residual=0.;minimum_step=None;minimum_rate=None;steps=[]
            local_integrals=np.zeros((n,width));local_maxima=np.zeros(width)
            local_initial=np.array(initial['conserved_state'][:n*width]).reshape(n,width)
            for row in accepted_rows():
                dense=row['dense_output'];left,right=dense['start_time_s'],dense['end_time_s']
                half_step=(right-left)/2;center=(left+right)/2;previous_external=external
                for node,weight in zip(nodes,weights,strict=True):
                    at_time=float(center+half_step*node);v=polynomial(dense,at_time);states=[]
                    for i,cell in enumerate(v[:n*width].reshape(n,width)):
                        _,p=host.decode(dict(zip(species,map(float,cell[:-1]),strict=True)),float(cell[-1]),seeds[i])
                        seeds[i]=p['temperature_k'];states.append(p)
                    rates=faces(at_time,states);scale=float(half_step*weight)
                    if local_policy is not None:
                        for i,rate in enumerate(rates):
                            outward=np.array([rate['net_mol_s'][k] for k in species]+[rate['energy_out_w']])
                            local_integrals[i]-=scale*outward
                            if i+1<n:
                                local_integrals[i+1]+=scale*outward
                    external+=scale*rates[-1]['external_entropy_w_k']
                    production+=scale*math.fsum(p['production_w_k'] for p in rates)
                    local=min(p['production_w_k'] for p in rates)
                    if surface_water:
                        local=min(local,*rates[-1]['individual_productions_w_k'])
                        surface_max['inventory_mol_s']=max(surface_max['inventory_mol_s'],*map(abs,rates[-1]['surface_inventory_residuals_mol_s'].values()))
                        surface_max['energy_w']=max(surface_max['energy_w'],abs(rates[-1]['surface_energy_residual_w']))
                    minimum_rate=local if minimum_rate is None else min(minimum_rate,local)
                entropy=entropy_by_time[('accepted',row['time_s'])]
                residual=entropy-s0+external-production;step_change=entropy-previous_s+external-previous_external
                max_residual=max(max_residual,abs(residual));previous_s=entropy
                minimum_step=step_change if minimum_step is None else min(minimum_step,step_change)
                steps.append({'time_s':right,'entropy_balance_residual_j_k':residual,
                    'system_entropy_j_k':entropy,'external_entropy_integral_j_k':external,
                    'all_faces_production_integral_j_k':production,'step_total_entropy_change_j_k':step_change})
                if local_policy is not None:
                    local_now=np.array(row['conserved_state'][:n*width]).reshape(n,width)
                    residuals=local_now-local_initial-local_integrals
                    local_maxima=np.maximum(local_maxima,np.max(np.abs(residuals),axis=0))
                    steps[-1]['local_integrals']=local_integrals.tolist()
            result={'quadrature_order':degree,'maximum_entropy_balance_residual_j_k':max_residual,
                'minimum_step_total_entropy_change_j_k':minimum_step,'minimum_face_production_w_k':minimum_rate,
                'final_total_entropy_change_j_k':previous_s-s0+external,'steps':steps,
                'within_balance_budget':max_residual<=budget['entropy_balance_j_k'],
                'negative_steps_beyond_budget':sum(p['step_total_entropy_change_j_k'] < -budget['negative_step_entropy_allowance_j_k'] for p in steps)}
            if local_policy is not None:
                result['local_balance']={'maximum_species_residuals_mol':dict(zip(species,map(float,local_maxima[:-1]),strict=True)),
                    'maximum_energy_residual_j':float(local_maxima[-1]),
                    'within_budgets':bool(max(local_maxima[:-1])<=local_policy['inventory_balance_mol'] and local_maxima[-1]<=local_policy['energy_balance_j'])}
            entropy_results.append(result);print(json.dumps({k:v for k,v in result.items() if k!='steps'}),flush=True)
    low,high=entropy_results
    quadrature={key:max(abs(a[key]-b[key]) for a,b in zip(low['steps'],high['steps'],strict=True))
                for key in ('external_entropy_integral_j_k','all_faces_production_integral_j_k')}
    local_review=None
    if local_policy is not None:
        differences=np.max([np.max(np.abs(np.array(a['local_integrals'])-np.array(b['local_integrals'])),axis=0)
                            for a,b in zip(low['steps'],high['steps'],strict=True)],axis=0)
        local_review={'policy':local_policy,'maximum_integral_quadrature_differences':dict(zip(species+['energy_j'],map(float,differences),strict=True)),
            'within_quadrature_budgets':bool(max(differences[:-1])<=local_policy['inventory_quadrature_mol'] and differences[-1]<=local_policy['energy_quadrature_j']),
            'scope':'Each cell compared with independently integrated face fluxes, sealed left face; shared recorded equilibrium decoder, no material validation.'}
        for result in entropy_results:
            for step in result['steps']:
                del step['local_integrals']
    result={'trajectory':str(args.trajectory),'settings':settings,'cell_count':n,
        'completed':terminal['kind']=='summary' and terminal['status']=='completed',
        'source_state_count':count,'branch_state_counts':branch_counts,'source_maxima':maxima,'worst_source_states':worst,
        'maximum_inventory_balance_residual_mol':max(balances[:-1]),'maximum_energy_balance_residual_j':balances[-1],
        'geometry_differences':deltas,'face_reconstruction':{'faces':faces_count,'max_inventory_rate_difference_mol_s':face_n,
            'max_energy_rate_difference_w':face_u,'minimum_nominal_production_w_k':min_production},
        'fixed_inventory_calorimetry':calorimetry,'entropy_results':entropy_results,'quadrature_differences_j_k':quadrature,
        'within_budgets':{'source_energy':maxima['energy_j']<=budget['source_energy_j'],
            'source_pressure':maxima['pressure_pa']<=budget['source_pressure_pa'],
            'source_chemical_potential':maxima['mu_j_mol']<=budget['source_chemical_potential_j_mol'],
            'face_rates':face_n<=budget['face_inventory_mol_s'] and face_u<=budget['face_energy_w'],
            'geometry':max(map(abs,deltas.values()))<=settings['geometry_absolute_budget'],
            'fixed_inventory_calorimetry':all(p['cell_cv_j_k']>0 and abs(p['difference_j_k'])<=budget['calorimetry_j_k'] for p in calorimetry),
            'quadrature':max(quadrature.values())<=budget['entropy_quadrature_j_k']},
        'material_qualified':False,'training_eligible':False,
        'local_conservation_review':local_review,
        'scope':'Conditional trajectory, independent entropy/face/source integrals with shared equilibrium decoder and IAPWS backend.',
        'elapsed_s':time.monotonic()-started}
    if caloric_policy is not None:
        result['trajectory_calorimetry_policy']=caloric_policy
        result['within_budgets']['requested_calorimetry_states_observed']=len(caloric_states)==len(caloric_policy['observation_times_s'])*n
    if free_water:
        result['maximum_phase_partition_difference_mol']=phase_partition_max_mol
        result['within_budgets']['free_sorbed_partition']=phase_partition_max_mol<=budget['phase_partition_mol']
    if mobile_water:
        result['condensed_field_maxima']=condensed_fields_max
        result['within_budgets']['condensed_mu']=condensed_fields_max['condensed_chemical_potential_j_mol']<=budget['source_chemical_potential_j_mol']
        result['within_budgets']['condensed_h']=condensed_fields_max['condensed_partial_enthalpy_j_mol']<=budget['condensed_enthalpy_j_mol']
    if surface_water:
        result['surface_reconstruction_maxima']=surface_max
        result['within_budgets']['surface_mass_balance']=surface_max['inventory_mol_s']<=budget['surface_inventory_rate_mol_s']
        result['within_budgets']['surface_energy_balance']=surface_max['energy_w']<=budget['surface_energy_rate_w']
        result['within_budgets']['surface_state']=all(surface_max[k]<=budget['surface_'+k] for k in ('temperature_k','pressure_pa','moisture_kg_kg'))
    requested_checks=[result['completed'],*result['within_budgets'].values()]
    requested_checks.extend(p['within_balance_budget'] and p['negative_steps_beyond_budget']==0 for p in entropy_results)
    if local_policy is not None:
        requested_checks.extend(p['local_balance']['within_budgets'] for p in entropy_results)
        requested_checks.append(local_review['within_quadrature_budgets'])
    result['all_requested_numerical_budgets_met']=all(requested_checks)
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],
        'within_budgets':result['within_budgets'],'source_maxima':maxima,'elapsed_s':result['elapsed_s']},indent=2))


if __name__=='__main__':
    main()
