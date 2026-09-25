"""Full closed two-cell source, elemental, energy and entropy trajectory review."""
import argparse
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_carbon_gas_cycle import polynomial
from carbon_calcium_pressure_setup import build
from carbon_calcium_source_audit import SourceState,independent_exchange


def audit(path,root):
    with path.open() as stream:rows=[json.loads(line) for line in stream]
    header,initial=rows[:2];p=header['settings'];budget=p['verification'];cells=p['cells']
    rigid=header['rigid_parameters'];face_policy=header['face_parameters'];inventories=header['inventories']
    model,_,_=build(root,header['pressure_parameters']);source=SourceState(header['sources'])
    u0=np.array(header['initial_internal_energies_j']);s0=np.array([s['entropy_j_k'] for s in initial['states']])
    y0=np.array(initial['values'][:8]).reshape(2,4)
    maxima={k:0. for k in ['element_mol','pressure_pa','volume_m3','reaction_gibbs_j_mol','source_energy_j','source_entropy_j_k',
        'face_species_mol_s','face_energy_w','face_entropy_w_k','global_inventory_mol','global_energy_j','entropy_ledger_j_k','energy_coordinate_j']}
    minima={'gas_mol':float('inf'),'solid_mol':float('inf'),'cv_j_k':float('inf'),'production_w_k':float('inf')}
    counts={'recorded':0,'dense':0};phases={}
    def decode(y):
        return [model.from_internal_energy(float(u0[i]+y[4*i+3]),cell['volume_m3'],inventories[i]['calcium_atoms_mol'],
                    *map(float,y[4*i:4*i+3]),rigid['numerics']) for i,cell in enumerate(cells)]
    def review(states,y,category,recorded_face=None):
        counts[category]+=len(states);refs=[]
        for i,state in enumerate(states):
            ref=source.reconstruct(state,cells[i]['volume_m3'],[inventories[i]['calcium_atoms_mol'],*y[4*i:4*i+3]])
            refs.append(ref)
            for k,v in ref['errors'].items():maxima[k]=max(maxima[k],v)
            minima['gas_mol']=min(minima['gas_mol'],ref['minimum_gas_mol']);minima['solid_mol']=min(minima['solid_mol'],ref['minimum_solid_mol'])
            minima['cv_j_k']=min(minima['cv_j_k'],state['equilibrium_cv_j_k'])
            key=str(i)+':'+state['calcium_phase']+'/'+state['carbon_phase'];phases[key]=phases.get(key,0)+1
            maxima['energy_coordinate_j']=max(maxima['energy_coordinate_j'],abs(ref['internal_energy_j']-u0[i]-y[4*i+3]))
        face=independent_exchange(*refs,face_policy);minima['production_w_k']=min(minima['production_w_k'],face['production'])
        if recorded_face is not None:
            maxima['face_species_mol_s']=max(maxima['face_species_mol_s'],*(abs(recorded_face['gas_flows_mol_s'][k]-v) for k,v in face['gas'].items()),
                *(abs(recorded_face['inventory_flows_mol_s'][k]-v) for k,v in zip(face_policy['transferred_inventory_order'],face['inventory'],strict=True)))
            maxima['face_energy_w']=max(maxima['face_energy_w'],abs(face['energy']-recorded_face['energy_flow_w']))
            maxima['face_entropy_w_k']=max(maxima['face_entropy_w_k'],abs(face['production']-recorded_face['entropy_production_w_k']),
                abs(face['entropy'][0]-recorded_face['left_entropy_rate_w_k']),abs(face['entropy'][1]-recorded_face['right_entropy_rate_w_k']))
        return refs,face
    for row in rows:
        if 'states' not in row:continue
        y=np.array(row['values']);refs,_=review(row['states'],y,'recorded',row['face'])
        change=y[:8].reshape(2,4)-y0;total=change.sum(axis=0)
        maxima['global_inventory_mol']=max(maxima['global_inventory_mol'],float(np.max(np.abs(total[:3]))))
        maxima['global_energy_j']=max(maxima['global_energy_j'],abs(sum(r['internal_energy_j'] for r in refs)-sum(u0)))
        maxima['entropy_ledger_j_k']=max(maxima['entropy_ledger_j_k'],abs(sum(r['entropy_j_k'] for r in refs)-sum(s0)-y[-1]))
    integral_reviews=[];integrals_by_order=[]
    for order in budget['quadrature_orders']:
        nodes,weights=leggauss(order);total=np.zeros(7);previous=initial
        max_local=np.zeros(4);max_cumulative=np.zeros(4);max_s_local=max_s_cumulative=max_production=0.
        minimum_step=float('inf');increments=[]
        for row in rows:
            if row['kind']!='accepted':continue
            dense=row['dense_output'];left,right=dense['start_time_s'],dense['end_time_s'];integral=np.zeros(7)
            for node,weight in zip(nodes,weights,strict=True):
                at=(left+right)/2+(right-left)*node/2;y=polynomial(row,at)
                refs,face=review(decode(y),y,'dense')
                integral+=weight*(right-left)/2*np.array([*face['inventory'],face['energy'],*face['entropy'],face['production']])
            total+=integral;increments.append(integral)
            y=np.array(row['values'][:8]).reshape(2,4);prev=np.array(previous['values'][:8]).reshape(2,4)
            expected=np.array([-integral[:4],integral[:4]]);cumulative=np.array([-total[:4],total[:4]])
            max_local=np.maximum(max_local,np.max(np.abs(y-prev-expected),axis=0))
            max_cumulative=np.maximum(max_cumulative,np.max(np.abs(y-y0-cumulative),axis=0))
            entropy=np.array([s['entropy_j_k'] for s in row['states']]);before_s=np.array([s['entropy_j_k'] for s in previous['states']])
            max_s_local=max(max_s_local,float(np.max(np.abs(entropy-before_s-integral[4:6]))))
            max_s_cumulative=max(max_s_cumulative,float(np.max(np.abs(entropy-s0-total[4:6]))))
            max_production=max(max_production,abs(float(np.sum(entropy-s0))-total[6]),abs(row['values'][-1]-total[6]))
            minimum_step=min(minimum_step,float(np.sum(entropy-before_s)));previous=row
        flags={'local_inventory':max(max_local[:3])<=budget['inventory_integral_mol'],
            'cumulative_inventory':max(max_cumulative[:3])<=budget['inventory_integral_mol'],
            'local_energy':max_local[3]<=budget['energy_j'],'cumulative_energy':max_cumulative[3]<=budget['energy_j'],
            'local_entropy':max_s_local<=budget['entropy_j_k'],'cumulative_entropy':max_s_cumulative<=budget['entropy_j_k'],
            'production_integral':max_production<=budget['entropy_j_k'],'nonnegative_step_entropy':minimum_step>=-budget['nonnegative_entropy_j_k']}
        integral_reviews.append({'order':order,'final_integrals_C_O_N_U_Sleft_Sright_production':total.tolist(),
            'maximum_local_C_O_N_U_residual':max_local.tolist(),'maximum_cumulative_C_O_N_U_residual':max_cumulative.tolist(),
            'maximum_local_entropy_residual_j_k':max_s_local,'maximum_cumulative_entropy_residual_j_k':max_s_cumulative,
            'maximum_production_integral_residual_j_k':max_production,'minimum_step_entropy_change_j_k':minimum_step,
            'within_budgets':{k:bool(v) for k,v in flags.items()}})
        integrals_by_order.append(np.array(increments))
        print(json.dumps({'trajectory':str(path),'quadrature_order':order,'within_budgets':integral_reviews[-1]['within_budgets']}),flush=True)
    delta=integrals_by_order[1]-integrals_by_order[0]
    qlocal=np.max(np.abs(delta),axis=0);qtotal=np.max(np.abs(np.cumsum(delta,axis=0)),axis=0)
    flags={k:maxima[k]<=budget[k] for k in ['element_mol','pressure_pa','volume_m3','reaction_gibbs_j_mol','source_energy_j','source_entropy_j_k','face_species_mol_s','face_energy_w','face_entropy_w_k']}
    flags.update(completed=rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        positive_gas=minima['gas_mol']>0,nonnegative_solids=minima['solid_mol']>=0,positive_cv=minima['cv_j_k']>0,
        nonnegative_production=minima['production_w_k']>=0,global_inventory=maxima['global_inventory_mol']<=budget['element_mol'],
        global_energy=maxima['global_energy_j']<=budget['energy_j'],entropy_ledger=maxima['entropy_ledger_j_k']<=budget['entropy_j_k'],
        energy_coordinate=maxima['energy_coordinate_j']<=budget['source_energy_j'],
        integral_reviews=all(all(r['within_budgets'].values()) for r in integral_reviews),
        quadrature_inventory=max(max(qlocal[:3]),max(qtotal[:3]))<=budget['inventory_integral_mol'],
        quadrature_energy=max(qlocal[3],qtotal[3])<=budget['energy_j'],
        quadrature_entropy=max(max(qlocal[4:]),max(qtotal[4:]))<=budget['entropy_j_k'])
    flags={k:bool(v) for k,v in flags.items()}
    return {'trajectory':str(path),'counts':counts,'maxima':maxima,'minima':minima,'phase_counts':phases,
        'integral_reviews':integral_reviews,'maximum_local_quadrature_differences':qlocal.tolist(),
        'maximum_cumulative_quadrature_differences':qtotal.tolist(),'within_budgets':flags,
        'all_requested_numerical_budgets_met':all(flags.values())},rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());reviews={};rows={}
    for name,path in settings['trajectories'].items():reviews[name],rows[name]=audit(root/path,root)
    ln,rn=settings['time_comparison_pair'];left={r['time_s']:r for r in rows[ln] if r['kind']=='sample'};right={r['time_s']:r for r in rows[rn] if r['kind']=='sample'}
    budget=rows[ln][0]['settings']['verification'];differences={}
    for field in ['temperature_k','pressure_pa']:
        differences[field]=max(abs(a[field]-b[field]) for t in left for a,b in zip(left[t]['states'],right[t]['states'],strict=True))
    differences['species_mol']=max(abs(a['amounts_mol'][k]-b['amounts_mol'][k]) for t in left for a,b in zip(left[t]['states'],right[t]['states'],strict=True) for k in a['amounts_mol'])
    flags={key:value<=budget['time_'+key] for key,value in differences.items()};flags['same_observation_times']=left.keys()==right.keys()
    result={'settings':settings,'trajectory_reviews':reviews,'time_comparison':{'observations':len(left),'maximum_differences':differences,'within_budgets':flags},
        'all_requested_numerical_budgets_met':all(r['all_requested_numerical_budgets_met'] for r in reviews.values()) and all(flags.values()),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],'time_comparison':result['time_comparison']}))


if __name__=='__main__':main()
