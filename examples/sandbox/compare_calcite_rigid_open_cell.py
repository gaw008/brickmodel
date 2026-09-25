"""Compare common physical observations from completed open-cell coordinate paths."""
import argparse
import json
from pathlib import Path


def read(path):
    samples = []
    with path.open() as stream:
        header = json.loads(next(stream))
        for line in stream:
            row = json.loads(line)
            if row['kind'] in ('initial','sample'):
                samples.append({'time_s':row['time_s'],**{k:row['state'][k] for k in ('temperature_k','pressure_pa','lime_mol','carbon_mol','nitrogen_mol')},
                    'surface_temperature_k':row['contact']['surface']['temperature_k']})
    return header,samples,row


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent;settings = json.loads(args.parameters.read_text())
    data = {k:read(root/path) for k,path in settings['trajectories'].items()};comparisons = []
    for left,right in settings['pairs']:
        _,a,end_a = data[left];_,b,end_b = data[right]
        if [s['time_s'] for s in a]!=[s['time_s'] for s in b]:
            raise ValueError('Open-cell comparison needs common observation times over the complete program')
        keys = ('temperature_k','pressure_pa','lime_mol','carbon_mol','nitrogen_mol','surface_temperature_k')
        maxima = {k:0. for k in keys};where = {k:None for k in keys}
        for x,y in zip(a,b,strict=True):
            for k in keys:
                difference = abs(x[k]-y[k])
                if difference>maxima[k]:maxima[k]=difference;where[k]=x['time_s']
        flags = {k:maxima[k]<=budget for k,budget in settings['budgets'].items()}
        flags['both_completed'] = all(row['kind']=='summary' and row['status']=='completed' for row in (end_a,end_b))
        comparisons.append({'left':left,'right':right,'observations':len(a),'maximum_differences':maxima,'maximum_difference_times_s':where,'within_budgets':flags})
    result = {'settings':settings,'comparisons':comparisons,'all_requested_time_budgets_met':all(all(r['within_budgets'].values()) for r in comparisons),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as out:json.dump(result,out,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps({'all_requested_time_budgets_met':result['all_requested_time_budgets_met']}))


if __name__=='__main__':main()
