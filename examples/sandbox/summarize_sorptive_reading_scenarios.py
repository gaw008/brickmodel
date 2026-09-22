"""Describe endpoint-scenario sensitivity without claiming prediction bounds."""
import argparse
import json
from pathlib import Path


def trajectory(path):
    events=[];samples=[]
    with path.open() as stream:
        for line in stream:
            row=json.loads(line)
            if row['kind']=='initial':
                initial=row
            if row['kind']=='moisture_event':
                events.append(row['time_s'])
            if row['kind']=='sample':
                samples.append(row)
    return {'path':str(path),'completed':row['kind']=='summary' and row['status']=='completed',
        'initial_inventories_mol':initial['state']['inventories_mol'],
        'initial_energy_j':initial['state']['internal_energy_j'],
        'moisture_event_times_s':events,
        'final_temperature_k':samples[-1]['state']['temperature_k'],
        'final_moisture_kg_kg':samples[-1]['state']['moisture_kg_kg_dry'],
        'minimum_saved_temperature_k':min(p['state']['temperature_k'] for p in samples)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    nominal=trajectory(root/settings['nominal_trajectory']);results=[]
    for scenario in settings['scenarios']:
        name=scenario['name'];folder=root/settings['output_directory']
        result=trajectory(folder/(name+'-base.jsonl'))
        review=json.loads((folder/(name+'-source-review.json')).read_text())
        holdout=review['same_curve_holdout'];low,high=holdout['source_digitization_bounds']
        result.update({'scenario':scenario,'event_shift_from_nominal_s':result['moisture_event_times_s'][0]-nominal['moisture_event_times_s'][0],
            'reference_activity_holdout':holdout,
            'within_same_curve_holdout_reading_interval':low<=holdout['model_activity']<=high,
            'physical_qualification':'conditional endpoint scenario, not a validated source-consistent material'})
        results.append(result)
    output={'settings':settings,'nominal':nominal,'scenarios':results,
        'scope':'T/P/W initial design is fixed, while equilibrium initial gas inventory/U follow each scenario. Reading-interval consistency is distinct from thermodynamic identity and numerical budget checks. These two selected trajectories are not extrema, confidence limits or material predictions.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(output,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    main()
