"""Locate free-water and recorded-sorption interfaces in saved BDF trajectories.

Uses the frozen production inverse for dense states. These are numerical
events in the declared potential, not measured drying-front observations.
"""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scipy.optimize import brentq

from audit_sorptive_gas_cell import polynomial
from sorptive_gas_cell_setup import restore_sorptive_cell


def locate(path,settings):
    events=[]
    with path.open() as stream,TemporaryDirectory(prefix='sorptive-phase-events-') as directory:
        header=json.loads(next(stream));previous=json.loads(next(stream))
        config=header['parameters'];species=config['boundary_program']['values']['species_order'];width=len(species)+1
        host=restore_sorptive_cell({**header,'parameters':header['cell_parameters']},Path(directory))
        policy=config['observation'];n=header['cell_count']
        def score(state,interface):
            w=state['moisture_kg_kg_dry']
            if interface=='free_water':
                return w-host.excess.saturation(state['temperature_k'])['moisture_kg_kg']
            return w-settings['source_interfaces_kg_kg'][interface]
        for line in stream:
            row=json.loads(line)
            if row['kind']!='accepted':
                continue
            for index,(before,after) in enumerate(zip(previous['states'],row['states'],strict=True)):
                for interface in ['free_water',*settings['source_interfaces_kg_kg']]:
                    lo,hi=score(before,interface),score(after,interface)
                    if (lo>0)==(hi>0):
                        continue
                    def state_at(t):
                        vector=polynomial(row['dense_output'],t)[index*width:(index+1)*width]
                        return host.decode(dict(zip(species,map(float,vector[:-1]),strict=True)),float(vector[-1]),before['temperature_k'])[1]
                    event=brentq(lambda t:score(state_at(t),interface),previous['time_s'],row['time_s'],
                        xtol=policy['moisture_event_absolute_time_tolerance_s'],
                        rtol=policy['moisture_event_relative_tolerance'],maxiter=policy['moisture_event_maximum_iterations'])
                    state=state_at(event)
                    events.append({'interface':interface,'cell':index,'cell_center_m':header['geometry']['cell_centers_m'][index],
                        'direction':'decreasing' if hi<lo else 'increasing','time_s':event,
                        'accepted_bracket_s':[previous['time_s'],row['time_s']],
                        'event_residual_kg_kg':score(state,interface),'temperature_k':state['temperature_k'],
                        'total_condensed_moisture_kg_kg':state['moisture_kg_kg_dry'],
                        'free_water_mol':state['free_water_mol'],'sorbed_water_mol':state['sorbed_water_mol']})
            previous=row
        terminal=row
    return {'trajectory':str(path),'cell_count':n,
        'completed':terminal['kind']=='summary' and terminal['status']=='completed','events':events,
        'scope':'Every accepted sign-change bracket; no proof that a step cannot contain unobserved paired crossings.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    records={path:locate(root/path,settings) for path in settings['trajectories']}
    comparisons=[]
    for pair in settings['same_mesh_comparisons']:
        left,right=(records[pair[key]] for key in ('left','right'))
        identity=lambda p:(p['interface'],p['cell'],p['direction'])
        identities_equal=[identity(p) for p in left['events']]==[identity(p) for p in right['events']]
        differences=[abs(a['time_s']-b['time_s']) for a,b in zip(left['events'],right['events'],strict=True)] if identities_equal else []
        maximum=max(differences) if differences else None
        comparisons.append({'left':pair['left'],'right':pair['right'],'same_event_identities':identities_equal,
            'maximum_event_time_difference_s':maximum,
            'within_budget':maximum is not None and maximum<=settings['event_time_budget_s']})
    output={'settings':settings,'trajectories':list(records.values()),'comparisons':comparisons,
            'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(output,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'event_counts':{k:len(v['events']) for k,v in records.items()},'comparisons':comparisons},indent=2))


if __name__=='__main__':
    main()
