"""Independent reactive-face integration, elemental ledgers and entropy study."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from calcite_affinity_setup import from_records
from calcite_closed_setup import nitrogen_from_record
from sludge_sandbox.equilibrium_calcite_inventory import CalciteInventoryCell
from audit_sorptive_gas_cell import polynomial


def audit(rows):
    header=rows[0];config=header['parameters'];budget=config['verification'];initial=rows[1]
    reaction=from_records(header['affinity_parameters'],header['source'],header['reference_facts'])
    nitrogen=nitrogen_from_record(header['nitrogen_source']);r=reaction.gas_constant_j_mol_k;p0=reaction.standard_pressure_pa
    cells=[CalciteInventoryCell(reaction,nitrogen,config,cell) for cell in config['cells']]
    s0=sum(s['entropy_j_k'] for s in initial['states']);h0=sum(initial['values'][i] for i in (1,3));c0=sum(initial['values'][i] for i in (0,2))
    total_model=CalciteInventoryCell(reaction,nitrogen,config,{'calcium_mol':sum(c.calcium for c in cells),'nitrogen_mol':sum(c.carrier for c in cells)})
    equilibrium=total_model.state(c0,h0);seq=equilibrium['entropy_j_k']
    maximum={'carbon_ledger_mol':0.,'enthalpy_ledger_j':0.,'entropy_ledger_j_k':0.,'element_residual_mol':0.,
        'source_enthalpy_j':0.,'source_entropy_j_k':0.,'chemical_stability_j_mol':0.,'equilibrium_entropy_excess_j_k':0.}
    observed=[row for row in rows if row['kind'] in ('initial','accepted','sample')];phases=[{},{}]
    for row in observed:
        v=row['values'];total_s=sum(s['entropy_j_k'] for s in row['states'])
        maximum['carbon_ledger_mol']=max(maximum['carbon_ledger_mol'],abs(v[0]+v[2]-c0),abs(v[0]-initial['values'][0]+v[4]),abs(v[2]-initial['values'][2]-v[4]))
        maximum['enthalpy_ledger_j']=max(maximum['enthalpy_ledger_j'],abs(v[1]+v[3]-h0),abs(v[1]-initial['values'][1]+v[5]),abs(v[3]-initial['values'][3]-v[5]))
        maximum['entropy_ledger_j_k']=max(maximum['entropy_ledger_j_k'],abs(total_s-s0-v[6]))
        maximum['equilibrium_entropy_excess_j_k']=max(maximum['equilibrium_entropy_excess_j_k'],total_s-seq)
        for i,(cell,state) in enumerate(zip(cells,row['states'],strict=True)):
            t=state['temperature_k'];nc=state['calcite_mol'];nl=state['lime_mol'];ng=state['co2_mol'];nn=state['nitrogen_mol'];carbon=v[2*i]
            counts=phases[i];counts[state['phase']]=counts.get(state['phase'],0)+1
            source_states=[phase.standard(t) for phase in (cell.reactant,cell.product,cell.gas,nitrogen)];amounts=(nc,nl,ng,nn)
            href=math.fsum(n*s['enthalpy_j_mol'] for n,s in zip(amounts,source_states,strict=True))
            pc=config['total_pressure_pa']*ng/(ng+nn);pn=config['total_pressure_pa']*nn/(ng+nn)
            sref=math.fsum(n*s['entropy_j_mol_k'] for n,s in zip(amounts,source_states,strict=True))-r*(ng*math.log(pc/p0)+nn*math.log(pn/p0))
            af=reaction.affinity(t,pc)['affinity_j_mol_extent'];phase=state['phase']
            violation=abs(af) if phase=='coexistence' else (max(0.,af) if phase=='calcite' else max(0.,-af))
            errors={'element_residual_mol':max(abs(nc+nl-cell.calcium),abs(nc+ng-carbon),abs(3*nc+nl+2*ng-cell.calcium-2*carbon),abs(nn-cell.carrier)),
                'source_enthalpy_j':abs(href-v[2*i+1]),'source_entropy_j_k':abs(sref-state['entropy_j_k']),'chemical_stability_j_mol':violation}
            for key,value in errors.items():maximum[key]=max(maximum[key],value)
    def independent_flux(values):
        left,right=[cell.state(float(values[2*i]),float(values[2*i+1])) for i,cell in enumerate(cells)]
        tl,tr=left['temperature_k'],right['temperature_k'];hl,hr=[cell.gas.standard(state['temperature_k'])['enthalpy_j_mol'] for cell,state in zip(cells,(left,right),strict=True)]
        sl,sr=[cell.gas.standard(state['temperature_k'])['entropy_j_mol_k']-r*math.log(state['co2_partial_pressure_pa']/p0) for cell,state in zip(cells,(left,right),strict=True)]
        h=(hl+hr)/2;force=(hl-h)/tl-(hr-h)/tr-sl+sr
        n=config['face']['carbon_mobility_mol2_k_j_s']*force;heat=config['face']['heat_conductance_w_k']*(tl-tr);flow=heat+h*n
        mu_l=hl-tl*sl;mu_r=hr-tr*sr
        s_left=(-flow+mu_l*n)/tl;s_right=(flow-mu_r*n)/tr
        production=flow*(1/tr-1/tl)+n*(mu_l/tl-mu_r/tr)
        return np.array([n,flow,production,s_left,s_right])
    integrals=[]
    for order in budget['quadrature_orders']:
        nodes,weights=leggauss(order);total=np.zeros(5);previous=initial;max_carbon=max_h=max_s=0.;minimum_step=math.inf
        for row in rows:
            if row['kind']!='accepted':continue
            left=row['dense_output']['start_time_s'];right=row['time_s'];integral=np.zeros(5)
            for node,weight in zip(nodes,weights,strict=True):
                t=(left+right)/2+(right-left)*node/2;integral+=independent_flux(polynomial(row['dense_output'],t))*weight*(right-left)/2
            total+=integral
            for i,sign in ((0,-1.),(1,1.)):
                max_carbon=max(max_carbon,abs(row['values'][2*i]-previous['values'][2*i]-sign*integral[0]))
                max_h=max(max_h,abs(row['values'][2*i+1]-previous['values'][2*i+1]-sign*integral[1]))
                max_s=max(max_s,abs(row['states'][i]['entropy_j_k']-initial['states'][i]['entropy_j_k']-total[3+i]))
            minimum_step=min(minimum_step,sum(s['entropy_j_k'] for s in row['states'])-sum(s['entropy_j_k'] for s in previous['states']))
            previous=row
        entropy_residual=abs(sum(s['entropy_j_k'] for s in previous['states'])-s0-total[2])
        integrals.append({'quadrature_order':order,'integrals':total.tolist(),'maximum_local_carbon_residual_mol':max_carbon,
            'maximum_local_enthalpy_residual_j':max_h,'maximum_cell_entropy_integral_residual_j_k':max_s,
            'final_total_entropy_integral_residual_j_k':entropy_residual,'minimum_accepted_step_entropy_j_k':minimum_step,
            'within_budgets':bool(max_carbon<=budget['balance_carbon_mol'] and max_h<=budget['balance_energy_j'] and max_s<=budget['balance_entropy_j_k'] and
                entropy_residual<=budget['balance_entropy_j_k'] and minimum_step>=-budget['negative_entropy_allowance_j_k'])})
    difference=np.abs(np.array(integrals[-1]['integrals'])-np.array(integrals[0]['integrals']))
    flags={'completed':rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        'carbon_ledger':maximum['carbon_ledger_mol']<=budget['balance_carbon_mol'],
        'enthalpy_ledger':maximum['enthalpy_ledger_j']<=budget['balance_energy_j'],
        'entropy_ledger':maximum['entropy_ledger_j_k']<=budget['balance_entropy_j_k'],
        'elements':maximum['element_residual_mol']<=budget['balance_carbon_mol'],
        'source_enthalpy':maximum['source_enthalpy_j']<=budget['balance_energy_j'],
        'source_entropy':maximum['source_entropy_j_k']<=budget['balance_entropy_j_k'],
        'chemical_stability':maximum['chemical_stability_j_mol']<=budget['source_affinity_budget_j_mol'],
        'equilibrium_entropy_bound':maximum['equilibrium_entropy_excess_j_k']<=budget['balance_entropy_j_k'],
        'local_integrals':all(v['within_budgets'] for v in integrals),'quadrature_energy':bool(difference[1]<=budget['quadrature_energy_j']),
        'quadrature_entropy':bool(max(difference[2:])<=budget['quadrature_entropy_j_k'])}
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
            for key in ('temperature_k','carbon_mol','calcite_mol','co2_partial_pressure_pa')}
        comparisons.append({**case,'observations':len(a),'maximum_differences':differences,
            'within_budgets':differences['temperature_k']<=budget['time_temperature_k'] and differences['carbon_mol']<=budget['time_carbon_mol']})
    result={'settings':settings,'reports':reports,'comparisons':comparisons,'all_requested_numerical_budgets_met':all(r['all_requested_numerical_budgets_met'] for r in reports) and all(c['within_budgets'] for c in comparisons),
        'material_qualified':False,'training_eligible':False,'scope':'Same source potentials and equilibrium flash, independent face algebra and time integrals. No actual material kinetic or transport validation.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
