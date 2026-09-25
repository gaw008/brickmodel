"""Recorded one-dimensional sorptive profile/time comparisons and balances."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path

import numpy as np


def load(path):
    samples=[];events=[];counts={};checks=0;header=initial=last=None
    with path.open() as stream:
        for line in stream:
            row=json.loads(line);last=row;kind=row['kind'];counts[kind]=counts.get(kind,0)+1
            if kind=='input':
                header=row;species=header['parameters']['boundary_program']['values']['species_order'];width=len(species)+1
                balance=[0.]*width
                column=header['parameters']['schema'] in ('source_sorptive_common_gas_column_v1','sorptive_free_water_column_v1','source_sorptive_mobile_column_v1','sorptive_evaporating_surface_column_v1')
                n=header['cell_count'] if column else 1
            if kind in ('initial','sample','accepted','moisture_event'):
                states=row['states'] if column else [row['state']]
                v=row['conserved_state']
                totals=[sum(Fraction(v[i*width+k]) for i in range(n)) for k in range(width)]
                if kind=='initial':
                    initial=row;baseline=totals
                for k in range(width):
                    balance[k]=max(balance[k],abs(float(totals[k]+Fraction(v[n*width+k])-baseline[k])))
                checks+=width
                if kind in ('initial','sample'):
                    samples.append({'time_s':row['time_s'],'temperature_k':[s['temperature_k'] for s in states],
                        'pressure_pa':[s['pressure_pa'] for s in states],
                        'moisture_kg_kg':[s['moisture_kg_kg_dry'] for s in states],
                        'total_water_mol':math.fsum(s['inventories_mol']['H2O'] for s in states)})
                if kind=='moisture_event':
                    events.append({'time_s':row['time_s'],'target':row['moisture_target_kg_kg'],'transition':row['transition']})
    return {'path':str(path),'header':header,'cell_count':n,'samples':samples,'events':events,
        'summary':last,'completed':last['kind']=='summary' and last['status']=='completed',
        'record_counts':counts,'balance_observations':checks,'maximum_inventory_balance_residual_mol':max(balance[:-1]),
        'maximum_energy_balance_residual_j':balance[-1]}


def compare(left,right,budget,prefix):
    a,b=left['samples'],right['samples'];nl,nr=left['cell_count'],right['cell_count']
    if [r['time_s'] for r in a]!=[r['time_s'] for r in b] or nr%nl:
        raise ValueError('comparison requires common observation times and nested uniform meshes')
    maxima={'volume_mean_temperature_k':0.,'outer_cell_temperature_k':0.,'total_water_mol':0.,'mean_moisture_kg_kg':0.,'volume_mean_pressure_pa':0.}
    for x,y in zip(a,b,strict=True):
        averages=lambda key:np.array(y[key]).reshape(nl,nr//nl).mean(axis=1)
        maxima['volume_mean_temperature_k']=max(maxima['volume_mean_temperature_k'],float(np.max(np.abs(np.array(x['temperature_k'])-averages('temperature_k')))))
        maxima['outer_cell_temperature_k']=max(maxima['outer_cell_temperature_k'],abs(x['temperature_k'][-1]-y['temperature_k'][-1]))
        maxima['volume_mean_pressure_pa']=max(maxima['volume_mean_pressure_pa'],float(np.max(np.abs(np.array(x['pressure_pa'])-averages('pressure_pa')))))
        maxima['total_water_mol']=max(maxima['total_water_mol'],abs(x['total_water_mol']-y['total_water_mol']))
        maxima['mean_moisture_kg_kg']=max(maxima['mean_moisture_kg_kg'],abs(math.fsum(x['moisture_kg_kg'])/nl-math.fsum(y['moisture_kg_kg'])/nr))
    identities=lambda rows:[(p['target'],p['transition']) for p in rows]
    if identities(left['events'])!=identities(right['events']):
        raise ValueError('operational moisture event identities differ')
    event=max(abs(x['time_s']-y['time_s']) for x,y in zip(left['events'],right['events'],strict=True))
    return {'left':left['path'],'right':right['path'],'cell_counts':[nl,nr],'observations':len(a),'max_differences':maxima,
        'mean_moisture_event_difference_s':event,'budgets':budget,'budget_prefix':prefix,
        'both_completed':left['completed'] and right['completed'],
        'within_budgets':{'temperature':max(maxima['volume_mean_temperature_k'],maxima['outer_cell_temperature_k'])<=budget[prefix+'_temperature_k'],
            'water':maxima['total_water_mol']<=budget[prefix+'_total_water_mol'],
            'mean_moisture_event':event<=budget[prefix+'_moisture_event_s']}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    names={p[k] for p in settings['comparisons'] for k in ('left','right')}
    records={p:load(root/p) for p in sorted(names)}
    comparisons=[compare(records[p['left']],records[p['right']],settings['budgets'],p['type']) for p in settings['comparisons']]
    reports=[]
    for record in records.values():
        samples=record['samples'];last=samples[-1]
        reports.append({k:v for k,v in record.items() if k not in ('header','samples','summary')}|{
            'final_observation':last,'maximum_temperature_span_k':max(max(p['temperature_k'])-min(p['temperature_k']) for p in samples),
            'maximum_moisture_span_kg_kg':max(max(p['moisture_kg_kg'])-min(p['moisture_kg_kg']) for p in samples),
            'saved_temperature_range_k':[min(min(p['temperature_k']) for p in samples),max(max(p['temperature_k']) for p in samples)],
            'saved_pressure_range_pa':[min(min(p['pressure_pa']) for p in samples),max(max(p['pressure_pa']) for p in samples)]})
    result={'settings':settings,'trajectories':reports,'comparisons':comparisons,'material_qualified':False,'training_eligible':False,
        'scope':'Nested finite-volume profiles and operational mean-moisture crossing. Outer-cell temperature is a moving cell-center observable, not reconstructed wall temperature.'}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(comparisons,indent=2))


if __name__=='__main__':
    main()
