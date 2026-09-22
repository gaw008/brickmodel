"""Independent entropy ledger on saved BDF polynomials of the water column.

Temperature/phase decoding reuses the declared host. Entropy storage, face
transport and exterior entropy use independent source expressions. Direct
IAPWS liquid entropy shares the source EOS backend, not its fitted Gibbs table.
No runtime downloads and no adjustment of the saved conserved trajectory.
"""
import argparse
from functools import lru_cache
import json
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

import numpy as np
from iapws import IAPWS95
from numpy.polynomial.legendre import leggauss
from scipy.integrate import quad

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from analyze_equilibrium_water_column import surface_temperature
from equilibrium_water_column_setup import build_column
from review_equilibrium_water_column import reconstruct_face_rates
from water_column_checkpoint import restore_sources


class SourceEntropy:
    def __init__(self, header, settings):
        self.header, self.settings = header, settings
        self.config, self.thermo = header['parameters'], header['thermochemistry']
        self.facts = header['water_source']['facts']
        self.r = self.thermo['gas_constant']['value_j_mol_k']
        self.mass = IAPWS95.M/1000
        self.pref = self.config['reference_pressure_pa']
        self.offset = self.facts['gas_formation_h_j_mol']-self.water_ideal(self.facts['reference_temperature_k'])[0]
        self.solid_coefficients = header['solid_source_facts']['segments'][self.config['solid']['segment_index']]['coefficients']
        self.ideal = lru_cache(maxsize=settings['property_cache_entries'])(self.ideal)

    def water_ideal(self, t):
        c, a = self.facts['iapws_constants'], self.facts['ideal_formula_constants']
        tau = c['T_critical_k']/t
        phi = math.log(self.pref/(c['R_specific_j_kg_k']*t*c['rho_critical_kg_m3']))
        phi += a['n1']+a['n2']*tau+a['n3']*math.log(tau)
        derivative = a['n2']*tau+a['n3']
        for n, g in zip(a['n4_to_n8'], a['gamma4_to_gamma8'], strict=True):
            phi += n*math.log1p(-math.exp(-g*tau))
            derivative += n*g*tau/(math.exp(g*tau)-1)
        native_r = c['R_specific_j_kg_k']*self.mass
        return native_r*t*(1+derivative), native_r*(derivative-phi)

    def ideal(self, species, t):
        if species == 'H2O':
            h, s = self.water_ideal(t)
            return h+self.offset, s
        record = next(p for p in self.thermo['species'] if p['species_id'] == species)
        segment = next(p for p in record['segments'] if p['temperature_range_k'][0] <= t <= p['temperature_range_k'][1])
        a,b,c,d,e,f,g,h0 = segment['coefficients']
        x = t/1000
        return (record['formation_enthalpy_298_j_mol']+1000*(a*x+b*x*x/2+c*x**3/3+d*x**4/4-e/x+f-h0),
                a*math.log(x)+b*x+c*x*x/2+d*x**3/3-e/(2*x*x)+g)

    def chemical_over_t(self, t, partial_pressures):
        return {k: self.ideal(k,t)[0]/t-self.ideal(k,t)[1]+self.r*math.log(p/self.pref)
                for k,p in partial_pressures.items()}

    def entropy(self, states):
        a,b,c,d,e,_,_,_ = map(float,self.solid_coefficients)
        q = self.settings['solid_entropy_quadrature']
        values = []
        for p in states:
            t = p['temperature_k']
            gas = math.fsum(n*(self.ideal(k,t)[1]-self.r*math.log(n*self.r*t/p['gas_volume_m3']/self.pref))
                            for k,n in p['amounts_mol'].items())
            liquid = 0.
            if p['liquid_water_mol'] > 0:
                liquid = p['liquid_water_mol']*IAPWS95(T=t,P=p['pressure_pa']/1e6).s*1000*self.mass
            solid,_ = quad(lambda temp: (a+b*(temp/1000)+c*(temp/1000)**2+d*(temp/1000)**3+e/(temp/1000)**2)/temp,
                self.config['solid']['reference_temperature_k'],t,
                epsabs=q['absolute_tolerance_j_mol_k'],epsrel=q['relative_tolerance'],limit=q['maximum_subintervals'])
            values.append(gas+liquid+solid*self.config['solid']['total_mol']/len(states))
        return math.fsum(values)

    def fluxes(self, t, states):
        config = self.config
        p = config['boundary_program']['values']
        interp = lambda key: float(np.interp(t,p['knot_times_s'],p[key]))
        boundary = {'gas_temperature_k':interp('gas_temperature_k'),'radiation_temperature_k':interp('radiation_temperature_k'),
            'total_pressure_pa':interp('total_pressure_pa'), 'mole_fractions':{
                k:float(np.interp(t,p['knot_times_s'],np.array(p['mole_fractions'])[:,i])) for i,k in enumerate(p['species_order'])}}
        ts = surface_temperature(config,len(states),t,states[-1]['temperature_k'])
        area = config['geometry']['area_m2']
        surface = {'convective_in_w':config['transfer']['external_conductivity_w_m_k']*area/config['transfer']['external_distance_m']*(boundary['gas_temperature_k']-ts),
            'radiative_in_w':config['radiation']['effective_emissivity']*config['radiation']['stefan_boltzmann_w_m2_k4']*area*(boundary['radiation_temperature_k']**4-ts**4)}
        faces,radiation = reconstruct_face_rates(config,states,boundary,surface,self.ideal,self.r)
        temperatures = [s['temperature_k'] for s in states]+[boundary['gas_temperature_k']]
        mus = [self.chemical_over_t(s['temperature_k'],{k:n*self.r*s['temperature_k']/s['gas_volume_m3'] for k,n in s['amounts_mol'].items()}) for s in states]
        mus.append(self.chemical_over_t(boundary['gas_temperature_k'],{k:x*boundary['total_pressure_pa'] for k,x in boundary['mole_fractions'].items()}))
        productions = []
        for i,face in enumerate(faces):
            production = face['energy_out_w']*(1/temperatures[i+1]-1/temperatures[i])
            production += math.fsum(j*(mus[i][k]-mus[i+1][k]) for k,j in face['exchange']['net_mol_s'].items())
            if i == len(states)-1:
                production += radiation*(1/boundary['radiation_temperature_k']-1/temperatures[i])
            productions.append(production)
        external = faces[-1]['energy_out_w']/boundary['gas_temperature_k']
        external -= math.fsum(mus[-1][k]*j for k,j in faces[-1]['exchange']['net_mol_s'].items())
        external += radiation/boundary['radiation_temperature_k']
        return external, math.fsum(productions), min(productions)


def evaluate_polynomial(record,t):
    products = np.cumprod((t-np.array(record['shifts_s']))/np.array(record['denominators_s']))
    differences = np.array(record['differences'])
    return differences[0]+differences[1:].T@products


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trajectory',required=True,type=Path)
    parser.add_argument('--parameters',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    start=time.monotonic()
    rows=[json.loads(line) for line in args.trajectory.read_text().splitlines()]
    header=rows[0]; settings=json.loads(args.parameters.read_text()); source=SourceEntropy(header,settings)
    order=header['parameters']['boundary_program']['values']['species_order']; width=len(order)+1; n=header['cell_count']
    accepted=[r for r in rows if r['kind']=='accepted']
    s0=source.entropy(rows[1]['states'])
    results=[]
    with TemporaryDirectory(prefix='brick-entropy-sources-') as directory:
        directory=Path(directory)
        model=build_column(directory,restore_sources(header,directory),n)
        for degree in settings['quadrature_orders']:
            nodes,weights=leggauss(degree)
            seeds=[p['temperature_k'] for p in rows[1]['states']]
            inverse_error=0.
            def decode(vector):
                nonlocal inverse_error
                points=[]
                for i,cell in enumerate(vector[:n*width].reshape(n,width)):
                    _,point=model.host.decode(dict(zip(order,map(float,cell[:-1]),strict=True)),float(cell[-1]),seeds[i])
                    seeds[i]=point['temperature_k'];points.append(point)
                    inverse_error=max(inverse_error,abs(point['energy_inverse_residual_j']))
                return points
            external=production=0.
            last_entropy=s0
            minimum_face=None
            residual_max=0.
            steps=[]
            previous_vector=np.array([[p['inventories_mol'][k] for k in order]+[p['internal_energy_j']]
                for p in rows[1]['states']]+[[0.]*width]).ravel()
            endpoint_difference=np.zeros_like(previous_vector)
            for row in accepted:
                polynomial=row['dense_output'];left,right=polynomial['start_time_s'],polynomial['end_time_s']
                current_vector=np.array(row['conserved_state'])
                endpoint_difference=np.maximum(endpoint_difference,np.abs(evaluate_polynomial(polynomial,left)-previous_vector))
                endpoint_difference=np.maximum(endpoint_difference,np.abs(evaluate_polynomial(polynomial,right)-current_vector))
                ext_terms=[];sigma_terms=[]
                for node,weight in zip(nodes,weights,strict=True):
                    t=(left+right)/2+float(node)*(right-left)/2
                    points=decode(evaluate_polynomial(polynomial,t))
                    ext,sigma,minimum=source.fluxes(t,points)
                    ext_terms.append(float(weight)*ext*(right-left)/2)
                    sigma_terms.append(float(weight)*sigma*(right-left)/2)
                    minimum_face=minimum if minimum_face is None else min(minimum_face,minimum)
                ext_step=math.fsum(ext_terms);sigma_step=math.fsum(sigma_terms)
                external+=ext_step;production+=sigma_step
                entropy=source.entropy(decode(np.array(row['conserved_state'])))
                residual=entropy-s0+external-production
                residual_max=max(residual_max,abs(residual))
                steps.append({'time_s':right,'system_entropy_j_k':entropy,'external_entropy_integral_j_k':external,
                    'face_production_integral_j_k':production,'entropy_balance_residual_j_k':residual,
                    'step_total_entropy_change_j_k':entropy-last_entropy+ext_step})
                last_entropy=entropy
                previous_vector=current_vector
            budgets=settings['numerical_comparison_budgets']
            results.append({'quadrature_order':degree,'steps':steps,'max_entropy_balance_residual_j_k':residual_max,
                'final_total_entropy_change_j_k':last_entropy-s0+external,'final_face_production_integral_j_k':production,
                'minimum_step_total_entropy_change_j_k':min(r['step_total_entropy_change_j_k'] for r in steps),
                'minimum_sampled_face_production_w_k':minimum_face,'maximum_decode_energy_residual_j':inverse_error,
                'dense_endpoint_inventory_difference_mol':float(np.max(endpoint_difference.reshape(n+1,width)[:,:-1])),
                'dense_endpoint_energy_difference_j':float(np.max(endpoint_difference.reshape(n+1,width)[:,-1])),
                'within_balance_budget':residual_max<=budgets['entropy_balance_j_k'],
                'decode_within_energy_budget':inverse_error<=budgets['temperature_inverse_energy_j'],
                'negative_steps_beyond_budget':sum(r['step_total_entropy_change_j_k'] < -budgets['negative_step_entropy_allowance_j_k'] for r in steps)})
            print(json.dumps({k:v for k,v in results[-1].items() if k!='steps'}),flush=True)
    differences={key:max(abs(a[key]-b[key]) for a,b in zip(results[-2]['steps'],results[-1]['steps'],strict=True))
        for key in ('external_entropy_integral_j_k','face_production_integral_j_k')}
    result={'trajectory':str(args.trajectory),'settings':settings,'initial_entropy_j_k':s0,'quadrature_results':results,
        'trajectory_completed':rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        'recorded_time_interval_s':[accepted[0]['dense_output']['start_time_s'],accepted[-1]['time_s']],
        'max_external_quadrature_difference_j_k':differences['external_entropy_integral_j_k'],
        'max_production_quadrature_difference_j_k':differences['face_production_integral_j_k'],
        'quadrature_difference_within_budget':max(differences.values())<=settings['numerical_comparison_budgets']['quadrature_difference_j_k'],
        'elapsed_s':time.monotonic()-start,'material_qualified':False,
        'scope':'Recorded numerical trajectory and source entropy expressions. Shared temperature/phase decoder and EOS backend; no universal entropy or material proof.'}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'status':'completed','elapsed_s':result['elapsed_s'],'quadrature_differences_j_k':differences}),flush=True)


if __name__=='__main__':
    main()
