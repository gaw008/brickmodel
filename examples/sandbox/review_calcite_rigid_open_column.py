"""Review spatial assembly, log-coordinate Jacobian and exterior entropy rate."""
import argparse
import json
from pathlib import Path

import numpy as np

from calcite_rigid_setup import build_rigid
from sludge_sandbox.rigid_reactive_open_column import OpenRigidReactiveColumn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent;settings = json.loads(args.parameters.read_text())
    policy = json.loads((root/settings['column_parameters']).read_text())
    config = json.loads((root/policy['model_parameters']).read_text())
    surface = json.loads((root/policy['surface_parameters']).read_text())['surface']
    reaction,nitrogen,_,_,_,_,volume = build_rigid(root,config)
    records = [];budget = settings['budgets']
    for case in settings['cases']:
        time_s = case['time_s'] if 'continuous_boundary_program' in policy else 0.
        n = len(case['temperatures_k']);column = OpenRigidReactiveColumn(reaction,nitrogen,volume,config,policy,surface,n,case.get('cell_widths_m'))
        z = column.initial.copy();base = 3*n
        for i,cell in enumerate(column.cells):
            offset = case['excess_carbon_densities_mol_m3'][i]*cell.volume
            nitrogen_mol = case['nitrogen_densities_mol_m3'][i]*cell.volume
            state = cell.at_carbon_offset(case['temperatures_k'][i],offset,nitrogen_mol)
            z[3*i:3*i+3] = [column.carbon_coordinate(cell,offset),np.log(nitrogen_mol/column.reference_nitrogen),state['internal_energy_j']]
        physical,states,faces,reservoir,contact = column.observe(z,case['segment_index'],time_s)
        f = column.rates(time_s,z,case['segment_index']);matrix = column.jacobian(time_s,z,case['segment_index']).toarray()
        physical_rates = f.copy();physical_rates[1:base:3] *= physical[1:base:3]
        if column.log_carbon:physical_rates[0:base:3] *= physical[0:base:3]
        global_balance = physical_rates[:base].reshape(n,3).sum(axis=0)+f[base:base+3]
        exterior_balance = physical_rates[:base].reshape(n,3).sum(axis=0)+f[base+3:base+6];exterior_balance[2] -= f[base+6]
        entropy_gradient = np.array([[-s['carbon_chemical_potential_j_mol']/s['temperature_k'],
            -s['nitrogen_chemical_potential_j_mol']/s['temperature_k'],1/s['temperature_k']] for s in states])
        entropy_identity = float(np.sum(entropy_gradient*physical_rates[:base].reshape(n,3))+f[base+7]+f[base+8]-f[-1])
        chart = np.ones(len(z));chart[1:base:3] = physical[1:base:3]
        if column.log_carbon:chart[0:base:3] = physical[0:base:3]
        physical_jacobian = chart[:,None]*matrix
        for i in range(n):physical_jacobian[3*i+1,3*i+1] += physical_rates[3*i+1]
        if column.log_carbon:
            for i in range(n):physical_jacobian[3*i,3*i] += physical_rates[3*i]
        balance_jacobian = physical_jacobian[:base].reshape(n,3,len(z)).sum(axis=0)+matrix[base:base+3]
        normalization = np.array([entry for cell in column.cells for entry in [settings['coordinate_normalization']['carbon_density_mol_m3']*cell.volume,
            settings['coordinate_normalization']['log_nitrogen'],settings['coordinate_normalization']['energy_density_j_m3']*cell.volume]])
        perturbation = np.array([entry for cell in column.cells for entry in [case['carbon_difference_density_mol_m3']*cell.volume,
            settings['difference_scales']['log_nitrogen'],settings['difference_scales']['energy_density_j_m3']*cell.volume]])
        if column.log_carbon:
            normalization[0:base:3] /= physical[0:base:3]
            perturbation[0:base:3] /= physical[0:base:3]
        output_scales = np.array(settings['per_cell_rate_scales']*n+settings['ledger_rate_scales'])
        if column.log_carbon and settings.get('carbon_rate_scale_basis')=='physical_inventory':
            output_scales[0:base:3] /= physical[0:base:3]
        derivatives = []
        for step in settings['difference_steps']:
            reference = np.zeros_like(matrix);same_phase = True
            for coordinate in range(base):
                left,right = z.copy(),z.copy();left[coordinate] -= step*perturbation[coordinate];right[coordinate] += step*perturbation[coordinate]
                reference[:,coordinate] = (column.rates(time_s,right,case['segment_index'])-column.rates(time_s,left,case['segment_index']))/(right[coordinate]-left[coordinate])
                for value in (left,right):
                    same_phase &= [s['phase'] for s in column.observe(value,case['segment_index'],time_s)[1]]==[s['phase'] for s in states]
            scaled = np.abs(matrix[:,:base]-reference[:,:base])*normalization[None,:]/output_scales[:,None]
            worst_row,worst_column = np.unravel_index(np.argmax(scaled),scaled.shape)
            error = float(scaled[worst_row,worst_column])
            derivatives.append({'step':step,'scaled_maximum_absolute_difference':error,'all_perturbations_same_phase':bool(same_phase),
                'worst_row':int(worst_row),'worst_column':int(worst_column),
                'analytic_at_worst':float(matrix[worst_row,worst_column]),'central_difference_at_worst':float(reference[worst_row,worst_column]),
                'within_budget':bool(error<=budget['scaled_derivative'] and same_phase)})
        flags = {'inner_species':float(np.max(np.abs(global_balance[:2])))<=budget['species_rate_mol_s'],
            'outer_species':float(np.max(np.abs(exterior_balance[:2])))<=budget['species_rate_mol_s'],
            'inner_energy':abs(global_balance[2])<=budget['energy_rate_w'],'outer_energy':abs(exterior_balance[2])<=budget['energy_rate_w'],
            'entropy_identity':abs(entropy_identity)<=budget['entropy_rate_w_k'],
            'derivatives':all(d['within_budget'] for d in derivatives),
            'conservation_derivative':float(np.max(np.abs(balance_jacobian[:,:base])*normalization))<=budget['conservation_derivative'],
            'passive_ledger_columns':bool(np.all(matrix[:,base:]==0.))}
        record = {'case':case,'cell_volume_m3':column.volume,'cell_volumes_m3':column.volumes.tolist(),'surface_parameters':column.surface_parameters,
            'integration_values':z.tolist(),'phases':[s['phase'] for s in states],
            'inner_C_N_U_rate_residuals':global_balance.tolist(),'outer_C_N_U_rate_residuals':exterior_balance.tolist(),
            'entropy_rate_identity_residual_w_k':entropy_identity,'derivative_reviews':derivatives,
            'maximum_scaled_conservation_derivative':float(np.max(np.abs(balance_jacobian[:,:base])*normalization)),
            'within_budgets':{k:bool(v) for k,v in flags.items()}}
        records.append(record);print(json.dumps({'name':case['name'],'within_budgets':record['within_budgets'],'derivatives':derivatives}),flush=True)
    result = {'settings':settings,'column_parameters':policy,'records':records,
        'all_requested_static_budgets_met':all(all(r['within_budgets'].values()) for r in records),
        'material_qualified':False,'training_eligible':False,
        'scope':'Selected phase-local full-column derivatives, coordinate-chain conservation and thermodynamic rate identity. No completed spatial trajectory or material accuracy.'}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':
    main()
