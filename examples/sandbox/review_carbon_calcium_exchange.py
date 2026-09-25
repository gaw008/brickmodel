"""Independent elemental Gibbs derivatives and two-cell face thermodynamics."""
import argparse
import json
from pathlib import Path

from mpmath import mp

from carbon_calcium_pressure_setup import build
from carbon_calcium_rigid_decimal_reference import reconstruct
from sludge_sandbox.carbon_calcium_rigid_exchange import exchange


def source_face(left,right,tl,tr,parameters):
    tl,tr=mp.mpf(tl),mp.mpf(tr)
    names=parameters['gas_order']
    h={name:(left['thermal'][name][0]+right['thermal'][name][0])/2 for name in names}
    forces={name:left['mu'][name]/tl-right['mu'][name]/tr+h[name]*(1/tr-1/tl) for name in names}
    flow={name:mp.mpf(parameters['gas_mobilities_mol2_k_j_s'][name])*forces[name] for name in names}
    energy=mp.mpf(parameters['heat_conductance_w_k'])*(tl-tr)+mp.fsum(h[k]*flow[k] for k in names)
    sl=(-energy+mp.fsum(left['mu'][k]*flow[k] for k in names))/tl
    sr=(energy-mp.fsum(right['mu'][k]*flow[k] for k in names))/tr
    elements={'carbon_atoms_mol':flow['CO']+flow['CO2'],
              'oxygen_atoms_mol':flow['CO']+2*flow['CO2']+2*flow['O2'],
              'nitrogen_molecules_mol':flow['N2']}
    return {'gas':flow,'inventory':elements,'energy':energy,'left_entropy':sl,'right_entropy':sr,'production':sl+sr}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    parameters=json.loads((root/settings['exchange_parameters']).read_text())
    rigid=json.loads((root/parameters['rigid_parameters']).read_text())
    pressure=json.loads((root/rigid['pressure_parameters']).read_text());model,sources,_=build(root,pressure)
    mp.dps=settings['decimal_digits'];budget=settings['budgets'];volume=rigid['virtual_volume_m3']
    keys=['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']
    reviews=[];faces=[]
    for inventory in pressure['inventories']:
        states=[];references=[]
        for temp in settings['temperature_points_k']:
            state=model.at_temperature_volume(temp,volume,*[inventory[k] for k in keys],rigid['numerics'])
            ref=reconstruct(model,temp,volume,inventory,state,settings);states.append(state);references.append(ref)
            mu=ref['mu'];potentials={'carbon_atoms_mol':mu['CO']-mu['O2']/2,
                                    'oxygen_atoms_mol':mu['O2']/2,'nitrogen_molecules_mol':mu['N2']}
            gas_error=abs(mu['CO2']-potentials['carbon_atoms_mol']-2*potentials['oxygen_atoms_mol'])
            derivatives=[]
            for name in parameters['transferred_inventory_order']:
                for relative_step in settings['inventory_relative_difference_steps']:
                    step=mp.mpf(relative_step)*mp.mpf(inventory[name]);pair=[];phases=[]
                    for sign in [-1,1]:
                        altered={**inventory,name:mp.mpf(inventory[name])+sign*step}
                        candidate=model.at_temperature_volume(temp,volume,*[float(altered[k]) for k in keys],rigid['numerics'])
                        phases.append((candidate['calcium_phase'],candidate['carbon_phase']))
                        pair.append(reconstruct(model,temp,volume,altered,candidate,settings))
                    derivative=(pair[1]['internal_energy']-pair[0]['internal_energy']
                                -mp.mpf(temp)*(pair[1]['entropy']-pair[0]['entropy']))/(2*step)
                    error=float(abs(derivative-potentials[name]))
                    flags={'gibbs_derivative':error<=budget['inventory_gibbs_derivative_j_mol'],
                           'same_phase':all(p==(state['calcium_phase'],state['carbon_phase']) for p in phases)}
                    derivatives.append({'inventory_coordinate':name,'relative_difference_step':relative_step,
                        'source_derivative_j_mol':str(derivative),'element_potential_j_mol':str(potentials[name]),
                        'absolute_error_j_mol':error,'within_budgets':flags})
            same=exchange(model,state,state,parameters)
            flags={'gas_element_potential':float(gas_error)<=budget['gas_element_potential_j_mol'],
                'derivatives':all(all(r['within_budgets'].values()) for r in derivatives),
                'identical_state_zero_flow':all(v==0 for v in same['gas_flows_mol_s'].values())
                    and same['energy_flow_w']==0 and same['entropy_production_w_k']==0}
            reviews.append({'inventory':inventory,'state':state,'derivatives':derivatives,
                'gas_element_potential_error_j_mol':float(gas_error),'within_budgets':flags})
            print(json.dumps({'inventory':inventory['name'],'temperature_k':temp,'flags':flags}),flush=True)
        for a,b in settings['pairings']:
            left,right=states[a],states[b];candidate=exchange(model,left,right,parameters)
            reverse=exchange(model,right,left,parameters)
            ref=source_face(references[a],references[b],left['temperature_k'],right['temperature_k'],parameters)
            errors={'face_gas_rate_mol_s':max(float(abs(mp.mpf(candidate['gas_flows_mol_s'][k])-v)) for k,v in ref['gas'].items()),
                'face_inventory_rate_mol_s':max(float(abs(mp.mpf(candidate['inventory_flows_mol_s'][k])-v)) for k,v in ref['inventory'].items()),
                'face_energy_w':float(abs(mp.mpf(candidate['energy_flow_w'])-ref['energy'])),
                'face_entropy_rate_w_k':max(float(abs(mp.mpf(candidate[k])-ref[v])) for k,v in
                    [('left_entropy_rate_w_k','left_entropy'),('right_entropy_rate_w_k','right_entropy'),('entropy_production_w_k','production')])}
            identity=abs(candidate['left_entropy_rate_w_k']+candidate['right_entropy_rate_w_k']-candidate['entropy_production_w_k'])
            flags={k:v<=budget[k] for k,v in errors.items()}
            flags.update(entropy_identity=identity<=budget['face_entropy_rate_w_k'],
                nonnegative_entropy=candidate['entropy_production_w_k']>=0 and ref['production']>=0,
                exact_reversal=all(candidate['gas_flows_mol_s'][k]==-reverse['gas_flows_mol_s'][k] for k in parameters['gas_order'])
                    and candidate['energy_flow_w']==-reverse['energy_flow_w']
                    and candidate['entropy_production_w_k']==reverse['entropy_production_w_k'])
            faces.append({'inventory_name':inventory['name'],'temperatures_k':[left['temperature_k'],right['temperature_k']],
                          'face':candidate,'errors':errors,'entropy_identity_error_w_k':identity,'within_budgets':{k:bool(v) for k,v in flags.items()}})
    result={'settings':settings,'exchange_parameters':parameters,'rigid_parameters':rigid,'pressure_parameters':pressure,
        'sources':sources,'state_reviews':reviews,'face_reviews':faces,
        'all_requested_budgets_met':all(all(r['within_budgets'].values()) for r in reviews+faces),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
