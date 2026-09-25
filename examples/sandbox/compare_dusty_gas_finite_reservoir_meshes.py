"""Compare finite-vessel pressures and same-volume pore averages on union BDF nodes."""
import argparse
from bisect import bisect_left
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_maxwell_stefan_binary_column import polynomial


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); settings=json.loads(args.parameters.read_text()); root=args.parameters.resolve().parent
    records={}
    for name,path in settings['records'].items():
        with (root/path).open() as stream:
            records[name]=[json.loads(line) for line in stream]
    results=[]
    for coarse,fine in settings['pairs']:
        a,b=records[coarse],records[fine]
        times={0.}; accepted=[]
        for rows in [a,b]:
            steps=[row for row in rows if row['kind']=='accepted']; accepted.append(steps)
            times.update(row['time_s'] for row in rows if row['kind'] in ('accepted','sample'))
            for order in rows[0]['settings']['verification']['entropy_quadrature_orders']:
                nodes,_=leggauss(order)
                for row in steps:
                    l,r=row['dense_output']['start_time_s'],row['dense_output']['end_time_s']
                    times.update(float((l+r)/2+(r-l)*node/2) for node in nodes)
        ends=[[row['time_s'] for row in steps] for steps in accepted]
        count=a[0]['cell_count']; rt=a[0]['gas_constant_j_mol_k']*a[0]['settings']['temperature_k']
        maxima={'pore_parent_concentration_mol_m3':0.,'reservoir_pressure_pa':0.}; locations={}
        for at in sorted(times):
            x,y=[np.asarray(rows[1]['values']) if at==0 else polynomial(steps[bisect_left(end,at)],at)
                for rows,steps,end in zip([a,b],accepted,ends,strict=True)]
            parent=y[1:-1].reshape(count,-1).mean(axis=1)
            errors={'pore_parent_concentration_mol_m3':float(np.max(np.abs(x[1:-1]-parent))),
                'reservoir_pressure_pa':rt*float(np.max(np.abs(x[[0,-1]]-y[[0,-1]])))}
            for key,value in errors.items():
                if value>maxima[key]: maxima[key]=value;locations[key]=at
        budgets={'pore_parent_concentration_mol_m3':settings['pore_concentration_budget_mol_m3'],
            'reservoir_pressure_pa':settings['reservoir_pressure_budget_pa']}
        flags={key:value<=budgets[key] for key,value in maxima.items()}
        results.append({'coarse':coarse,'fine':fine,'times_compared':len(times),'maxima':maxima,
            'maximum_at_time_s':locations,'budgets':budgets,'within_budgets':flags})
    result={'settings':settings,'comparisons':results,'all_spatial_budgets_met':all(all(row['within_budgets'].values()) for row in results),
        'scope':'Union of accepted endpoints, 2/4 quadrature nodes, common observations; native BDF polynomials and equal-volume pore averaging. Vessels compared directly. Not a continuous-time bound or experiment.',
        'material_qualified':False,'training_eligible':False}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
