"""Entropy concavity, reactive transport mobility and closed-column modes."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path

import numpy as np

from carbon_calcium_pressure_setup import build
from sludge_sandbox.carbon_calcium_rigid_column import CarbonCalciumRigidColumn
from sludge_sandbox.carbon_calcium_rigid_exchange import exchange_jacobian
from sludge_sandbox.carbon_calcium_rigid_tangent import rigid_tangent


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());original=json.loads((root/settings['column_parameters']).read_text())
    face_parameters=json.loads((root/original['exchange_parameters']).read_text());rigid=json.loads((root/face_parameters['rigid_parameters']).read_text());pressure=json.loads((root/rigid['pressure_parameters']).read_text())
    model,sources,_=build(root,pressure);n=original['meshes'][settings['mesh']];budget=settings['budgets'];records=[]
    laplacian=np.diag([1.]+[2.]*(n-2)+[1.])+np.diag([-1.]*(n-1),1)+np.diag([-1.]*(n-1),-1)
    laplacian_modes=[2-2*math.cos(k*math.pi/n) for k in range(n)]
    for inventory in pressure['inventories']:
        for temperature in settings['temperature_points_k']:
            p=deepcopy(original);p['initial'].update(temperature_left_k=temperature,temperature_right_k=temperature)
            for atom,density in [('calcium_atoms_mol','calcium_density_mol_m3'),('carbon_atoms_mol','carbon_density_mol_m3'),
                                 ('oxygen_atoms_mol','oxygen_density_mol_m3'),('nitrogen_molecules_mol','nitrogen_density_mol_m3')]:
                p['initial'][density]=inventory[atom]/rigid['virtual_volume_m3']
            column=CarbonCalciumRigidColumn(model,p,face_parameters,rigid['numerics'],n);y=column.initial;states,_=column.observe(y);state=states[0]
            tangent=rigid_tangent(model,state,column.volume,column.inventories[0]['calcium_atoms_mol'],y[0],y[1])
            t=state['temperature_k'];mu=state['chemical_potentials_j_mol'];dm={k:np.array(v) for k,v in tangent['gas_chemical_potential_conserved_derivatives'].items()}
            potentials=np.array([mu['CO']-mu['O2']/2,mu['O2']/2,mu['N2']]);dpotentials=np.array([dm['CO']-dm['O2']/2,dm['O2']/2,dm['N2']])
            dt=np.array(tangent['physical_from_conserved_derivative'][0]);hessian=np.zeros((4,4))
            hessian[:3]=-dpotentials/t+potentials[:,None]*dt[None,:]/t**2;hessian[3]=-dt/t**2
            scales=np.array([y[0],y[1],y[2],tangent['internal_energy_derivatives'][0]*t]);scaled_hessian=hessian*scales[:,None]*scales[None,:]
            face=exchange_jacobian(model,state,state,tangent,tangent,column.face_parameters)
            diffusion=np.array([*[face['inventory'][k][:4] for k in column.face_parameters['transferred_inventory_order']],face['energy'][:4]])
            scaled_diffusion=diffusion*scales[None,:]/scales[:,None]
            mobility=np.zeros((4,4));mobility[3,3]=column.face_parameters['heat_conductance_w_k']*t*t
            for name in column.face_parameters['gas_order']:
                vector=np.array([*column.face_parameters['inventory_per_gas_molecule'][name],model.phases[name].standard(t)['enthalpy_j_mol']])
                mobility+=column.face_parameters['gas_mobilities_mol2_k_j_s'][name]*np.outer(vector,vector)
            mobility_predicted=-mobility@hessian
            dissipation=scaled_hessian@scaled_diffusion
            hessian_eigenvalues=np.linalg.eigvalsh((scaled_hessian+scaled_hessian.T)/2)
            dissipation_eigenvalues=np.linalg.eigvalsh((dissipation+dissipation.T)/2)
            local_eigenvalues=np.linalg.eigvals(scaled_diffusion)
            global_scales=np.tile(scales,n);matrix=column.jacobian(0.,y).toarray()[:4*n,:4*n]
            scaled_matrix=matrix*global_scales[None,:]/global_scales[:,None];expected=-np.kron(laplacian,scaled_diffusion)
            actual_eigenvalues=np.linalg.eigvals(scaled_matrix)
            expected_eigenvalues=np.array([-mode*value for mode in laplacian_modes for value in local_eigenvalues])
            actual_sorted=np.sort(actual_eigenvalues.real);expected_sorted=np.sort(expected_eigenvalues.real)
            null_per_nonuniform_mode=int(state['calcium_phase']=='coexistence')+int(state['carbon_phase']=='graphite_present')
            expected_nullity=4+(n-1)*null_per_nonuniform_mode
            observed_nullity=int(np.count_nonzero(np.abs(actual_eigenvalues)<=budget['zero_eigenvalue_absolute_s_inverse']))
            rates=column.rates(0.,y);body=rates[:-1].reshape(n,4)
            errors={'stationary_inventory_rate_mol_s':float(np.max(np.abs(body[:,:3]))),'stationary_energy_rate_w':float(np.max(np.abs(body[:,3]))),
                'stationary_production_w_k':abs(float(rates[-1])),
                'scaled_hessian_symmetry_j_k':float(np.max(np.abs(scaled_hessian-scaled_hessian.T))),
                'scaled_entropy_maximum_eigenvalue_j_k':float(max(hessian_eigenvalues)),
                'scaled_mobility_identity_s_inverse':float(np.max(np.abs((diffusion-mobility_predicted)*scales[None,:]/scales[:,None]))),
                'scaled_dissipation_symmetry_w_k':float(np.max(np.abs(dissipation-dissipation.T))),
                'scaled_dissipation_maximum_eigenvalue_w_k':float(max(dissipation_eigenvalues)),
                'scaled_spatial_operator_s_inverse':float(np.max(np.abs(scaled_matrix-expected))),
                'spectral_real_difference_s_inverse':float(np.max(np.abs(actual_sorted-expected_sorted))),
                'spectral_imaginary_s_inverse':float(max(np.max(np.abs(actual_eigenvalues.imag)),np.max(np.abs(expected_eigenvalues.imag)))),
                'maximum_growth_rate_s_inverse':float(max(actual_eigenvalues.real))}
            flags={k:v<=budget[k] for k,v in errors.items()};flags['expected_nullity']=observed_nullity==expected_nullity
            records.append({'inventory_name':inventory['name'],'temperature_k':temperature,'phases':[state['calcium_phase'],state['carbon_phase']],
                'scales':scales.tolist(),'scaled_entropy_hessian':scaled_hessian.tolist(),'scaled_local_diffusion_matrix':scaled_diffusion.tolist(),
                'entropy_hessian_eigenvalues':hessian_eigenvalues.tolist(),'entropy_dissipation_eigenvalues':dissipation_eigenvalues.tolist(),
                'actual_eigenvalue_real_parts':actual_sorted.tolist(),'expected_eigenvalue_real_parts':expected_sorted.tolist(),
                'expected_nullity':expected_nullity,'observed_nullity':observed_nullity,'errors':errors,'within_budgets':flags})
            print(json.dumps({'inventory':inventory['name'],'temperature_k':temperature,'nullity':[observed_nullity,expected_nullity],'passed':all(flags.values())}),flush=True)
    result={'settings':settings,'column_parameters':original,'rigid_parameters':rigid,'sources':sources,'records':records,
        'all_requested_budgets_met':all(all(r['within_budgets'].values()) for r in records),'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
