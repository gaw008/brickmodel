"""Streaming full source and local conservation review of reactive columns."""
import argparse
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_carbon_gas_cycle import polynomial
from carbon_calcium_pressure_setup import build
from carbon_calcium_source_audit import SourceState,independent_exchange


def records(path):
    with path.open() as stream:
        for line in stream:yield json.loads(line)


def audit(path,root):
    stream=records(path);header=next(stream);initial=next(stream);stream.close()
    n=header['cell_count'];base=4*n;p=header['settings'];budget=p['verification'];volume=header['cell_volume_m3']
    rigid=header['rigid_parameters'];face_policy=header['face_parameters'];inventories=header['inventories']
    model,_,_=build(root,header['pressure_parameters']);source=SourceState(header['sources'])
    u0=np.array(header['initial_internal_energies_j']);s0=np.array([s['entropy_j_k'] for s in initial['states']])
    y0=np.array(initial['values'][:base]).reshape(n,4)
    maxima={k:0. for k in ['element_mol','pressure_pa','volume_m3','reaction_gibbs_j_mol','source_energy_j','source_entropy_j_k',
        'face_species_mol_s','face_energy_w','face_entropy_w_k','global_inventory_mol','global_energy_j','entropy_ledger_j_k','energy_coordinate_j']}
    minima={'gas_mol':float('inf'),'solid_mol':float('inf'),'cv_j_k':float('inf'),'dissipation_w_k':float('inf'),'source_entropy_sum_w_k':float('inf')}
    counts={'recorded':0,'dense':0};phases={};samples={}
    def decode(y):
        return [model.from_internal_energy(float(u0[i]+y[4*i+3]),volume,inventories[i]['calcium_atoms_mol'],
                    *map(float,y[4*i:4*i+3]),rigid['numerics']) for i in range(n)]
    def review(states,y,category,faces=None):
        counts[category]+=n;refs=[]
        for i,state in enumerate(states):
            ref=source.reconstruct(state,volume,[inventories[i]['calcium_atoms_mol'],*y[4*i:4*i+3]]);refs.append(ref)
            for k,v in ref['errors'].items():maxima[k]=max(maxima[k],v)
            minima['gas_mol']=min(minima['gas_mol'],ref['minimum_gas_mol']);minima['solid_mol']=min(minima['solid_mol'],ref['minimum_solid_mol'])
            minima['cv_j_k']=min(minima['cv_j_k'],state['equilibrium_cv_j_k'])
            key=state['calcium_phase']+'/'+state['carbon_phase'];phases[key]=phases.get(key,0)+1
            maxima['energy_coordinate_j']=max(maxima['energy_coordinate_j'],abs(ref['internal_energy_j']-u0[i]-y[4*i+3]))
        rates=np.zeros((n,5));production=0.
        for i in range(n-1):
            face=independent_exchange(refs[i],refs[i+1],face_policy);flow=np.array([*face['inventory'],face['energy']])
            rates[i,:4]-=flow;rates[i+1,:4]+=flow;rates[i,4]+=face['entropy'][0];rates[i+1,4]+=face['entropy'][1]
            production+=face['dissipation'];minima['dissipation_w_k']=min(minima['dissipation_w_k'],face['dissipation'])
            minima['source_entropy_sum_w_k']=min(minima['source_entropy_sum_w_k'],face['production'])
            maxima['face_entropy_w_k']=max(maxima['face_entropy_w_k'],abs(face['production']-face['dissipation']))
            if faces is not None:
                recorded=faces[i]
                maxima['face_species_mol_s']=max(maxima['face_species_mol_s'],*(abs(recorded['gas_flows_mol_s'][k]-v) for k,v in face['gas'].items()),
                    *(abs(recorded['inventory_flows_mol_s'][k]-v) for k,v in zip(face_policy['transferred_inventory_order'],face['inventory'],strict=True)))
                maxima['face_energy_w']=max(maxima['face_energy_w'],abs(face['energy']-recorded['energy_flow_w']))
                maxima['face_entropy_w_k']=max(maxima['face_entropy_w_k'],abs(face['dissipation']-recorded['entropy_production_w_k']),
                    abs(face['entropy'][0]-recorded['left_entropy_rate_w_k']),abs(face['entropy'][1]-recorded['right_entropy_rate_w_k']))
        return refs,np.concatenate((rates.ravel(),[production]))
    for row in records(path):
        terminal=row
        if 'states' not in row:continue
        y=np.array(row['values']);refs,_=review(row['states'],y,'recorded',row['faces'])
        total=(y[:base].reshape(n,4)-y0).sum(axis=0)
        maxima['global_inventory_mol']=max(maxima['global_inventory_mol'],float(np.max(np.abs(total[:3]))))
        maxima['global_energy_j']=max(maxima['global_energy_j'],abs(sum(r['internal_energy_j'] for r in refs)-sum(u0)))
        maxima['entropy_ledger_j_k']=max(maxima['entropy_ledger_j_k'],abs(sum(r['entropy_j_k'] for r in refs)-sum(s0)-y[-1]))
        if row['kind']=='sample':samples[row['time_s']]=[{k:s[k] for k in ['temperature_k','pressure_pa','amounts_mol']} for s in row['states']]
    integral_reviews=[];integrals_by_order=[]
    for order in budget['quadrature_orders']:
        nodes,weights=leggauss(order);total=np.zeros(5*n+1);previous=initial
        max_local=np.zeros(4);max_cumulative=np.zeros(4);max_s_local=max_s_cumulative=max_production=0.;minimum_step=float('inf');increments=[]
        for row in records(path):
            if row['kind']!='accepted':continue
            dense=row['dense_output'];left,right=dense['start_time_s'],dense['end_time_s'];integral=np.zeros(5*n+1)
            for node,weight in zip(nodes,weights,strict=True):
                at=(left+right)/2+(right-left)*node/2;y=polynomial(row,at)
                _,rates=review(decode(y),y,'dense');integral+=weight*(right-left)/2*rates
            total+=integral;increments.append(integral);local=integral[:-1].reshape(n,5);cumulative=total[:-1].reshape(n,5)
            y=np.array(row['values'][:base]).reshape(n,4);before=np.array(previous['values'][:base]).reshape(n,4)
            max_local=np.maximum(max_local,np.max(np.abs(y-before-local[:,:4]),axis=0))
            max_cumulative=np.maximum(max_cumulative,np.max(np.abs(y-y0-cumulative[:,:4]),axis=0))
            entropy=np.array([s['entropy_j_k'] for s in row['states']]);before_s=np.array([s['entropy_j_k'] for s in previous['states']])
            max_s_local=max(max_s_local,float(np.max(np.abs(entropy-before_s-local[:,4]))))
            max_s_cumulative=max(max_s_cumulative,float(np.max(np.abs(entropy-s0-cumulative[:,4]))))
            max_production=max(max_production,abs(float(np.sum(entropy-s0))-total[-1]),abs(row['values'][-1]-total[-1]))
            minimum_step=min(minimum_step,float(np.sum(entropy-before_s)));previous=row
        flags={'local_inventory':max(max_local[:3])<=budget['inventory_integral_mol'],'cumulative_inventory':max(max_cumulative[:3])<=budget['inventory_integral_mol'],
            'local_energy':max_local[3]<=budget['energy_j'],'cumulative_energy':max_cumulative[3]<=budget['energy_j'],
            'local_entropy':max_s_local<=budget['entropy_j_k'],'cumulative_entropy':max_s_cumulative<=budget['entropy_j_k'],
            'production_integral':max_production<=budget['entropy_j_k'],'nonnegative_step_entropy':minimum_step>=-budget['nonnegative_entropy_j_k']}
        integral_reviews.append({'order':order,'final_local_integrals_C_O_N_U_S':total[:-1].reshape(n,5).tolist(),'final_production_j_k':float(total[-1]),
            'maximum_local_C_O_N_U_residual':max_local.tolist(),'maximum_cumulative_C_O_N_U_residual':max_cumulative.tolist(),
            'maximum_local_entropy_residual_j_k':max_s_local,'maximum_cumulative_entropy_residual_j_k':max_s_cumulative,
            'maximum_production_integral_residual_j_k':max_production,'minimum_step_entropy_change_j_k':minimum_step,'within_budgets':{k:bool(v) for k,v in flags.items()}})
        integrals_by_order.append(np.array(increments));print(json.dumps({'trajectory':str(path),'order':order,'flags':integral_reviews[-1]['within_budgets']}),flush=True)
    delta=integrals_by_order[1]-integrals_by_order[0];qlocal=np.max(np.abs(delta),axis=0);qtotal=np.max(np.abs(np.cumsum(delta,axis=0)),axis=0)
    qbody=np.maximum(qlocal[:-1],qtotal[:-1]).reshape(n,5);qmax=np.max(qbody,axis=0)
    flags={k:maxima[k]<=budget[k] for k in ['element_mol','pressure_pa','volume_m3','reaction_gibbs_j_mol','source_energy_j','source_entropy_j_k','face_species_mol_s','face_energy_w','face_entropy_w_k']}
    flags.update(completed=terminal['kind']=='summary' and terminal['status']=='completed',positive_gas=minima['gas_mol']>0,nonnegative_solids=minima['solid_mol']>=0,
        positive_cv=minima['cv_j_k']>0,nonnegative_dissipation=minima['dissipation_w_k']>=0,global_inventory=maxima['global_inventory_mol']<=budget['element_mol'],
        global_energy=maxima['global_energy_j']<=budget['energy_j'],entropy_ledger=maxima['entropy_ledger_j_k']<=budget['entropy_j_k'],
        energy_coordinate=maxima['energy_coordinate_j']<=budget['source_energy_j'],integral_reviews=all(all(r['within_budgets'].values()) for r in integral_reviews),
        quadrature_inventory=max(qmax[:3])<=budget['inventory_integral_mol'],quadrature_energy=qmax[3]<=budget['energy_j'],
        quadrature_entropy=max(qmax[4],qlocal[-1],qtotal[-1])<=budget['entropy_j_k'])
    flags={k:bool(v) for k,v in flags.items()}
    return {'trajectory':str(path),'cell_count':n,'counts':counts,'maxima':maxima,'minima':minima,'phase_counts':phases,'integral_reviews':integral_reviews,
        'maximum_quadrature_differences_C_O_N_U_S':qmax.tolist(),'maximum_production_quadrature_difference_j_k':float(max(qlocal[-1],qtotal[-1])),
        'within_budgets':flags,'all_requested_numerical_budgets_met':all(flags.values())},samples,header


def compare(left,right,budget):
    differences={field:max(abs(a[field]-b[field]) for t in left for a,b in zip(left[t],right[t],strict=True)) for field in ['temperature_k','pressure_pa']}
    differences['species_mol']=max(abs(a['amounts_mol'][k]-b['amounts_mol'][k]) for t in left for a,b in zip(left[t],right[t],strict=True) for k in a['amounts_mol'])
    flags={k:v<=budget['time_'+k] for k,v in differences.items()};flags['same_observation_times']=left.keys()==right.keys()
    return {'observations':len(left),'maximum_differences':differences,'within_budgets':flags,'all_requested_budgets_met':all(flags.values())}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());reviews={};samples={};headers={}
    for name,path in settings['trajectories'].items():reviews[name],samples[name],headers[name]=audit(root/path,root)
    left,right=settings['time_comparison_pair'];budget=headers[left]['settings']['verification'];comparisons={'time':compare(samples[left],samples[right],budget)}
    if 'reference_pair_trajectory' in settings:
        reference={r['time_s']:r['states'] for r in records(root/settings['reference_pair_trajectory']) if r['kind']=='sample'}
        comparisons['original_pair']=compare(reference,samples[right],budget)
    result={'settings':settings,'trajectory_reviews':reviews,'comparisons':comparisons,
        'all_requested_numerical_budgets_met':all(r['all_requested_numerical_budgets_met'] for r in reviews.values()) and all(r['all_requested_budgets_met'] for r in comparisons.values()),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],'comparisons':comparisons}))


if __name__=='__main__':main()
