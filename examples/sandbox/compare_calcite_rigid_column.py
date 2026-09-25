"""Frozen time/space comparisons over all saved column observations."""
import argparse
import json
from pathlib import Path
import numpy as np


def observations(path):
    out=[]
    with path.open() as stream:
        header=json.loads(next(stream))
        for line in stream:
            row=json.loads(line)
            if row['kind'] in ('initial','sample'):out.append(row)
    return header,out


def temperature_event(rows,target):
    previous=rows[0];before=max(s['temperature_k'] for s in previous['states'])-min(s['temperature_k'] for s in previous['states'])
    for row in rows[1:]:
        after=max(s['temperature_k'] for s in row['states'])-min(s['temperature_k'] for s in row['states'])
        if before>target>=after:
            return previous['time_s']+(row['time_s']-previous['time_s'])*(before-target)/(before-after)
        previous=row;before=after
    return None


def compare(a,b):
    if [r['time_s'] for r in a]!=[r['time_s'] for r in b]:raise ValueError('observation times differ')
    na=len(a[0]['states']);nb=len(b[0]['states']);ratio=nb//na
    metrics={k:0. for k in ('mean_temperature_k','cell_average_temperature_k','mean_pressure_pa','cell_average_pressure_pa','total_lime_mol')}
    where={k:None for k in metrics}
    for left,right in zip(a,b,strict=True):
        lt,rt=[np.array([s['temperature_k'] for s in row['states']]) for row in (left,right)]
        lp,rp=[np.array([s['pressure_pa'] for s in row['states']]) for row in (left,right)]
        values={'mean_temperature_k':abs(lt.mean()-rt.mean()),'cell_average_temperature_k':np.max(np.abs(lt-rt.reshape(na,ratio).mean(axis=1))),
            'mean_pressure_pa':abs(lp.mean()-rp.mean()),'cell_average_pressure_pa':np.max(np.abs(lp-rp.reshape(na,ratio).mean(axis=1))),
            'total_lime_mol':abs(sum(s['lime_mol'] for s in left['states'])-sum(s['lime_mol'] for s in right['states']))}
        for k,v in values.items():
            if v>metrics[k]:metrics[k]=float(v);where[k]=left['time_s']
    return {'observations':len(a),'cell_counts':[na,nb],'maximum_differences':metrics,'time_of_maximum_difference_s':where}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());budget=settings['budgets']
    records={k:observations(root/v) for k,v in settings['trajectories'].items()};time=[];space=[]
    for left,right in settings['time_pairs']:
        report=compare(records[left][1],records[right][1]);m=report['maximum_differences']
        report.update(left=left,right=right,within_budgets=m['cell_average_temperature_k']<=budget['time_temperature_k'] and m['cell_average_pressure_pa']<=budget['time_pressure_pa'] and m['total_lime_mol']<=budget['time_total_lime_mol']);time.append(report)
    events={k:temperature_event(rows,settings['event']['temperature_range_target_k']) for k,(_,rows) in records.items()}
    for left,right in settings['space_pairs']:
        report=compare(records[left][1],records[right][1]);m=report['maximum_differences'];ea,eb=events[left],events[right]
        difference=abs(ea-eb) if ea is not None and eb is not None else None
        flags={key:m[key]<=budget['space_'+key] for key in ('mean_temperature_k','cell_average_temperature_k','mean_pressure_pa','total_lime_mol')}
        flags['event_time']=difference is not None and difference<=budget['space_event_time_s']
        report.update(left=left,right=right,event_difference_s=difference,within_budgets=flags,all_requested_space_budgets_met=all(flags.values()));space.append(report)
    _,reference=observations(root/settings['two_cell_reference']);path=compare(reference,records['two-refined'][1]);m=path['maximum_differences']
    path['within_budgets']=m['cell_average_temperature_k']<=budget['two_cell_path_temperature_k'] and m['cell_average_pressure_pa']<=budget['two_cell_path_pressure_pa']
    totals={}
    for name,(header,rows) in records.items():
        s=rows[0]['states'];totals[name]={k:sum(x[k] for x in s) for k in ('carbon_mol','nitrogen_mol','internal_energy_j')}
    result={'settings':settings,'initial_totals':totals,'two_cell_reference_comparison':path,'time_comparisons':time,'space_comparisons':space,
        'temperature_equalization_events_s':events,'all_requested_time_budgets_met':all(v['within_budgets'] for v in time),
        'all_requested_space_budgets_met':all(v['all_requested_space_budgets_met'] for v in space) if space else None,
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({k:result[k] for k in ('all_requested_time_budgets_met','all_requested_space_budgets_met')}))


if __name__=='__main__':main()
