"""Source recomposition, independently expanded gas exchange, local U and entropy."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from calcite_affinity_setup import from_records
from calcite_closed_setup import nitrogen_from_record
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture
from audit_sorptive_gas_cell import polynomial


def audit(rows):
    header=rows[0];config=header['parameters'];budget=config['verification'];initial=rows[1]
    reaction=from_records(header['affinity_parameters'],header['source'],header['reference_facts'])
    nitrogen=nitrogen_from_record(header['nitrogen_source']);r=reaction.gas_constant_j_mol_k;p0=reaction.standard_pressure_pa
    cells=[RigidCalciteMixture(reaction,nitrogen,header['volume_source'],config,cell) for cell in config['cells']]
    s0=sum(s['entropy_j_k'] for s in initial['states']);u0=sum(initial['values'][i] for i in (2,5))
    c0=sum(initial['values'][i] for i in (0,3));n0=sum(initial['values'][i] for i in (1,4))
    total_model=RigidCalciteMixture(reaction,nitrogen,header['volume_source'],config,{'calcium_mol':sum(c.calcium for c in cells),
        'nitrogen_mol':n0,'total_volume_m3':sum(c.volume for c in cells)})
    equilibrium=total_model.inventory_state(c0,n0,u0);seq=equilibrium['entropy_j_k']
    maximum={k:0. for k in ('carbon_ledger_mol','nitrogen_ledger_mol','energy_ledger_j','entropy_ledger_j_k','element_residual_mol',
        'source_energy_j','source_entropy_j_k','source_pressure_pa','source_volume_m3','chemical_stability_j_mol','equilibrium_entropy_excess_j_k')}
    observed=[row for row in rows if row['kind'] in ('initial','accepted','sample')];phases=[{},{}]
    for row in observed:
        v=row['values'];total_s=sum(s['entropy_j_k'] for s in row['states'])
        for column,key,original in ((0,'carbon_ledger_mol',c0),(1,'nitrogen_ledger_mol',n0),(2,'energy_ledger_j',u0)):
            maximum[key]=max(maximum[key],abs(v[column]+v[column+3]-original),
                abs(v[column]-initial['values'][column]+v[column+6]),abs(v[column+3]-initial['values'][column+3]-v[column+6]))
        maximum['entropy_ledger_j_k']=max(maximum['entropy_ledger_j_k'],abs(total_s-s0-v[9]))
        maximum['equilibrium_entropy_excess_j_k']=max(maximum['equilibrium_entropy_excess_j_k'],total_s-seq)
        for i,(cell,state) in enumerate(zip(cells,row['states'],strict=True)):
            t=state['temperature_k'];nc=state['calcite_mol'];nl=state['lime_mol'];ng=state['co2_mol'];nn=state['nitrogen_mol'];carbon=v[3*i]
            counts=phases[i];counts[state['phase']]=counts.get(state['phase'],0)+1
            source_states=[phase.standard(t) for phase in (cell.reactant,cell.product,cell.gas,nitrogen)];amounts=(nc,nl,ng,nn)
            energies=[source_states[0]['enthalpy_j_mol']-p0*cell.vc,source_states[1]['enthalpy_j_mol']-p0*cell.vl,
                source_states[2]['enthalpy_j_mol']-r*t,source_states[3]['enthalpy_j_mol']-r*t]
            uref=math.fsum(n*u for n,u in zip(amounts,energies,strict=True))
            vg=cell.volume-nc*cell.vc-nl*cell.vl;pc=ng*r*t/vg;pn=nn*r*t/vg
            sref=math.fsum(n*s['entropy_j_mol_k'] for n,s in zip(amounts,source_states,strict=True))-r*(ng*math.log(pc/p0)+nn*math.log(pn/p0))
            f=source_states[1]['gibbs_j_mol']+source_states[2]['gibbs_j_mol']-source_states[0]['gibbs_j_mol']-(pc+pn-p0)*cell.dv+r*t*math.log(pc/p0)
            phase=state['phase'];violation=abs(f) if phase=='coexistence' else (max(0.,-f) if phase=='calcite' else max(0.,f))
            errors={'element_residual_mol':max(abs(nc+nl-cell.calcium),abs(nc+ng-carbon),abs(3*nc+nl+2*ng-cell.calcium-2*carbon),abs(nn-v[3*i+1])),
                'source_energy_j':abs(uref-v[3*i+2]),'source_entropy_j_k':abs(sref-state['entropy_j_k']),
                'source_pressure_pa':abs(pc+pn-state['pressure_pa']),'source_volume_m3':abs(vg-state['gas_volume_m3']),'chemical_stability_j_mol':violation}
            for key,value in errors.items():maximum[key]=max(maximum[key],value)
    def independent_flux(values):
        left,right=[cell.inventory_state(*[float(x) for x in values[3*i:3*i+3]]) for i,cell in enumerate(cells)]
        tl,tr=left['temperature_k'],right['temperature_k'];enthalpies=[];forces=[];mu=[];fractions=[]
        for name,phase in (('co2',cells[0].gas),('nitrogen',nitrogen)):
            sl,sr=phase.standard(tl),phase.standard(tr);hl,hr=sl['enthalpy_j_mol'],sr['enthalpy_j_mol'];h=(hl+hr)/2
            entropy_l=sl['entropy_j_mol_k']-r*math.log(left[name+'_partial_pressure_pa']/p0)
            entropy_r=sr['entropy_j_mol_k']-r*math.log(right[name+'_partial_pressure_pa']/p0)
            enthalpies.append(h);forces.append((hl-h)/tl-(hr-h)/tr-entropy_l+entropy_r);mu.append((hl-tl*entropy_l,hr-tr*entropy_r))
            fractions.append((left[name+'_mol']/(left['co2_mol']+left['nitrogen_mol'])+right[name+'_mol']/(right['co2_mol']+right['nitrogen_mol']))/2)
        b=config['face']['bulk_mobility_mol2_k_j_s'];d=config['face']['counter_mobility_mol2_k_j_s'];x,y=fractions
        nc=(b*x*x+d)*forces[0]+(b*x*y-d)*forces[1];nn=(b*x*y-d)*forces[0]+(b*y*y+d)*forces[1]
        flow=config['face']['heat_conductance_w_k']*(tl-tr)+enthalpies[0]*nc+enthalpies[1]*nn
        sl=(-flow+mu[0][0]*nc+mu[1][0]*nn)/tl;sr=(flow-mu[0][1]*nc-mu[1][1]*nn)/tr
        return np.array([nc,nn,flow,sl+sr,sl,sr])
    integrals=[]
    for order in budget['quadrature_orders']:
        nodes,weights=leggauss(order);total=np.zeros(6);previous=initial;max_c=max_n=max_u=max_s=0.;minimum_step=math.inf
        for row in rows:
            if row['kind']!='accepted':continue
            left=row['dense_output']['start_time_s'];right=row['time_s'];integral=np.zeros(6)
            for node,weight in zip(nodes,weights,strict=True):
                t=(left+right)/2+(right-left)*node/2;integral+=independent_flux(polynomial(row['dense_output'],t))*weight*(right-left)/2
            total+=integral
            for i,sign in ((0,-1.),(1,1.)):
                max_c=max(max_c,abs(row['values'][3*i]-previous['values'][3*i]-sign*integral[0]))
                max_n=max(max_n,abs(row['values'][3*i+1]-previous['values'][3*i+1]-sign*integral[1]))
                max_u=max(max_u,abs(row['values'][3*i+2]-previous['values'][3*i+2]-sign*integral[2]))
                max_s=max(max_s,abs(row['states'][i]['entropy_j_k']-initial['states'][i]['entropy_j_k']-total[4+i]))
            minimum_step=min(minimum_step,sum(s['entropy_j_k'] for s in row['states'])-sum(s['entropy_j_k'] for s in previous['states']))
            previous=row
        entropy_residual=abs(sum(s['entropy_j_k'] for s in previous['states'])-s0-total[3])
        integrals.append({'quadrature_order':order,'integrals':total.tolist(),'maximum_local_carbon_residual_mol':max_c,
            'maximum_local_nitrogen_residual_mol':max_n,'maximum_local_energy_residual_j':max_u,
            'maximum_cell_entropy_integral_residual_j_k':max_s,'final_total_entropy_integral_residual_j_k':entropy_residual,
            'minimum_accepted_step_entropy_j_k':minimum_step,
            'within_budgets':bool(max_c<=budget['balance_carbon_mol'] and max_n<=budget['balance_nitrogen_mol'] and max_u<=budget['balance_energy_j'] and max_s<=budget['balance_entropy_j_k'] and
                entropy_residual<=budget['balance_entropy_j_k'] and minimum_step>=-budget['negative_entropy_allowance_j_k'])})
        print(json.dumps({'tolerance':header['tolerance'],'quadrature_order':order,'within_budgets':integrals[-1]['within_budgets']}),flush=True)
    difference=np.abs(np.array(integrals[-1]['integrals'])-np.array(integrals[0]['integrals']))
    lookup={'carbon_ledger_mol':'balance_carbon_mol','nitrogen_ledger_mol':'balance_nitrogen_mol','energy_ledger_j':'balance_energy_j',
        'entropy_ledger_j_k':'balance_entropy_j_k','element_residual_mol':'balance_carbon_mol','source_energy_j':'balance_energy_j',
        'source_entropy_j_k':'balance_entropy_j_k','source_pressure_pa':'source_pressure_absolute_pa','source_volume_m3':'source_volume_absolute_m3',
        'chemical_stability_j_mol':'source_affinity_budget_j_mol','equilibrium_entropy_excess_j_k':'balance_entropy_j_k'}
    flags={key:maximum[key]<=budget[value] for key,value in lookup.items()}
    flags.update(completed=rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',local_integrals=all(v['within_budgets'] for v in integrals),
        quadrature_energy=bool(difference[2]<=budget['quadrature_energy_j']),quadrature_entropy=bool(max(difference[3:])<=budget['quadrature_entropy_j_k']),
        quadrature_carbon=bool(difference[0]<=budget['balance_carbon_mol']),quadrature_nitrogen=bool(difference[1]<=budget['balance_nitrogen_mol']))
    return {'tolerance':header['tolerance'],'observed_states':len(observed),'maximum_residuals':maximum,'phase_observation_counts':phases,
        'integral_reviews':integrals,'quadrature_differences':difference.tolist(),'aggregate_equilibrium_limit':equilibrium,
        'final_entropy_gap_to_equilibrium_j_k':seq-sum(s['entropy_j_k'] for s in rows[-1]['final_states']),
        'within_budgets':flags,'all_requested_numerical_budgets_met':all(flags.values())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    records={name:[json.loads(line) for line in (root/name).read_text().splitlines()] for name in settings['trajectories']}
    reports=[{'trajectory':name,**audit(rows)} for name,rows in records.items()];comparisons=[]
    for case in settings['comparisons']:
        left,right=[records[case[k]] for k in ('left','right')];budget=left[0]['parameters']['verification']
        a,b=[[row for row in rows if row['kind'] in ('initial','sample')] for rows in (left,right)]
        if [row['time_s'] for row in a]!=[row['time_s'] for row in b]:raise ValueError('observation times differ')
        differences={key:max(abs(x['states'][i][key]-y['states'][i][key]) for x,y in zip(a,b,strict=True) for i in range(len(x['states'])))
            for key in ('temperature_k','carbon_mol','nitrogen_mol','calcite_mol','pressure_pa')}
        flags={key:differences[key]<=budget[value] for key,value in {'temperature_k':'time_temperature_k','carbon_mol':'time_carbon_mol',
            'nitrogen_mol':'time_nitrogen_mol','calcite_mol':'time_carbon_mol','pressure_pa':'time_pressure_pa'}.items()}
        comparisons.append({**case,'observations':len(a),'maximum_differences':differences,'within_budgets':all(flags.values())})
    result={'settings':settings,'reports':reports,'comparisons':comparisons,'all_requested_numerical_budgets_met':all(r['all_requested_numerical_budgets_met'] for r in reports) and all(c['within_budgets'] for c in comparisons),
        'material_qualified':False,'training_eligible':False,'scope':'Independent source recomposition and expanded face matrix, shared equilibrium flash for dense quadrature. Virtual transport coefficients, not material calibration.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met']}))


if __name__=='__main__':main()
