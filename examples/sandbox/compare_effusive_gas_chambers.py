"""Common-observation time accuracy of the finite effusive gas chambers."""
import argparse
import json
from pathlib import Path

import numpy as np


def read(path):
    observations=[]
    with path.open() as stream:
        for line in stream:
            row=json.loads(line)
            if row['kind'] in ('initial','sample'):
                observations.append({'time_s':row['time_s'],
                    'temperature_k':[s['temperature_k'] for s in row['states']],
                    'pressure_pa':[s['pressure_pa'] for s in row['states']],
                    'species_mol':[row['values'][i] for i in (0,1,3,4)]})
    return observations,row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    a,final_a=read(root/settings['trajectories']['base']);b,final_b=read(root/settings['trajectories']['refined'])
    if [r['time_s'] for r in a]!=[r['time_s'] for r in b]:raise ValueError('Observation times differ')
    maxima={k:0. for k in ('temperature_k','pressure_pa','species_mol')};where={k:None for k in maxima}
    for left,right in zip(a,b,strict=True):
        for k in maxima:
            difference=float(np.max(np.abs(np.array(left[k])-np.array(right[k]))))
            if difference>maxima[k]:maxima[k]=difference;where[k]=left['time_s']
    flags={k:value<=settings['budgets']['time_'+k] for k,value in maxima.items()}
    flags['both_completed']=all(r['kind']=='summary' and r['status']=='completed' for r in (final_a,final_b))
    result={'settings':settings,'common_observations':len(a),'maximum_differences':maxima,
        'times_of_maximum_s':where,'within_budgets':flags,'all_requested_budgets_met':all(flags.values()),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_budgets_met':result['all_requested_budgets_met']}))


if __name__=='__main__':
    main()
