"""Full source, local C/N/U/S and exterior entropy review of an open column."""
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
from sludge_sandbox.rigid_reactive_open_column import OpenRigidReactiveColumn


def rows(path):
    with path.open() as stream:
        for line in stream:
            yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--trajectory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();settings = json.loads(args.parameters.read_text());root = args.parameters.resolve().parent
    path = root/args.trajectory;stream = rows(path);header = next(stream);initial = next(stream)
    policy = header['settings'];budget = policy['verification'];n = header['cell_count'];base = 3*n
    reaction = from_records(header['affinity_parameters'],header['source'],header['reference_facts'])
    nitrogen = nitrogen_from_record(header['nitrogen_source'])
    model = OpenRigidReactiveColumn(reaction,nitrogen,header['volume_source'],header['model_parameters'],policy,header['surface_parameters'],n,header.get('cell_widths_m'))
    v0 = np.array(initial['values'][:base]).reshape(n,3);s0 = np.array([s['entropy_j_k'] for s in initial['states']])
    def quantities(states,faces,reservoir,contact,segment):
        local = np.zeros((n,3));entropy = np.zeros(n);productions = [];face_species = face_energy = 0.
        for i,face in enumerate(faces):
            q = independent_face(states[i],states[i+1],model.cells[i],model.internal_face_parameters[i])
            local[i] -= q[:3];local[i+1] += q[:3];entropy[i] += q[3];entropy[i+1] += q[4]
            productions.append(float(q[3]+q[4]))
            face_species = max(face_species,abs(q[0]-face['carbon_flow_mol_s']),abs(q[1]-face['nitrogen_flow_mol_s']))
            face_energy = max(face_energy,abs(q[2]-face['energy_flow_w']))
        surface = contact['surface'];wall = policy['boundary_program'][segment]['radiation_temperature_k']
        inner = independent_face(states[-1],surface,model.cells[-1],model.boundary.surface.interior)
        outer = independent_face(surface,reservoir,model.cells[-1],model.boundary.surface.exterior)
        radiation = model.surface_parameters['area_m2']*model.surface_parameters['radiation']['emissivity']*model.surface_parameters['radiation']['stefan_boltzmann_w_m2_k4']*(wall**4-surface['temperature_k']**4)
        local[-1] -= inner[:3];entropy[-1] += inner[3]
        productions.extend([float(inner[3]+inner[4]),float(outer[3]+outer[4]),float(radiation*(1/surface['temperature_k']-1/wall))])
        q = np.concatenate((inner[:3],outer[:3],[radiation,outer[4],-radiation/wall,math.fsum(productions)]))
        balance = inner[:3]-outer[:3];balance[2] += radiation
        for independent,recorded in [(inner,contact['interior_face']),(outer,contact['exterior_face'])]:
            face_species = max(face_species,abs(independent[0]-recorded['carbon_flow_mol_s']),abs(independent[1]-recorded['nitrogen_flow_mol_s']))
            face_energy = max(face_energy,abs(independent[2]-recorded['energy_flow_w']))
        return local,entropy,q,balance,min(productions),float(face_species),float(face_energy)
    maximum = {k:0. for k in ['elements_mol','source_energy_j','source_entropy_j_k','source_pressure_pa','source_volume_m3','affinity_j_mol',
        'inner_species_ledger_mol','inner_energy_ledger_j','outer_species_ledger_mol','outer_energy_ledger_j',
        'surface_species_ledger_mol','surface_energy_ledger_j','entropy_ledger_j_k','surface_species_mol_s','surface_energy_w',
        'independent_face_species_mol_s','independent_face_energy_w']}
    minimum_gas = minimum_solid = minimum_face_entropy = math.inf;observed = steps = 0;phase_counts = {}
    for row in rows(path):
        terminal = row
        if row['kind'] not in ('initial','accepted','sample','boundary_transition'):
            continue
        observed += 1;steps += row['kind']=='accepted';values = np.array(row['values']);inventory = values[:base].reshape(n,3);ledger = values[base:]
        for i,state in enumerate(row['states']):
            for key,value in source_cell_errors(model.cells[i],state,inventory[i]).items():maximum[key] = max(maximum[key],float(value))
            phase_counts[state['phase']] = phase_counts.get(state['phase'],0)+1
            minimum_gas = min(minimum_gas,state['co2_mol'],state['nitrogen_mol']);minimum_solid = min(minimum_solid,state['calcite_mol'],state['lime_mol'])
        change = inventory.sum(axis=0)-v0.sum(axis=0)
        inner = change+ledger[:3];outer = change+ledger[3:6];outer[2] -= ledger[6]
        surface = ledger[:3]-ledger[3:6];surface[2] += ledger[6]
        for prefix,residual in [('inner',inner),('outer',outer),('surface',surface)]:
            maximum[prefix+'_species_ledger_mol'] = max(maximum[prefix+'_species_ledger_mol'],float(np.max(np.abs(residual[:2]))))
            maximum[prefix+'_energy_ledger_j'] = max(maximum[prefix+'_energy_ledger_j'],float(abs(residual[2])))
        maximum['entropy_ledger_j_k'] = max(maximum['entropy_ledger_j_k'],abs(sum(s['entropy_j_k'] for s in row['states'])-s0.sum()+ledger[7]+ledger[8]-ledger[9]))
        _,_,_,balance,production,fn,fe = quantities(row['states'],row['faces'],row['reservoir'],row['contact'],row['segment_index'])
        maximum['surface_species_mol_s'] = max(maximum['surface_species_mol_s'],float(np.max(np.abs(balance[:2]))))
        maximum['surface_energy_w'] = max(maximum['surface_energy_w'],float(abs(balance[2])))
        maximum['independent_face_species_mol_s'] = max(maximum['independent_face_species_mol_s'],fn)
        maximum['independent_face_energy_w'] = max(maximum['independent_face_energy_w'],fe)
        minimum_face_entropy = min(minimum_face_entropy,production)
    reviews = []
    for order in budget['quadrature_orders']:
        nodes,weights = leggauss(order);total = np.zeros(10);total_local = np.zeros((n,3));total_s = np.zeros(n)
        max_local = np.zeros(3);max_cumulative = np.zeros(3);max_ledger = np.zeros(10);max_s = combined_s = 0.
        min_step = min_node = math.inf;max_surface = np.zeros(3);previous = initial
        for row in rows(path):
            if row['kind']!='accepted':continue
            dense = row['dense_output'];left,right = dense['start_time_s'],dense['end_time_s']
            interval = np.zeros((n,3));interval_s = np.zeros(n);integral = np.zeros(10)
            for node,weight in zip(nodes,weights,strict=True):
                at = (left+right)/2+(right-left)*node/2;scale = weight*(right-left)/2
                _,states,faces,reservoir,contact = model.observe(polynomial(dense,at),row['segment_index'])
                local,entropy,q,balance,production,_,_ = quantities(states,faces,reservoir,contact,row['segment_index'])
                interval += scale*local;interval_s += scale*entropy;integral += scale*q
                min_node = min(min_node,production);max_surface = np.maximum(max_surface,np.abs(balance))
            total += integral;total_local += interval;total_s += interval_s
            values = np.array(row['values']);inventory = values[:base].reshape(n,3);before = np.array(previous['values'][:base]).reshape(n,3)
            max_local = np.maximum(max_local,np.max(np.abs(inventory-before-interval),axis=0))
            max_cumulative = np.maximum(max_cumulative,np.max(np.abs(inventory-v0-total_local),axis=0))
            max_ledger = np.maximum(max_ledger,np.abs(values[base:]-total))
            entropy = np.array([s['entropy_j_k'] for s in row['states']])
            max_s = max(max_s,float(np.max(np.abs(entropy-s0-total_s))))
            combined_s = max(combined_s,abs(entropy.sum()-s0.sum()+total[7]+total[8]-total[9]))
            min_step = min(min_step,float(entropy.sum()-sum(s['entropy_j_k'] for s in previous['states'])+integral[7]+integral[8]))
            previous = row
        flags = {'local_species':max(max_local[:2])<=budget['species_balance_mol'],'local_energy':max_local[2]<=budget['energy_balance_j'],
            'cumulative_species':max(max_cumulative[:2])<=budget['species_balance_mol'],'cumulative_energy':max_cumulative[2]<=budget['energy_balance_j'],
            'species_integrals':max(max_ledger[[0,1,3,4]])<=budget['species_balance_mol'],
            'energy_integrals':max(max_ledger[[2,5,6]])<=budget['energy_balance_j'],
            'entropy_integrals':max(max_ledger[7:])<=budget['entropy_balance_j_k'],'local_entropy':max_s<=budget['entropy_balance_j_k'],
            'combined_entropy':combined_s<=budget['entropy_balance_j_k'],'entropy_step_sign':min_step>=-budget['negative_step_entropy_allowance_j_k'],
            'surface_species':max(max_surface[:2])<=budget['surface_species_mol_s'],'surface_energy':max_surface[2]<=budget['surface_energy_w'],
            'node_entropy_sign':min_node>=-settings['negative_face_entropy_allowance_w_k']}
        review = {'quadrature_order':order,'maximum_local_C_N_U_residuals':max_local.tolist(),
            'maximum_cumulative_cell_C_N_U_residuals':max_cumulative.tolist(),'maximum_ledger_integral_residuals':max_ledger.tolist(),
            'maximum_local_entropy_residual_j_k':max_s,'maximum_combined_entropy_residual_j_k':combined_s,
            'minimum_step_total_entropy_j_k':min_step,'minimum_node_entropy_production_w_k':min_node,
            'maximum_node_surface_residuals':max_surface.tolist(),'integrated_exterior_quantities':total.tolist(),
            'integrated_cell_C_N_U':total_local.tolist(),'integrated_cell_entropy_j_k':total_s.tolist(),
            'within_budgets':{k:bool(v) for k,v in flags.items()}}
        reviews.append(review);print(json.dumps({'quadrature_order':order,'within_budgets':review['within_budgets']}),flush=True)
    difference = np.abs(np.array(reviews[-1]['integrated_exterior_quantities'])-np.array(reviews[0]['integrated_exterior_quantities']))
    cell_difference = np.max(np.abs(np.array(reviews[-1]['integrated_cell_C_N_U'])-np.array(reviews[0]['integrated_cell_C_N_U'])),axis=0)
    entropy_difference = float(np.max(np.abs(np.array(reviews[-1]['integrated_cell_entropy_j_k'])-np.array(reviews[0]['integrated_cell_entropy_j_k']))))
    ledger_budgets = [budget['species_balance_mol'],budget['species_balance_mol'],budget['energy_balance_j']]*2+[budget['energy_balance_j']]+[budget['entropy_balance_j_k']]*3
    mapping = {'elements_mol':'species_balance_mol','source_energy_j':'source_energy_j','source_entropy_j_k':'source_entropy_j_k','source_pressure_pa':'source_pressure_pa',
        'source_volume_m3':'source_volume_m3','affinity_j_mol':'source_affinity_j_mol','entropy_ledger_j_k':'entropy_balance_j_k',
        'surface_species_mol_s':'surface_species_mol_s','surface_energy_w':'surface_energy_w'}
    for prefix in ('inner','outer','surface'):
        mapping[prefix+'_species_ledger_mol'] = 'species_balance_mol';mapping[prefix+'_energy_ledger_j'] = 'energy_balance_j'
    flags = {k:maximum[k]<=budget[v] for k,v in mapping.items()}
    flags.update({k:maximum[k]<=settings[k] for k in ('independent_face_species_mol_s','independent_face_energy_w')})
    flags.update(completed=terminal['kind']=='summary' and terminal['status']=='completed',positive_gas=minimum_gas>0,nonnegative_solid=minimum_solid>=0,
        nonnegative_face_entropy=minimum_face_entropy>=-settings['negative_face_entropy_allowance_w_k'],dense_integrals=all(all(r['within_budgets'].values()) for r in reviews),
        exterior_quadrature=bool(np.all(difference<=np.array(ledger_budgets))),
        local_quadrature=bool(np.all(cell_difference<=np.array(ledger_budgets[:3]))) and entropy_difference<=budget['entropy_balance_j_k'])
    result = {'settings':settings,'trajectory':str(args.trajectory),'cell_count':n,'accepted_steps':steps,'recorded_states':observed*n,
        'phase_counts':phase_counts,'maximum_residuals':maximum,'minimum_gas_mol':minimum_gas,'minimum_solid_mol':minimum_solid,
        'minimum_face_entropy_production_w_k':minimum_face_entropy,'integral_reviews':reviews,
        'exterior_quadrature_differences':difference.tolist(),'cell_C_N_U_quadrature_differences':cell_difference.tolist(),
        'cell_entropy_quadrature_difference_j_k':entropy_difference,'within_budgets':{k:bool(v) for k,v in flags.items()},
        'all_requested_numerical_budgets_met':all(flags.values()),'material_qualified':False,'training_eligible':False,
        'scope':'Every recorded cell and full local/exterior/entropy 2/4 Gauss integrals. Independent source/face expansion with shared flash and surface root.'}
    with args.output.open('x') as out:
        json.dump(result,out,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met']}))


if __name__=='__main__':
    main()
