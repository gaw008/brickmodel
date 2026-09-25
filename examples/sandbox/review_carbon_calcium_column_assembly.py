"""Conserved initial geometry and linearized finite-volume exchange assembly."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from carbon_calcium_pressure_setup import build
from sludge_sandbox.carbon_calcium_rigid_column import CarbonCalciumRigidColumn
from sludge_sandbox.carbon_calcium_rigid_tangent import rigid_tangent


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());p=json.loads((root/settings['column_parameters']).read_text())
    face=json.loads((root/p['exchange_parameters']).read_text());rigid=json.loads((root/face['rigid_parameters']).read_text());pressure=json.loads((root/rigid['pressure_parameters']).read_text())
    model,sources,_=build(root,pressure);budget=settings['budgets'];records=[];totals=[]
    with (root/settings['reference_two_cell_trajectory']).open() as stream:
        header=json.loads(next(stream));reference=json.loads(next(stream))
    for mesh in settings['meshes']:
        n=p['meshes'][mesh];column=CarbonCalciumRigidColumn(model,p,face,rigid['numerics'],n)
        y=column.initial;states,faces=column.observe(y);rates=column.rates(0.,y);jacobian=column.jacobian(0.,y)
        total=np.array(y[:4*n]).reshape(n,4).sum(axis=0);total[3]=sum(column.initial_energies);totals.append(total)
        sums=rates[:4*n].reshape(n,4).sum(axis=0)
        matrix=jacobian.toarray();matrix_sums=np.array([np.sum(matrix[index:4*n:4],axis=0) for index in range(4)])
        direction=np.zeros_like(y);recipe=settings['direction']
        for i,state in enumerate(states):
            tangent=rigid_tangent(model,state,column.volume,column.inventories[i]['calcium_atoms_mol'],y[4*i],y[4*i+1])
            wave=math.sin(recipe['spatial_wave_number']*math.pi*column.centers[i]/p['geometry']['length_m'])
            physical=np.array([recipe['temperature_amplitude_k']*wave,
                *[amplitude*y[4*i+k]*wave for k,amplitude in enumerate(recipe['inventory_relative_amplitudes_C_O_N'])]])
            direction[4*i:4*i+3]=physical[1:];direction[4*i+3]=np.array(tangent['internal_energy_derivatives'])@physical
        analytic=jacobian@direction;reviews=[]
        for step in settings['difference_steps']:
            low_y,high_y=y-step*direction,y+step*direction;low,high=column.states(low_y),column.states(high_y)
            finite=(column.rates(0.,high_y)-column.rates(0.,low_y))/(2*step)
            error=(analytic-finite)[:4*n].reshape(n,4)
            errors={'inventory_rate_mol_s':float(np.max(np.abs(error[:,:3]))),'energy_rate_w':float(np.max(np.abs(error[:,3]))),
                    'entropy_rate_w_k':abs(float(analytic[-1]-finite[-1]))}
            flags={k:v<=budget[k] for k,v in errors.items()};flags['same_phase']=all((a['calcium_phase'],a['carbon_phase'])==(s['calcium_phase'],s['carbon_phase'])==(b['calcium_phase'],b['carbon_phase']) for a,s,b in zip(low,states,high,strict=True))
            reviews.append({'difference_step':step,'errors':errors,'within_budgets':flags})
        flags={'inventory_rate_conservation':max(abs(sums[:3]))<=budget['inventory_rate_mol_s'],
            'energy_rate_conservation':abs(sums[3])<=budget['energy_rate_w'],
            'jacobian_conservation':float(np.max(np.abs(matrix_sums)))<=budget['jacobian_conservation_absolute'],
            'nonnegative_face_entropy':all(f['entropy_production_w_k']>=0 for f in faces),
            'directional_derivatives':all(all(r['within_budgets'].values()) for r in reviews)}
        records.append({'mesh':mesh,'cells':n,'cell_volume_m3':column.volume,'initial_totals_C_O_N_U':total.tolist(),
            'global_rate_residuals':sums.tolist(),'maximum_jacobian_conservation_residual':float(np.max(np.abs(matrix_sums))),
            'direction':direction.tolist(),'difference_reviews':reviews,'within_budgets':{k:bool(v) for k,v in flags.items()}})
        if n==len(reference['states']):
            differences={k:max(abs(s[k]-r[k]) for s,r in zip(states,reference['states'],strict=True)) for k in ['temperature_k','pressure_pa']}
            differences['species_mol']=max(abs(s['amounts_mol'][k]-r['amounts_mol'][k]) for s,r in zip(states,reference['states'],strict=True) for k in s['amounts_mol'])
            mapping={'maximum_differences':differences,'face_coefficients_match':column.face_parameters['heat_conductance_w_k']==header['face_parameters']['heat_conductance_w_k'] and column.face_parameters['gas_mobilities_mol2_k_j_s']==header['face_parameters']['gas_mobilities_mol2_k_j_s'],
                'within_budgets':all(v<=budget['reference_'+k] for k,v in differences.items())}
    difference=np.max(np.abs(np.array(totals)-totals[0]),axis=0)
    flags={'assembly':all(all(r['within_budgets'].values()) for r in records),'initial_inventory_totals':max(difference[:3])<=budget['inventory_total_mol'],
        'initial_energy_total':difference[3]<=budget['energy_total_j'],'two_cell_mapping':mapping['within_budgets'] and mapping['face_coefficients_match']}
    result={'settings':settings,'column_parameters':p,'sources':sources,'records':records,'two_cell_mapping':mapping,
        'maximum_initial_total_differences':difference.tolist(),'within_budgets':{k:bool(v) for k,v in flags.items()},
        'all_requested_budgets_met':bool(all(flags.values())),'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(result['within_budgets']))


if __name__=='__main__':main()
