"""Measure ledger coloring cost and review the temperature-coordinate entropy row."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate._ivp.common import num_jac
from scipy.optimize._numdiff import group_columns

from carbon_calcium_pressure_setup import build
from carbon_calcium_source_audit import SourceState,independent_exchange
from sludge_sandbox.carbon_calcium_temperature_column import CarbonCalciumTemperatureColumn
from sludge_sandbox.carbon_calcium_temperature_jacobian import production_gradient


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;p=json.loads(args.parameters.read_text());selected=[]
    with (root/p['trajectory']).open() as stream:
        header=json.loads(next(stream))
        for line in stream:
            row=json.loads(line)
            if row['kind']=='sample' and row['time_s'] in p['times_s']:selected.append(row)
    model,_,_=build(root,header['pressure_parameters']);n=header['cell_count'];body=4*n
    column=CarbonCalciumTemperatureColumn(model,header['settings'],header['face_parameters'],header['rigid_parameters']['numerics'],n)
    source=SourceState(header['sources']);pattern=column.numerical_jacobian_sparsity();full_groups=group_columns(pattern,order=p['grouping_seed'])
    body_pattern=pattern[:-1,:-1];local_groups=np.arange(body)%(3*4)
    group_collisions=max(len(local_groups[body_pattern.getrow(i).indices])-len(set(local_groups[body_pattern.getrow(i).indices])) for i in range(body))
    def source_production(values):
        states=column.states(values);refs=[source.reconstruct(state,column.volume,[column.inventories[i]['calcium_atoms_mol'],*values[4*i:4*i+3]]) for i,state in enumerate(states)]
        production=sum(independent_exchange(a,b,column.face_parameters)['dissipation'] for a,b in zip(refs[:-1],refs[1:],strict=True))
        return production,[(s['calcium_phase'],s['carbon_phase']) for s in states]
    reviews=[]
    for row in selected:
        values=np.array(row['integration_values']);rates=column.rates(row['time_s'],values);scale=values[:-1].copy();scale[3::4]=p['temperature_direction_scale_k']
        profiles=[];matrices=[]
        for route in ['full','local_body']:
            evaluations=0
            def vectorized(at,columns):
                nonlocal evaluations
                result=[]
                for v in columns.T:
                    evaluations+=1
                    result.append(column.rates(at,v) if route=='full' else column.rates(at,np.append(v,values[-1]))[:-1])
                return np.array(result).T
            at=time.monotonic()
            matrix,_=num_jac(vectorized,row['time_s'],values if route=='full' else values[:-1],rates if route=='full' else rates[:-1],
                np.array(header['absolute_tolerances']) if route=='full' else np.array(header['absolute_tolerances'][:-1]),None,
                (pattern,full_groups) if route=='full' else (body_pattern,local_groups))
            profiles.append({'route':route,'rhs_evaluations':evaluations,'elapsed_s':time.monotonic()-at})
            matrices.append(matrix[:-1,:-1].toarray() if route=='full' else matrix.toarray())
        difference=(matrices[0]-matrices[1])*scale[None,:]
        errors={'body_jacobian_scaled_inventory_mol_s':float(np.max(np.abs(difference[np.arange(body)%4!=3]))),
                'body_jacobian_scaled_temperature_k_s':float(np.max(np.abs(difference[3::4])))}
        analytic=production_gradient(column,values,row['states']);_,phases=source_production(values);derivatives=[]
        for index in range(body):
            for step in p['central_steps']:
                plus=values.copy();minus=values.copy();plus[index]+=step*scale[index];minus[index]-=step*scale[index]
                fp,pp=source_production(plus);fm,pm=source_production(minus);numeric=(fp-fm)/(2*step)
                derivatives.append({'coordinate':index,'step':step,'scaled_analytic_w_k':float(analytic[index]*scale[index]),'scaled_source_difference_w_k':numeric,
                    'absolute_difference_w_k':abs(float(analytic[index]*scale[index])-numeric),'same_phases':pp==phases and pm==phases})
        errors['production_scaled_derivative_w_k']=max(d['absolute_difference_w_k'] for d in derivatives)
        flags={k:v<=p['budgets'][k] for k,v in errors.items()};flags['same_phases']=all(d['same_phases'] for d in derivatives)
        reviews.append({'time_s':row['time_s'],'profiles':profiles,'errors':errors,'derivatives':derivatives,'within_budgets':flags})
    flags={'all_requested_times':[r['time_s'] for r in reviews]==p['times_s'],'no_body_color_collision':group_collisions==0,
           'point_reviews':all(all(r['within_budgets'].values()) for r in reviews)}
    result={'settings':p,'cell_count':n,'full_color_groups':int(max(full_groups)+1),'local_body_color_groups':int(max(local_groups)+1),
        'body_color_collisions':group_collisions,'reviews':reviews,'within_budgets':flags,'all_requested_budgets_met':all(flags.values()),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:result[k] for k in ['full_color_groups','local_body_color_groups','within_budgets']}))


if __name__=='__main__':main()
