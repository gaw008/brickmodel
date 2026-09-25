"""Recorded-time volume and parent-cell spatial comparison of closed columns."""
import argparse
import json
from pathlib import Path

import numpy as np


def load(path):
    samples={}
    with path.open() as stream:
        header=json.loads(next(stream))
        for line in stream:
            row=json.loads(line);terminal=row
            if row['kind'] not in ('initial','sample'):continue
            states=row['states'];names=list(states[0]['amounts_mol'])
            samples[row['time_s']]={'temperature':np.array([s['temperature_k'] for s in states]),
                'pressure':np.array([s['pressure_pa'] for s in states]),
                'amounts':np.array([[s['amounts_mol'][k] for k in names] for s in states])}
    return header,samples,names,terminal


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    data={name:load(root/path) for name,path in settings['records'].items()};results=[]
    for left_name,right_name in settings['pairs']:
        lh,left,names,lt=data[left_name];rh,right,rnames,rt=data[right_name];nl,nr=lh['cell_count'],rh['cell_count'];factor=nr//nl
        maxima={k:0. for k in ['mean_temperature_k','coarse_cell_temperature_k','mean_pressure_pa','coarse_cell_pressure_pa','total_species_mol']};times={k:None for k in maxima}
        species_max=np.zeros(len(names))
        for t,a in left.items():
            b=right[t];tdiff=a['temperature']-b['temperature'].reshape(nl,factor).mean(axis=1)
            pdiff=a['pressure']-b['pressure'].reshape(nl,factor).mean(axis=1)
            ndiff=np.abs(a['amounts'].sum(axis=0)-b['amounts'].sum(axis=0));species_max=np.maximum(species_max,ndiff)
            values={'mean_temperature_k':abs(float(a['temperature'].mean()-b['temperature'].mean())),
                'coarse_cell_temperature_k':float(max(abs(tdiff))),
                'mean_pressure_pa':abs(float(a['pressure'].mean()-b['pressure'].mean())),
                'coarse_cell_pressure_pa':float(max(abs(pdiff))),'total_species_mol':float(max(ndiff))}
            for k,v in values.items():
                if v>maxima[k]:maxima[k]=v;times[k]=t
        flags={k:maxima[k]<=v for k,v in settings['space_budgets'].items()}
        flags.update(same_observation_times=left.keys()==right.keys(),same_species_order=names==rnames,
                     both_completed=lt['kind']=='summary' and rt['kind']=='summary' and lt['status']=='completed' and rt['status']=='completed')
        results.append({'pair':[left_name,right_name],'cell_counts':[nl,nr],'observations':len(left),'maximum_differences':maxima,
            'maximum_difference_times_s':times,'maximum_total_species_differences_mol':dict(zip(names,map(float,species_max),strict=True)),
            'within_budgets':flags,'all_requested_budgets_met':all(flags.values())})
    output={'settings':settings,'comparisons':results,'all_requested_budgets_met':all(r['all_requested_budgets_met'] for r in results),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(output,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(results))


if __name__=='__main__':main()
