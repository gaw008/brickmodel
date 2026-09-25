"""Frozen time, geometry-reference and adjacent-mesh physical observations."""
import argparse
import json
from pathlib import Path

import numpy as np


def read(path,format_name):
    result = []
    with path.open() as stream:
        header = json.loads(next(stream))
        for line in stream:
            row = json.loads(line)
            if row['kind'] not in ('initial','sample'):continue
            states = [row['state']] if format_name=='single_cell' else row['states']
            result.append({'time_s':row['time_s'],'temperature':np.array([s['temperature_k'] for s in states]),
                'pressure':np.array([s['pressure_pa'] for s in states]),'lime_mol':sum(s['lime_mol'] for s in states),
                'surface_temperature_k':row['contact']['surface']['temperature_k'],
                'surface_pressure_pa':row['contact']['surface']['pressure_pa']})
    return header,result,row


def mean(values,widths):
    return values.mean() if widths is None else np.average(values,weights=widths)


def compare(a,b,widths_a=None,widths_b=None):
    if [r['time_s'] for r in a]!=[r['time_s'] for r in b]:raise ValueError('Comparison requires identical physical observation times')
    na,nb = len(a[0]['temperature']),len(b[0]['temperature']);ratio = nb//na
    maxima = {k:0. for k in ['mean_temperature_k','cell_temperature_k','mean_pressure_pa','cell_pressure_pa','total_lime_mol','surface_temperature_k','surface_pressure_pa']}
    where = {k:None for k in maxima}
    for left,right in zip(a,b,strict=True):
        def project(values):
            matrix = values.reshape(na,ratio)
            return matrix.mean(axis=1) if widths_b is None else np.average(matrix,axis=1,weights=np.array(widths_b).reshape(na,ratio))
        differences = {'mean_temperature_k':abs(mean(left['temperature'],widths_a)-mean(right['temperature'],widths_b)),
            'cell_temperature_k':np.max(np.abs(left['temperature']-project(right['temperature']))),
            'mean_pressure_pa':abs(mean(left['pressure'],widths_a)-mean(right['pressure'],widths_b)),
            'cell_pressure_pa':np.max(np.abs(left['pressure']-project(right['pressure']))),
            'total_lime_mol':abs(left['lime_mol']-right['lime_mol']),
            'surface_temperature_k':abs(left['surface_temperature_k']-right['surface_temperature_k']),
            'surface_pressure_pa':abs(left['surface_pressure_pa']-right['surface_pressure_pa'])}
        for key,value in differences.items():
            if value>maxima[key]:maxima[key] = float(value);where[key] = left['time_s']
    return {'observations':len(a),'cell_counts':[na,nb],'maximum_differences':maxima,'maximum_difference_times_s':where}


def event_time(rows,event,widths=None):
    selection = [r for r in rows if event['start_s']<=r['time_s']<=event['end_s']]
    direction = event['direction'];target = event['mean_temperature_k']
    for before,after in zip(selection[:-1],selection[1:],strict=True):
        a,b = mean(before['temperature'],widths),mean(after['temperature'],widths)
        if direction*(a-target)<0<=direction*(b-target):
            return float(before['time_s']+(after['time_s']-before['time_s'])*(target-a)/(b-a))
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent;settings = json.loads(args.parameters.read_text())
    records = {k:read(root/p['trajectory'],p['format']) for k,p in settings['records'].items()}
    events = {name:{e['name']:event_time(data[1],e,data[0].get('cell_widths_m')) for e in settings['events']} for name,data in records.items()}
    reports = []
    for pair in settings['pairs']:
        left,right = pair['left'],pair['right'];report = compare(records[left][1],records[right][1],records[left][0].get('cell_widths_m'),records[right][0].get('cell_widths_m'))
        budgets = settings[pair['kind']+'_budgets'];flags = {k:report['maximum_differences'][k]<=v for k,v in budgets.items()}
        differences = {key:abs(events[left][key]-events[right][key]) if events[left][key] is not None and events[right][key] is not None else None for key in events[left]}
        if pair['kind']=='space':
            flags.update({key:value is not None and value<=settings['space_event_budget_s'] for key,value in differences.items()})
        flags['both_completed'] = all(records[name][2]['kind']=='summary' and records[name][2]['status']=='completed' for name in (left,right))
        report.update(pair=pair,event_differences_s=differences,within_budgets=flags,all_requested_budgets_met=all(flags.values()))
        reports.append(report)
    result = {'settings':settings,'events_s':events,'comparisons':reports,
        'all_requested_budgets_met':all(r['all_requested_budgets_met'] for r in reports),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_budgets_met':result['all_requested_budgets_met']}))


if __name__=='__main__':
    main()
