"""Full source, finite-inventory, local energy and entropy audit of effusion."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.integrate import quad
from scipy.optimize import brentq

from audit_sorptive_gas_cell import polynomial
from calcite_affinity_setup import from_records
from calcite_closed_setup import nitrogen_from_record
from sludge_sandbox.recorded_ideal_gas_cell import RecordedIdealGasCell


def rows(path):
    with path.open() as stream:
        for line in stream:
            yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trajectory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();stream = rows(args.trajectory);header = next(stream);initial = next(stream)
    settings = header['settings'];budget = settings['verification'];policy = settings['numerics']
    reaction = from_records(header['affinity_parameters'],header['source'],header['reference_facts'])
    phases = {'co2':reaction.phases[reaction.gas_phase],'nitrogen':nitrogen_from_record(header['nitrogen_source'])}
    r,p0 = reaction.gas_constant_j_mol_k,reaction.standard_pressure_pa
    volumes = [c['volume_m3'] for c in settings['cells']]
    cells = [RecordedIdealGasCell(phases,r,p0,v,policy) for v in volumes]
    aperture = header['aperture'];area = aperture['area_m2']
    face_budget = header['face_settings']['verification']
    integrate = lambda f,a,b:quad(f,a,b,epsabs=budget['quadrature_absolute'],
        epsrel=budget['quadrature_relative'],limit=budget['quadrature_limit'])[0]
    i3 = integrate(lambda x:x**3*math.exp(-x*x),0.,math.inf)
    i5 = integrate(lambda x:x**5*math.exp(-x*x),0.,math.inf)
    def thermal(name,t):
        phase = phases[name];a,b,c,d,e = phase.coefficients
        cp = lambda temp:a+b*temp+c/temp**2+d/math.sqrt(temp)+e*temp*temp
        h = phase.reference_enthalpy_j_mol+integrate(cp,phase.reference_temperature_k,t)
        s = phase.reference_entropy_j_mol_k+integrate(lambda temp:cp(temp)/temp,phase.reference_temperature_k,t)
        return h,s
    def source_state(t,carbon,carrier,volume):
        result = {'temperature_k':t,'pressure_pa':(carbon+carrier)*r*t/volume,'species':{}}
        energy=[];entropy=[]
        for name,amount in [('co2',carbon),('nitrogen',carrier)]:
            h,s = thermal(name,t);p = amount*r*t/volume;smol = s-r*math.log(p/p0)
            result['species'][name] = {'p':p,'h':h,'mu':h-t*smol}
            energy.append(amount*(h-r*t));entropy.append(amount*smol)
        result['U'] = math.fsum(energy);result['S'] = math.fsum(entropy)
        return result
    def face(states):
        tl,tr = [s['temperature_k'] for s in states];flows=[];energies=[];sl=[];sr=[]
        for name in phases:
            incident=[];carried=[];mu=[]
            mass = aperture['molar_masses_kg_mol'][name]
            for state in states:
                t = state['temperature_k'];s = state['species'][name];speed = math.sqrt(2*r*t/mass)
                incident.append(s['p']/(r*t)*(mass/(2*math.pi*r*t))**1.5*speed**4*i3*math.pi)
                carried.append(s['h']-2.5*r*t+.5*mass*speed*speed*i5/i3);mu.append(s['mu'])
            flow = area*(incident[0]-incident[1]);energy = area*(incident[0]*carried[0]-incident[1]*carried[1])
            flows.append(flow);energies.append(energy)
            sl.append((-energy+mu[0]*flow)/tl);sr.append((energy-mu[1]*flow)/tr)
        return np.array(flows+[math.fsum(energies)]),np.array([math.fsum(sl),math.fsum(sr)])
    def evaluate(values):
        states = [c.inventory_state(*values[3*i:3*i+3]) for i,c in enumerate(cells)]
        source = [source_state(s['temperature_k'],*values[3*i:3*i+2],volumes[i]) for i,s in enumerate(states)]
        return face(source)
    v0 = np.array(initial['values'][:6]).reshape(2,3);totals = v0.sum(axis=0)
    initial_s = np.array([s['entropy_j_k'] for s in initial['states']])
    total_volume = sum(volumes)
    equilibrium_t = brentq(lambda t:source_state(t,*totals[:2],total_volume)['U']-totals[2],
        *policy['temperature_bracket_k'],xtol=policy['temperature_absolute_k'],rtol=policy['temperature_relative'],maxiter=policy['temperature_iterations'])
    equilibrium = source_state(equilibrium_t,*totals[:2],total_volume)
    maximum = {key:0. for key in ['source_energy_j','source_entropy_j_k','species_ledger_mol',
        'energy_ledger_j','entropy_ledger_j_k','entropy_above_equilibrium_j_k','face_species_mol_s','face_energy_w','face_entropy_w_k']}
    observed = steps = 0;minimum_species = minimum_entropy = math.inf
    for row in rows(args.trajectory):
        terminal = row
        if row['kind'] not in ('initial','accepted','sample'):continue
        observed += 1;steps += row['kind']=='accepted'
        values = np.array(row['values']);inventory = values[:6].reshape(2,3)
        source = [source_state(s['temperature_k'],*inventory[i,:2],volumes[i]) for i,s in enumerate(row['states'])]
        for s,point in zip(source,row['states'],strict=True):
            maximum['source_energy_j'] = max(maximum['source_energy_j'],abs(s['U']-point['internal_energy_j']))
            maximum['source_entropy_j_k'] = max(maximum['source_entropy_j_k'],abs(s['S']-point['entropy_j_k']))
        residual = inventory-v0+np.array([values[6:9],-values[6:9]])
        maximum['species_ledger_mol'] = max(maximum['species_ledger_mol'],float(np.max(np.abs(residual[:,:2]))),float(np.max(np.abs(inventory.sum(axis=0)[:2]-totals[:2]))))
        maximum['energy_ledger_j'] = max(maximum['energy_ledger_j'],float(np.max(np.abs(residual[:,2]))),float(abs(inventory.sum(axis=0)[2]-totals[2])))
        entropy = math.fsum(s['S'] for s in source)
        maximum['entropy_ledger_j_k'] = max(maximum['entropy_ledger_j_k'],abs(entropy-initial_s.sum()-values[-1]))
        maximum['entropy_above_equilibrium_j_k'] = max(maximum['entropy_above_equilibrium_j_k'],entropy-equilibrium['S'])
        flux,entropy_rate = face(source);recorded = row['face']
        maximum['face_species_mol_s'] = max(maximum['face_species_mol_s'],abs(flux[0]-recorded['carbon_flow_mol_s']),abs(flux[1]-recorded['nitrogen_flow_mol_s']))
        maximum['face_energy_w'] = max(maximum['face_energy_w'],abs(flux[2]-recorded['energy_flow_w']))
        maximum['face_entropy_w_k'] = max(maximum['face_entropy_w_k'],abs(entropy_rate.sum()-recorded['entropy_production_w_k']))
        minimum_species = min(minimum_species,float(inventory[:,:2].min()));minimum_entropy = min(minimum_entropy,float(entropy_rate.sum()))
    reviews = []
    for order in budget['quadrature_orders']:
        nodes,weights = leggauss(order);total = np.zeros(3);total_s = np.zeros(2);local = np.zeros(3);cumulative = np.zeros(3)
        local_s = 0.;minimum_step = math.inf;previous = initial
        for row in rows(args.trajectory):
            if row['kind']!='accepted':continue
            dense = row['dense_output'];left,right = dense['start_time_s'],dense['end_time_s'];interval = np.zeros(3);entropy = np.zeros(2)
            for node,weight in zip(nodes,weights,strict=True):
                at=(left+right)/2+(right-left)*node/2;factor=weight*(right-left)/2
                flux,srate=evaluate(polynomial(dense,at));interval += factor*flux;entropy += factor*srate
            total += interval;total_s += entropy
            inventory = np.array(row['values'][:6]).reshape(2,3);before = np.array(previous['values'][:6]).reshape(2,3)
            local = np.maximum(local,np.max(np.abs(inventory-before+np.array([interval,-interval])),axis=0))
            cumulative = np.maximum(cumulative,np.max(np.abs(inventory-v0+np.array([total,-total])),axis=0))
            s = np.array([p['entropy_j_k'] for p in row['states']]);local_s = max(local_s,float(np.max(np.abs(s-initial_s-total_s))))
            minimum_step = min(minimum_step,float(s.sum()-sum(p['entropy_j_k'] for p in previous['states'])))
            previous=row
        flags = {'local_species':max(local[:2])<=budget['species_mol'],'local_energy':local[2]<=budget['energy_j'],
            'cumulative_species':max(cumulative[:2])<=budget['species_mol'],'cumulative_energy':cumulative[2]<=budget['energy_j'],
            'local_entropy':local_s<=budget['entropy_j_k'],'entropy_step_sign':minimum_step>=-budget['negative_step_entropy_j_k']}
        reviews.append({'quadrature_order':order,'maximum_local_C_N_U':local.tolist(),'maximum_cumulative_C_N_U':cumulative.tolist(),
            'maximum_local_entropy_j_k':local_s,'minimum_entropy_increment_j_k':minimum_step,'integrated_face_C_N_U':total.tolist(),
            'integrated_cell_entropy_j_k':total_s.tolist(),'within_budgets':{k:bool(v) for k,v in flags.items()}})
    final = terminal['final'];states = final['states'];inventory = np.array(final['values'][:6]).reshape(2,3)
    expected = np.array([v/total_volume*totals[:2] for v in volumes])
    equilibrium_differences = {'temperature_k':max(abs(s['temperature_k']-equilibrium_t) for s in states),
        'pressure_pa':max(abs(s['pressure_pa']-equilibrium['pressure_pa']) for s in states),'species_mol':float(np.max(np.abs(inventory[:,:2]-expected)))}
    difference = np.abs(np.array(reviews[0]['integrated_face_C_N_U'])-np.array(reviews[-1]['integrated_face_C_N_U']))
    sdifference = np.max(np.abs(np.array(reviews[0]['integrated_cell_entropy_j_k'])-np.array(reviews[-1]['integrated_cell_entropy_j_k'])))
    flags = {'completed':terminal['kind']=='summary' and terminal['status']=='completed','positive_species':minimum_species>0,
        'source_energy':maximum['source_energy_j']<=budget['source_energy_j'],'source_entropy':maximum['source_entropy_j_k']<=budget['source_entropy_j_k'],
        'species_ledger':maximum['species_ledger_mol']<=budget['species_mol'],'energy_ledger':maximum['energy_ledger_j']<=budget['energy_j'],
        'entropy_ledger':maximum['entropy_ledger_j_k']<=budget['entropy_j_k'],'entropy_upper_bound':maximum['entropy_above_equilibrium_j_k']<=budget['entropy_j_k'],
        'independent_face_species':maximum['face_species_mol_s']/area<=face_budget['species_flux_absolute_mol_m2_s'],
        'independent_face_energy':maximum['face_energy_w']/area<=face_budget['energy_flux_absolute_w_m2'],
        'independent_face_entropy':maximum['face_entropy_w_k']/area<=face_budget['entropy_flux_absolute_w_m2_k'],
        'face_entropy_sign':minimum_entropy/area>=-face_budget['negative_entropy_flux_allowance_w_m2_k'],
        'dense_integrals':all(all(v['within_budgets'].values()) for v in reviews),
        'quadrature_agreement':max(difference[:2])<=budget['species_mol'] and difference[2]<=budget['energy_j'] and sdifference<=budget['entropy_j_k']}
    equilibrium_flags = {k:bool(value<=budget['equilibrium_'+k]) for k,value in equilibrium_differences.items()}
    result = {'trajectory':str(args.trajectory),'settings':settings,'accepted_steps':steps,'recorded_cell_states':observed*2,
        'maximum_residuals':maximum,'minimum_species_mol':minimum_species,'minimum_face_entropy_w_k':minimum_entropy,
        'independent_equilibrium':equilibrium,'final_equilibrium_differences':equilibrium_differences,
        'within_equilibrium_budgets':equilibrium_flags,'integral_reviews':reviews,'quadrature_C_N_U_differences':difference.tolist(),
        'quadrature_entropy_difference_j_k':float(sdifference),'within_budgets':{k:bool(v) for k,v in flags.items()},
        'all_requested_numerical_budgets_met':all(flags.values()),'equilibrium_target_met':all(equilibrium_flags.values()),
        'scope':'Full recorded source expansion and independent source/Maxwell 2/4-point interval integrals. Dense states share the production temperature inverse. Final equilibrium follows total inventories, volume and independent source U.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],
        'equilibrium_target_met':result['equilibrium_target_met']}))


if __name__=='__main__':
    main()
