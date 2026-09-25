"""Source and complete inner/outer/radiative balance review of an open rigid cell."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_sorptive_gas_cell import polynomial
from calcite_affinity_setup import from_records
from calcite_closed_setup import nitrogen_from_record
from calcite_rigid_source_review import source_cell_errors, independent_face
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture
from sludge_sandbox.rigid_reactive_open_cell import OpenRigidCalciteCell
from sludge_sandbox.rigid_reactive_offset import OffsetRigidCalciteMixture


def rows(path):
    with path.open() as stream:
        for line in stream:
            yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--trajectory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();settings = json.loads(args.parameters.read_text());root = args.parameters.resolve().parent;path = root/args.trajectory
    stream = rows(path);header = next(stream);initial = next(stream)
    policy = header['settings'];budget = policy['verification'];config = header['model_parameters']
    reaction = from_records(header['affinity_parameters'],header['source'],header['reference_facts'])
    nitrogen = nitrogen_from_record(header['nitrogen_source'])
    coordinates = header['integration_coordinates'] if 'integration_coordinates' in header else {'method':'physical'}
    offset_coordinates = 'carbon_coordinate' in coordinates and coordinates['carbon_coordinate']=='excess_over_calcium'
    cell_class = OffsetRigidCalciteMixture if offset_coordinates else RigidCalciteMixture
    cell = cell_class(reaction,nitrogen,header['volume_source'],config,policy['cell'])
    model = OpenRigidCalciteCell(cell,header['surface_parameters'],policy['boundary_program'])
    initial_values = np.array(initial['values']);s0 = initial['state']['entropy_j_k']
    def physical(values):
        result = np.array(values)
        if offset_coordinates:
            result[0] += cell.calcium
        if coordinates['method']=='log_nitrogen':
            result[1] = coordinates['reference_nitrogen_mol']*np.exp(result[1])
        return result
    def quantities(state,reservoir,contact,segment):
        surface = contact['surface'];wall = policy['boundary_program'][segment]['radiation_temperature_k']
        inner = independent_face(state,surface,cell,model.surface.interior)
        outer = independent_face(surface,reservoir,cell,model.surface.exterior)
        rp = header['surface_parameters']['radiation']
        radiation = header['surface_parameters']['area_m2']*rp['emissivity']*rp['stefan_boltzmann_w_m2_k4']*(wall**4-surface['temperature_k']**4)
        components = [float(inner[3]+inner[4]),float(outer[3]+outer[4]),float(radiation*(1/surface['temperature_k']-1/wall))]
        q = np.concatenate((inner[:3],outer[:3],[radiation,outer[4],-radiation/wall,math.fsum(components)]))
        balance = inner[:3]-outer[:3];balance[2] += radiation
        return q,balance,components
    maximum = {key:0. for key in ('elements_mol','source_energy_j','source_entropy_j_k','source_pressure_pa','source_volume_m3','affinity_j_mol',
        'inner_species_ledger_mol','inner_energy_ledger_j','outer_species_ledger_mol','outer_energy_ledger_j','surface_species_ledger_mol',
        'surface_energy_ledger_j','entropy_ledger_j_k','surface_species_mol_s','surface_energy_w','independent_face_species_mol_s','independent_face_energy_w')}
    minimum_gas = minimum_solid = minimum_face_entropy = math.inf;observations = steps = 0;phase_counts = {}
    for row in rows(path):
        terminal = row
        if row['kind'] not in ('initial','accepted','sample','boundary_transition'):
            continue
        values = np.array(row['values']);state = row['state'];observations += 1;steps += row['kind']=='accepted'
        phase_counts[state['phase']] = phase_counts.get(state['phase'],0)+1
        for key,value in source_cell_errors(cell,state,values[:3]).items():
            maximum[key] = max(maximum[key],float(value))
        inner_residual = values[:3]-initial_values[:3]+values[3:6]
        outer_residual = values[:3]-initial_values[:3]+values[6:9];outer_residual[2] -= values[9]
        surface_residual = values[3:6]-values[6:9];surface_residual[2] += values[9]
        for prefix,residual in (('inner',inner_residual),('outer',outer_residual),('surface',surface_residual)):
            maximum[prefix+'_species_ledger_mol'] = max(maximum[prefix+'_species_ledger_mol'],float(np.max(np.abs(residual[:2]))))
            maximum[prefix+'_energy_ledger_j'] = max(maximum[prefix+'_energy_ledger_j'],float(abs(residual[2])))
        maximum['entropy_ledger_j_k'] = max(maximum['entropy_ledger_j_k'],abs(state['entropy_j_k']-s0+values[10]+values[11]-values[12]))
        q,balance,components = quantities(state,row['reservoir'],row['contact'],row['segment_index'])
        maximum['surface_species_mol_s'] = max(maximum['surface_species_mol_s'],float(np.max(np.abs(balance[:2]))))
        maximum['surface_energy_w'] = max(maximum['surface_energy_w'],float(abs(balance[2])))
        for offset,name in ((0,'interior_face'),(3,'exterior_face')):
            for j,key in enumerate(('carbon_flow_mol_s','nitrogen_flow_mol_s','energy_flow_w')):
                field = 'independent_face_energy_w' if j==2 else 'independent_face_species_mol_s'
                maximum[field] = max(maximum[field],float(abs(q[offset+j]-row['contact'][name][key])))
        minimum_face_entropy = min(minimum_face_entropy,*components)
        minimum_gas = min(minimum_gas,state['co2_mol'],state['nitrogen_mol'])
        minimum_solid = min(minimum_solid,state['calcite_mol'],state['lime_mol'])
    reviews = []
    for order in budget['quadrature_orders']:
        nodes,weights = leggauss(order);total = np.zeros(10);local = np.zeros(3);ledger = np.zeros(10);entropy = 0.;minimum_step = math.inf;previous = initial
        max_surface = np.zeros(3);min_node_entropy = math.inf
        for row in rows(path):
            if row['kind']!='accepted':
                continue
            start = row['dense_output']['start_time_s'];end = row['dense_output']['end_time_s'];integral = np.zeros(10)
            for node,weight in zip(nodes,weights,strict=True):
                at = (start+end)/2+(end-start)*node/2
                integration_values = polynomial(row['dense_output'],at);values = physical(integration_values)
                state,reservoir,contact = model.observe(values,row['segment_index'],integration_values[0] if offset_coordinates else None)
                q,balance,components = quantities(state,reservoir,contact,row['segment_index'])
                integral += q*weight*(end-start)/2
                max_surface = np.maximum(max_surface,np.abs(balance));min_node_entropy = min(min_node_entropy,*components)
            total += integral
            values = np.array(row['values']);before = np.array(previous['values'])
            local = np.maximum(local,np.abs(values[:3]-before[:3]+integral[:3]))
            ledger = np.maximum(ledger,np.abs(values[3:]-total))
            entropy = max(entropy,abs(row['state']['entropy_j_k']-s0+total[7]+total[8]-total[9]))
            minimum_step = min(minimum_step,row['state']['entropy_j_k']-previous['state']['entropy_j_k']+integral[7]+integral[8])
            previous = row
        flags = {'local_species':float(np.max(local[:2]))<=budget['species_balance_mol'],'local_energy':local[2]<=budget['energy_balance_j'],
            'species_integrals':float(np.max(ledger[[0,1,3,4]]))<=budget['species_balance_mol'],
            'energy_integrals':float(np.max(ledger[[2,5,6]]))<=budget['energy_balance_j'],
            'entropy_integrals':float(np.max(ledger[7:]))<=budget['entropy_balance_j_k'],'combined_entropy':entropy<=budget['entropy_balance_j_k'],
            'entropy_step_sign':minimum_step>=-budget['negative_step_entropy_allowance_j_k'],
            'surface_species':float(np.max(max_surface[:2]))<=budget['surface_species_mol_s'],'surface_energy':max_surface[2]<=budget['surface_energy_w'],
            'node_entropy_sign':min_node_entropy>=-settings['negative_face_entropy_allowance_w_k']}
        review = {'quadrature_order':order,'maximum_local_C_N_U_residuals':local.tolist(),'maximum_ledger_integral_residuals':ledger.tolist(),
            'maximum_combined_entropy_residual_j_k':entropy,'minimum_step_total_entropy_j_k':minimum_step,
            'maximum_node_surface_residuals':max_surface.tolist(),'minimum_node_entropy_production_w_k':min_node_entropy,
            'integrated_quantities':total.tolist(),'within_budgets':{k:bool(v) for k,v in flags.items()}}
        reviews.append(review);print(json.dumps({'quadrature_order':order,'within_budgets':review['within_budgets']}),flush=True)
    difference = np.abs(np.array(reviews[-1]['integrated_quantities'])-np.array(reviews[0]['integrated_quantities']))
    ledger_budgets = [budget['species_balance_mol'],budget['species_balance_mol'],budget['energy_balance_j']]*2+[budget['energy_balance_j']]+[budget['entropy_balance_j_k']]*3
    mapping = {'elements_mol':'species_balance_mol','source_energy_j':'source_energy_j','source_entropy_j_k':'source_entropy_j_k','source_pressure_pa':'source_pressure_pa',
        'source_volume_m3':'source_volume_m3','affinity_j_mol':'source_affinity_j_mol','entropy_ledger_j_k':'entropy_balance_j_k',
        'surface_species_mol_s':'surface_species_mol_s','surface_energy_w':'surface_energy_w'}
    for prefix in ('inner','outer','surface'):
        mapping[prefix+'_species_ledger_mol']='species_balance_mol';mapping[prefix+'_energy_ledger_j']='energy_balance_j'
    flags = {k:maximum[k]<=budget[v] for k,v in mapping.items()}
    flags.update({k:maximum[k]<=settings[k] for k in ('independent_face_species_mol_s','independent_face_energy_w')})
    flags.update(completed=terminal['kind']=='summary' and terminal['status']=='completed',positive_gas=minimum_gas>0,nonnegative_solid=minimum_solid>=0,
        nonnegative_face_entropy=minimum_face_entropy>=-settings['negative_face_entropy_allowance_w_k'],
        dense_integrals=all(all(r['within_budgets'].values()) for r in reviews),quadrature_consistency=bool(np.all(difference<=np.array(ledger_budgets))))
    result = {'settings':settings,'trajectory':str(args.trajectory),'accepted_steps':steps,'recorded_states':observations,'phase_counts':phase_counts,
        'maximum_residuals':maximum,'minimum_gas_mol':minimum_gas,'minimum_solid_mol':minimum_solid,'minimum_face_entropy_production_w_k':minimum_face_entropy,
        'integral_reviews':reviews,'quadrature_differences':difference.tolist(),'within_budgets':{k:bool(v) for k,v in flags.items()},
        'all_requested_numerical_budgets_met':all(flags.values()),'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as out:
        json.dump(result,out,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met']}))


if __name__=='__main__':
    main()
