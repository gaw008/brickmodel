"""Independent coupled calorimetric clock through elemental potential equations."""
import argparse
import json
from pathlib import Path

from mpmath import mp

from carbon_calcium_setup import build
from carbon_calcium_decimal_reference import caloric_capacity


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());mp.dps=settings['decimal_digits'];budget=settings['budgets']
    with (root/settings['trajectory']).open() as stream:rows=[json.loads(line) for line in stream]
    header=rows[0];model,_=build(root,header['equilibrium_parameters']);inventory=header['inventory'];p=header['settings']
    inputs=[inventory[k] for k in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
    starts={r['segment_index']:r for r in rows if r['kind'] in ('initial','boundary_transition')};events=[r for r in rows if r['kind']=='phase_event']
    boundaries={r['case']['name']:r for r in header['phase_boundary_references']};g=mp.mpf(p['virtual_calorimeter']['heat_conductance_w_k']);records=[]
    for order in settings['quadrature_orders']:
        nodes,weights=mp.gauss_quadrature(order,'legendre')
        for segment,start in starts.items():
            a=mp.mpf(start['state']['temperature_k']);wall=mp.mpf(start['reservoir_temperature_k']);clock=mp.mpf(start['time_s'])
            for event in sorted((row for row in events if row['segment_index']==segment),key=lambda row:row['time_s']):
                target=mp.mpf(boundaries[event['name']]['reference_temperature_k']);total=mp.mpf(0);max_cp=mp.mpf(0);minimum_cp=mp.inf;constraints=True
                for node,weight in zip(nodes,weights,strict=True):
                    t=(a+target)/2+(target-a)*node/2;candidate=model.at_temperature(float(t),*inputs)
                    reference=caloric_capacity(model,t,inventory,candidate,settings);cp=reference['cp'];minimum_cp=min(minimum_cp,cp)
                    max_cp=max(max_cp,abs(mp.mpf(candidate['equilibrium_cp_j_k'])-cp));total+=weight*(target-a)/2*cp/(g*(wall-t))
                    mu=reference['mu'];n=reference['amounts'];constraints=constraints and all(v>=0 for v in n.values())
                    calcium=mu['lime']+mu['CO2']-mu['calcite']
                    if candidate['calcium_phase']=='calcite':constraints=constraints and calcium>=0
                    if candidate['calcium_phase']=='lime':constraints=constraints and calcium<=0
                    if candidate['carbon_phase']=='graphite_exhausted':constraints=constraints and mu['CO']-mu['C']-mu['O2']/2<=0 and mu['CO2']-mu['C']-mu['O2']<=0
                clock+=total;a=target;error=float(abs(clock-mp.mpf(event['time_s'])))
                record={'order':order,'segment':segment,'name':event['name'],'direction':event['direction'],'reference_event_time_s':str(clock),
                    'recorded_event_time_s':event['time_s'],'absolute_time_error_s':error,'maximum_capacity_difference_j_k':float(max_cp),
                    'minimum_reference_capacity_j_k':str(minimum_cp),'within_budgets':{'time':error<=budget['phase_time_s'],
                        'capacity':max_cp<=budget['caloric_capacity_j_k'],'positive_capacity':minimum_cp>0,'phase_constraints':bool(constraints)}}
                records.append(record);print(json.dumps(record),flush=True)
    differences={}
    for event in events:
        selected=[row for row in records if row['segment']==event['segment_index'] and row['name']==event['name']]
        differences[str(event['segment_index'])+'/'+event['name']]=float(abs(mp.mpf(selected[-1]['reference_event_time_s'])-mp.mpf(selected[0]['reference_event_time_s'])))
    result={'settings':settings,'records':records,'quadrature_differences_s':differences,
        'all_requested_decimal_time_budgets_met':all(all(row['within_budgets'].values()) for row in records) and max(differences.values())<=budget['quadrature_time_s'],
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
