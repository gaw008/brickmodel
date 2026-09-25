"""Source and Maxwell-moment qualification of the collisionless aperture limit."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial import Polynomial
from scipy.integrate import quad

from calcite_closed_setup import build_closed
from sludge_sandbox.effusive_gas_face import effusive_gas_face


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    config = json.loads((root/settings['thermochemistry_parameters']).read_text())
    reaction, nitrogen, affinity, source, facts, nsource = build_closed(root, config)
    phases = {'co2': reaction.phases[reaction.gas_phase], 'nitrogen': nitrogen}
    r = reaction.gas_constant_j_mol_k; p0 = reaction.standard_pressure_pa
    aperture = settings['aperture']; area = aperture['area_m2']
    budgets = settings['verification']; quadrature = settings['quadrature']
    integrate = lambda f, a, b: quad(f, a, b, **quadrature)[0]
    moments = {str(k): integrate(lambda x: x**k*math.exp(-x*x), 0., math.inf) for k in (3, 5)}
    angular = integrate(lambda theta: math.cos(theta)*math.sin(theta), 0., math.pi/2)
    moment_flags = {'third': abs(moments['3']-.5)<=budgets['moment_absolute'],
                    'fifth': abs(moments['5']-1.)<=budgets['moment_absolute'],
                    'angular': abs(angular-.5)<=budgets['moment_absolute']}

    def cp(phase, t):
        a,b,c,d,e = phase.coefficients
        return a+b*t+c/t**2+d/math.sqrt(t)+e*t*t

    extrema = {}
    for name, phase in phases.items():
        a,b,c,d,e = phase.coefficients
        # x=sqrt(T): dCp/dx=0 becomes 4e*x^8+2b*x^6-d*x^3-4c=0.
        roots = Polynomial([-4*c,0,0,-d,0,0,2*b,0,4*e]).roots()
        low,high = phase.temperature_domain_k
        candidates = [low,high]+[float(z.real*z.real) for z in roots
            if abs(z.imag)<=budgets['polynomial_real_root_tolerance'] and math.sqrt(low)<z.real<math.sqrt(high)]
        values = [{'temperature_k': t, 'cp_minus_half_R_j_mol_k': cp(phase,t)-r/2} for t in candidates]
        extrema[name] = {'stationary_polynomial_coefficients': [-4*c,0,0,-d,0,0,2*b,0,4*e],
                         'candidates': values, 'minimum': min(v['cp_minus_half_R_j_mol_k'] for v in values)}

    def state(point):
        t = point['temperature_k']; p = point['pressure_pa']; x = point['co2_fraction']
        result = {'temperature_k': t, 'pressure_pa': p}
        for name, fraction, potential in [('co2',x,'carbon'),('nitrogen',1-x,'nitrogen')]:
            phase = phases[name]; thermal = phase.standard(t); pi = p*fraction
            result[name+'_partial_pressure_pa'] = pi
            result[name+'_partial_enthalpy_j_mol'] = thermal['enthalpy_j_mol']
            result[potential+'_chemical_potential_j_mol'] = thermal['gibbs_j_mol']+r*t*math.log(pi/p0)
        return result

    def moment_side(name, point):
        t = point['temperature_k']; pi = point[name+'_partial_pressure_pa']
        mass = aperture['molar_masses_kg_mol'][name]; phase = phases[name]
        velocity = math.sqrt(2*r*t/mass)
        flux = pi/(r*t)*(mass/(2*math.pi*r*t))**1.5*velocity**4*moments['3']*angular*2*math.pi
        h = phase.reference_enthalpy_j_mol+integrate(lambda temp: cp(phase,temp), phase.reference_temperature_k,t)
        internal = h-2.5*r*t
        carried = internal+.5*mass*velocity**2*moments['5']/moments['3']
        return flux, carried

    reports = []
    for case in settings['cases']:
        left, right = state(case['left']), state(case['right'])
        result = effusive_gas_face(left,right,aperture,r)
        reverse = effusive_gas_face(right,left,aperture,r)
        tl,tr = left['temperature_k'], right['temperature_k']
        reviews = []
        for name, potential in [('co2','carbon'),('nitrogen','nitrogen')]:
            jl,el = moment_side(name,left); jr,er = moment_side(name,right)
            phase = phases[name]; recorded = result['species'][name]
            def energy(t):
                return phase.standard(t)['enthalpy_j_mol']-r*t/2
            terms = [r*(jl-jr)*math.log(jl/jr),
                jl*integrate(lambda t: (el-energy(t))/t**2,tr,tl),
                jr*integrate(lambda t: (energy(t)-er)/t**2,tr,tl)]
            residuals = {
                'molar_flux_mol_m2_s': abs((jl-jr)-recorded['flow_mol_s']/area),
                'energy_flux_w_m2': abs(jl*el-jr*er-recorded['energy_flow_w']/area),
                'entropy_decomposition_w_m2_k': abs(math.fsum(terms)-recorded['entropy_production_w_k']/area),
                'left_incident_mol_m2_s': abs(jl-recorded['left_incident_mol_m2_s']),
                'right_incident_mol_m2_s': abs(jr-recorded['right_incident_mol_m2_s'])}
            flags = {'flux_moments':max(residuals[k] for k in ('molar_flux_mol_m2_s','left_incident_mol_m2_s','right_incident_mol_m2_s'))<=budgets['species_flux_absolute_mol_m2_s'],
                'energy_moments':residuals['energy_flux_w_m2']<=budgets['energy_flux_absolute_w_m2'],
                'entropy_identity':residuals['entropy_decomposition_w_m2_k']<=budgets['entropy_flux_absolute_w_m2_k'],
                'nonnegative_terms':min(terms)>=-budgets['negative_entropy_flux_allowance_w_m2_k'],
                'nonnegative_species_entropy':recorded['entropy_production_w_k']/area>=-budgets['negative_entropy_flux_allowance_w_m2_k']}
            reviews.append({'species':name,'independent_left_flux_and_energy':[jl,el],
                'independent_right_flux_and_energy':[jr,er],'entropy_terms_w_m2_k':terms,
                'residuals':residuals,'within_budgets':flags})
        shifted_left,shifted_right = deepcopy(left),deepcopy(right)
        for name,potential in [('co2','carbon'),('nitrogen','nitrogen')]:
            shift = settings['gauge_shifts'][name]
            for point in [shifted_left,shifted_right]:
                point[name+'_partial_enthalpy_j_mol'] += shift['enthalpy_j_mol']
                point[potential+'_chemical_potential_j_mol'] += shift['enthalpy_j_mol']-point['temperature_k']*shift['entropy_j_mol_k']
        shifted = effusive_gas_face(shifted_left,shifted_right,aperture,r)
        energy_shift = math.fsum(settings['gauge_shifts'][name]['enthalpy_j_mol']*result['species'][name]['flow_mol_s'] for name in phases)
        gauge_energy = abs(shifted['energy_flow_w']-result['energy_flow_w']-energy_shift)/area
        gauge_entropy = abs(shifted['entropy_production_w_k']-result['entropy_production_w_k'])/area
        flags = {'species_reviews':all(all(review['within_budgets'].values()) for review in reviews),
            'reverse_species':max(abs(result[key]+reverse[key])/area for key in ('carbon_flow_mol_s','nitrogen_flow_mol_s'))<=budgets['species_flux_absolute_mol_m2_s'],
            'reverse_energy':abs(result['energy_flow_w']+reverse['energy_flow_w'])/area<=budgets['energy_flux_absolute_w_m2'],
            'reverse_entropy':abs(result['entropy_production_w_k']-reverse['entropy_production_w_k'])/area<=budgets['entropy_flux_absolute_w_m2_k'],
            'gauge_energy':gauge_energy<=budgets['energy_flux_absolute_w_m2'],
            'gauge_entropy':gauge_entropy<=budgets['entropy_flux_absolute_w_m2_k']}
        if case['name']=='balanced_species_thermal':
            flags['zero_species_flux'] = max(abs(result[key])/area for key in ('carbon_flow_mol_s','nitrogen_flow_mol_s'))<=budgets['species_flux_absolute_mol_m2_s']
            flags['positive_heat_and_entropy'] = result['energy_flow_w']>0 and result['entropy_production_w_k']>0
        reports.append({'name':case['name'],'left':left,'right':right,'face':result,'species_reviews':reviews,
            'gauge_energy_residual_w_m2':gauge_energy,'gauge_entropy_residual_w_m2_k':gauge_entropy,
            'within_budgets':flags})
    flags = {'maxwell_moments':all(moment_flags.values()),'carried_energy_monotonic':all(v['minimum']>0 for v in extrema.values()),
             'all_cases':all(all(report['within_budgets'].values()) for report in reports)}
    output = {'settings':settings,'sources':json.loads((root/settings['source_record']).read_text()),
        'gas_constant_j_mol_k':r,'thermochemistry':{'affinity':affinity,'source':source,'reference_facts':facts,'nitrogen_source':nsource},
        'velocity_moments':moments,'angular_integral':angular,'moment_flags':moment_flags,
        'carried_energy_derivative_extrema':extrema,'cases':reports,'within_budgets':flags,
        'all_requested_budgets_met':all(flags.values()),'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(output,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'within_budgets':flags,'cases':len(reports)}))


if __name__=='__main__':
    main()
