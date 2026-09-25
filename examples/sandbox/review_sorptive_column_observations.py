"""Stream large column records: all saved balances/faces and chosen source states.

State-source reconstructions are only at explicitly selected observation times;
face equations cover every saved accepted face. This is not dense entropy proof.
"""
import argparse
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

from sorptive_source_formulas import source_for_column


def review(path,settings):
    counts={};state_max={'energy_j':0.,'pressure_pa':0.,'mu_j_mol':0.};source_states=0
    face_n=face_u=0.;face_count=0;min_production=None;selected=[];max_occupancy=0.
    with path.open() as stream:
        header=json.loads(next(stream));config=header['parameters'];n=header['cell_count']
        species=config['boundary_program']['values']['species_order'];width=len(species)+1;balances=[0.]*width
        single=deepcopy(header);single['parameters']=deepcopy(config)
        single['parameters']['cell']['available_fluid_volume_m3']/=n
        single['parameters']['cell']['dry_mass_kg']/=n
        half=config['geometry']['length_m']/n/2
        boundary={**config['transfer'],'area_m2':config['geometry']['face_area_m2'],'cell_distance_m':half}
        internal={**boundary,'reservoir_distance_m':half,'reservoir_conductivity_w_m_k':config['transfer']['cell_conductivity_w_m_k']}
        single['parameters']['transfer']=boundary
        source=source_for_column(single,settings['source_quadrature'])
        for line in stream:
            row=json.loads(line);kind=row['kind'];counts[kind]=counts.get(kind,0)+1
            if kind not in ('initial','accepted','sample','moisture_event'):
                continue
            v=row['conserved_state'];states=row['states']
            totals=[sum(Fraction(v[i*width+k]) for i in range(n)) for k in range(width)]
            if kind=='initial':
                baseline=totals
            for k in range(width):
                balances[k]=max(balances[k],abs(float(totals[k]+Fraction(v[n*width+k])-baseline[k])))
            max_occupancy=max(max_occupancy,*(p['condensed_volume_m3']/single['parameters']['cell']['available_fluid_volume_m3'] for p in states))
            if kind in ('initial','sample') and row['time_s'] in settings['source_observation_times_s']:
                selected.append(row['time_s'])
                for p in states:
                    q=source.reconstruct(p);source_states+=1
                    for key,value in {'energy_j':q['internal_energy_j']-p['internal_energy_j'],
                        'pressure_pa':q['pressure_pa']-p['pressure_pa'],'mu_j_mol':q['mu_vapor_minus_condensed_j_mol']}.items():
                        state_max[key]=max(state_max[key],abs(value))
            if kind=='accepted':
                rates=[source.between_states(a,b,internal) for a,b in zip(states[:-1],states[1:],strict=True)]+[source.fluxes(row['time_s'],states[-1])]
                for actual,computed in zip(row['faces'],rates,strict=True):
                    face_count+=1
                    face_n=max(face_n,*(abs(computed['net_mol_s'][k]-actual['exchange']['net_mol_s'][k]) for k in species))
                    face_u=max(face_u,abs(computed['energy_out_w']-actual['energy_out_w']))
                    min_production=computed['production_w_k'] if min_production is None else min(min_production,computed['production_w_k'])
        last=row
    budget=settings['comparison_budgets']
    return {'trajectory':str(path),'cell_count':n,'record_counts':counts,
        'completed':last['kind']=='summary' and last['status']=='completed',
        'source_observation_times_s':selected,'all_requested_source_times_observed':selected==settings['source_observation_times_s'],
        'source_states':source_states,'source_maxima':state_max,
        'maximum_inventory_balance_residual_mol':max(balances[:-1]),'maximum_energy_balance_residual_j':balances[-1],
        'maximum_condensed_volume_fraction':max_occupancy,'accepted_faces':face_count,
        'maximum_face_inventory_difference_mol_s':face_n,'maximum_face_energy_difference_w':face_u,
        'minimum_saved_face_entropy_production_w_k':min_production,
        'within_budgets':{'source_energy':state_max['energy_j']<=budget['source_energy_j'],
            'source_pressure':state_max['pressure_pa']<=budget['source_pressure_pa'],
            'source_chemical_potential':state_max['mu_j_mol']<=budget['source_chemical_potential_j_mol'],
            'face_rates':face_n<=budget['face_inventory_mol_s'] and face_u<=budget['face_energy_w']}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent
    settings=json.loads(args.parameters.read_text());results=[]
    for path in settings['trajectories']:
        item=review(root/path,settings);results.append(item);print(json.dumps(item),flush=True)
    with args.output.open('x') as stream:
        json.dump({'settings':settings,'trajectories':results,'material_qualified':False,'training_eligible':False,
            'scope':'All saved global balances and accepted face formulas; direct IAPWS/source state review only at listed observations. Not dense entropy or material validation.'},
            stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':
    main()
