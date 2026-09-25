"""Stream column source/face records and integrate every cell's conserved balances."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from calcite_affinity_setup import from_records
from calcite_closed_setup import nitrogen_from_record
from sludge_sandbox.rigid_reactive_column import RigidReactiveColumn
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture
from audit_sorptive_gas_cell import polynomial
from calcite_rigid_source_review import source_cell_errors,independent_face


def rows(path):
    with path.open() as stream:
        for line in stream:yield json.loads(line)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--trajectory',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent;path=root/args.trajectory
    stream=rows(path);header=next(stream);initial=next(stream);config=header['parameters'];budget=config['verification'];n=header['cell_count']
    reaction=from_records(header['affinity_parameters'],header['source'],header['reference_facts']);nitrogen=nitrogen_from_record(header['nitrogen_source'])
    column=RigidReactiveColumn(reaction,nitrogen,header['volume_source'],config,n);cells=column.cells
    s0=np.array([s['entropy_j_k'] for s in initial['states']]);v0=np.array(initial['values'][:3*n]).reshape(n,3);total0=v0.sum(axis=0)
    aggregate=RigidCalciteMixture(reaction,nitrogen,header['volume_source'],config,{'calcium_mol':sum(c.calcium for c in cells),
        'nitrogen_mol':total0[1],'total_volume_m3':sum(c.volume for c in cells)})
    equilibrium=aggregate.inventory_state(*total0.tolist());seq=equilibrium['entropy_j_k']
    maximum={k:0. for k in ('elements_mol','source_energy_j','source_entropy_j_k','source_pressure_pa','source_volume_m3','affinity_j_mol',
        'carbon_ledger_mol','nitrogen_ledger_mol','energy_ledger_j','entropy_ledger_j_k','entropy_excess_j_k','face_species_mol_s','face_energy_w','face_entropy_w_k')}
    minimum_species=minimum_solid=math.inf;observed=steps=0;phase_counts=[{} for _ in cells]
    for row in rows(path):
        final=row
        if row['kind'] not in ('initial','accepted','sample'):continue
        observed+=1;steps+=row['kind']=='accepted';v=np.array(row['values']);inventory=v[:3*n].reshape(n,3)
        ledgers=v[3*n:-1].reshape(n-1,3);face_ledger=np.vstack((np.zeros((1,3)),ledgers,np.zeros((1,3))))
        residual=inventory-v0-face_ledger[:-1]+face_ledger[1:]
        for k,key in enumerate(('carbon_ledger_mol','nitrogen_ledger_mol','energy_ledger_j')):
            maximum[key]=max(maximum[key],float(np.max(np.abs(residual[:,k]))),float(abs(inventory[:,k].sum()-total0[k])))
        entropy=sum(s['entropy_j_k'] for s in row['states']);maximum['entropy_ledger_j_k']=max(maximum['entropy_ledger_j_k'],abs(entropy-s0.sum()-v[-1]))
        maximum['entropy_excess_j_k']=max(maximum['entropy_excess_j_k'],entropy-seq)
        for i,(cell,state) in enumerate(zip(cells,row['states'],strict=True)):
            for k,value in source_cell_errors(cell,state,inventory[i]).items():maximum[k]=max(maximum[k],value)
            phase_counts[i][state['phase']]=phase_counts[i].get(state['phase'],0)+1
            minimum_species=min(minimum_species,state['co2_mol'],state['nitrogen_mol']);minimum_solid=min(minimum_solid,state['calcite_mol'],state['lime_mol'])
        for i,face in enumerate(row['faces']):
            ref=independent_face(row['states'][i],row['states'][i+1],cells[i],column.face_parameters)
            maximum['face_species_mol_s']=max(maximum['face_species_mol_s'],abs(ref[0]-face['carbon_flow_mol_s']),abs(ref[1]-face['nitrogen_flow_mol_s']))
            maximum['face_energy_w']=max(maximum['face_energy_w'],abs(ref[2]-face['energy_flow_w']))
            maximum['face_entropy_w_k']=max(maximum['face_entropy_w_k'],abs(ref[3]+ref[4]-face['entropy_production_w_k']))
    reviews=[]
    for order in budget['quadrature_orders']:
        nodes,weights=leggauss(order);total_faces=np.zeros((n-1,5));previous=initial;maximum_local=np.zeros(3);max_entropy=0.;min_step=math.inf
        for row in rows(path):
            if row['kind']!='accepted':continue
            left=row['dense_output']['start_time_s'];right=row['time_s'];integral=np.zeros((n-1,5))
            for node,weight in zip(nodes,weights,strict=True):
                t=(left+right)/2+(right-left)*node/2;states=column.states(polynomial(row['dense_output'],t))
                integral+=np.array([independent_face(states[i],states[i+1],cells[i],column.face_parameters) for i in range(n-1)])*weight*(right-left)/2
            total_faces+=integral;flux=np.vstack((np.zeros((1,3)),integral[:,:3],np.zeros((1,3))))
            delta=np.array(row['values'][:3*n]).reshape(n,3)-np.array(previous['values'][:3*n]).reshape(n,3)
            maximum_local=np.maximum(maximum_local,np.max(np.abs(delta-flux[:-1]+flux[1:]),axis=0))
            entropy=np.array([s['entropy_j_k'] for s in row['states']]);integrated_s=np.zeros(n)
            integrated_s[:-1]+=total_faces[:,3];integrated_s[1:]+=total_faces[:,4]
            max_entropy=max(max_entropy,float(np.max(np.abs(entropy-s0-integrated_s))))
            min_step=min(min_step,float(entropy.sum()-sum(s['entropy_j_k'] for s in previous['states'])));previous=row
        flags={'carbon':maximum_local[0]<=budget['balance_carbon_mol'],'nitrogen':maximum_local[1]<=budget['balance_nitrogen_mol'],
            'energy':maximum_local[2]<=budget['balance_energy_j'],'entropy':max_entropy<=budget['balance_entropy_j_k'],
            'entropy_sign':min_step>=-budget['negative_entropy_allowance_j_k']}
        reviews.append({'quadrature_order':order,'maximum_local_residuals_carbon_nitrogen_energy':maximum_local.tolist(),
            'maximum_cell_entropy_integral_residual_j_k':max_entropy,'minimum_total_step_entropy_j_k':min_step,
            'face_integrals':total_faces.tolist(),'within_budgets':{k:bool(v) for k,v in flags.items()}})
        print(json.dumps({'quadrature_order':order,'within_budgets':reviews[-1]['within_budgets']}),flush=True)
    difference=np.max(np.abs(np.array(reviews[-1]['face_integrals'])-np.array(reviews[0]['face_integrals'])),axis=0)
    mapping={'elements_mol':'balance_carbon_mol','source_energy_j':'balance_energy_j','source_entropy_j_k':'balance_entropy_j_k',
        'source_pressure_pa':'source_pressure_absolute_pa','source_volume_m3':'source_volume_absolute_m3','affinity_j_mol':'source_affinity_budget_j_mol',
        'carbon_ledger_mol':'balance_carbon_mol','nitrogen_ledger_mol':'balance_nitrogen_mol','energy_ledger_j':'balance_energy_j',
        'entropy_ledger_j_k':'balance_entropy_j_k','entropy_excess_j_k':'balance_entropy_j_k'}
    flags={k:maximum[k]<=budget[v] for k,v in mapping.items()}
    flags.update({k:maximum[k]<=settings[k] for k in ('face_species_mol_s','face_energy_w','face_entropy_w_k')})
    flags.update(completed=final['kind']=='summary' and final['status']=='completed',positive_gas=minimum_species>0.,nonnegative_solid=minimum_solid>=0.,
        local_integrals=all(all(r['within_budgets'].values()) for r in reviews),
        quadrature_consistency=bool(np.all(difference<=np.array([budget['balance_carbon_mol'],budget['balance_nitrogen_mol'],budget['quadrature_energy_j'],budget['quadrature_entropy_j_k'],budget['quadrature_entropy_j_k']]))))
    flags={k:bool(v) for k,v in flags.items()}
    result={'trajectory':str(args.trajectory),'cell_count':n,'tolerance':header['tolerance'],'accepted_steps':steps,'observed_states':observed,
        'settings':settings,'maximum_residuals':maximum,'phase_counts':phase_counts,'integral_reviews':reviews,'quadrature_maximum_differences':difference.tolist(),
        'aggregate_equilibrium_limit':equilibrium,'within_budgets':flags,'all_requested_numerical_budgets_met':all(flags.values()),
        'material_qualified':False,'training_eligible':False,'scope':'Independent source recomposition and face expansion, shared equilibrium state inversion for dense quadrature.'}
    with args.output.open('x') as out:json.dump(result,out,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met']}))


if __name__=='__main__':main()
