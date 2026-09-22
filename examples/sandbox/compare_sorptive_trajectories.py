"""Compare completed common-gas sorptive trajectories at saved observations.

Additional moisture crossings are reconstructed from recorded BDF polynomials
and the frozen source host. This is a numerical study, not material validation.
"""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scipy.optimize import brentq

from audit_sorptive_gas_cell import polynomial
from sorptive_gas_cell_setup import restore_sorptive_cell


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def crossings(rows,targets):
    header=rows[0];config=header['parameters'];policy=config['observation']
    species=config['boundary_program']['values']['species_order']
    previous=rows[1];events=[]
    with TemporaryDirectory(prefix='sorptive-crossing-') as name:
        host=restore_sorptive_cell(header,Path(name))
        for row in rows:
            if row['kind']!='accepted':
                continue
            for target in targets:
                left=previous['state']['moisture_kg_kg_dry']-target
                right=row['state']['moisture_kg_kg_dry']-target
                if (left>0)==(right>0):
                    continue
                def score(at_time):
                    v=polynomial(row['dense_output'],at_time)
                    _,state=host.decode(dict(zip(species,map(float,v[:len(species)]),strict=True)),
                        float(v[len(species)]),previous['state']['temperature_k'])
                    return state['moisture_kg_kg_dry']-target
                time=brentq(score,previous['time_s'],row['time_s'],
                    xtol=policy['moisture_event_absolute_time_tolerance_s'],
                    rtol=policy['moisture_event_relative_tolerance'],maxiter=policy['moisture_event_maximum_iterations'])
                events.append({'target_kg_kg':target,'time_s':time,'direction':'decreasing' if right<left else 'increasing',
                    'accepted_bracket_s':[previous['time_s'],row['time_s']]})
            previous=row
    return events


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent
    settings=json.loads(args.parameters.read_text());results=[]
    for case in settings['comparisons']:
        left,right=(load(root/case[k]) for k in ('left','right'))
        observations=lambda rows:[p for p in rows if p['kind'] in ('initial','sample')]
        a,b=observations(left),observations(right)
        if [p['time_s'] for p in a]!=[p['time_s'] for p in b]:
            raise ValueError('comparison requires identical saved observation times')
        differences={key:max(abs(x['state'][key]-y['state'][key]) for x,y in zip(a,b,strict=True)) for key in
                     ('temperature_k','pressure_pa','moisture_kg_kg_dry')}
        water=max(abs(x['state']['inventories_mol']['H2O']-y['state']['inventories_mol']['H2O']) for x,y in zip(a,b,strict=True))
        events=[crossings(rows,settings['source_branch_moisture_events_kg_kg']) for rows in (left,right)]
        identity=lambda rows:[(p['target_kg_kg'],p['direction']) for p in rows]
        if identity(events[0])!=identity(events[1]):
            raise ValueError('moisture event identities differ')
        event_difference=[{'target_kg_kg':x['target_kg_kg'],'time_difference_s':abs(x['time_s']-y['time_s'])} for x,y in zip(*events,strict=True)]
        target=left[0]['parameters']['observation']['moisture_target_kg_kg']
        target_difference=max(p['time_difference_s'] for p in event_difference if p['target_kg_kg']==target)
        budget=case['budgets']
        results.append({'case':case,'both_completed':all(p[-1]['kind']=='summary' and p[-1]['status']=='completed' for p in (left,right)),
            'observations':len(a),'max_differences':differences,'max_total_water_difference_mol':water,
            'moisture_events':events,'event_differences':event_difference,
            'within_budgets':{'temperature':differences['temperature_k']<=budget['time_temperature_k'],
                'water':water<=budget['time_total_water_mol'],'specified_event':target_difference<=budget['time_moisture_event_s']}})
    result={'settings':settings,'results':results,'material_qualified':False,'training_eligible':False,
        'scope':'Saved nominal trajectory comparisons. Additional source-knot crossings use the same frozen decoder, not an independent EOS.'}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    main()
