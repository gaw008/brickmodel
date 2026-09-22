"""Source-formula caloric reconstruction and sampled nominal face entropy.

No equilibrium cell, column host or surface solver is imported. IAPWS95 remains
the shared pure-water EOS backend, so this is not an independent EOS validation.
"""
import argparse
import json
import math
from pathlib import Path

from iapws import IAPWS95
from scipy.integrate import quad


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--trajectory', required=True, type=Path)
    parser.add_argument('--selection', required=True, choices=('landmarks', 'all', 'events'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    settings = json.loads(args.parameters.read_text())
    quadrature = settings['solid_caloric_quadrature']
    rows = [json.loads(line) for line in args.trajectory.read_text().splitlines()]
    header = rows[0]
    config, thermo = header['parameters'], header['thermochemistry']
    facts = header['water_source']['facts']
    constants, coefficients = facts['iapws_constants'], facts['ideal_formula_constants']
    gas_constant = thermo['gas_constant']['value_j_mol_k']
    mass = IAPWS95.M/1000
    native_r = constants['R_specific_j_kg_k']*mass
    pref = config['reference_pressure_pa']

    def ideal_water(t):
        tau = constants['T_critical_k']/t
        phi = math.log(pref/(constants['R_specific_j_kg_k']*t*constants['rho_critical_kg_m3']))
        phi += coefficients['n1']+coefficients['n2']*tau+coefficients['n3']*math.log(tau)
        derivative = coefficients['n2']*tau+coefficients['n3']
        for n, g in zip(coefficients['n4_to_n8'], coefficients['gamma4_to_gamma8'], strict=True):
            phi += n*math.log1p(-math.exp(-g*tau))
            derivative += n*g*tau/(math.exp(g*tau)-1)
        return native_r*t*(1+derivative), native_r*(derivative-phi)

    offset = facts['gas_formation_h_j_mol']-ideal_water(facts['reference_temperature_k'])[0]

    def ideal_properties(species_id, t):
        if species_id == 'H2O':
            h, s = ideal_water(t)
            return h+offset, s
        record = next(p for p in thermo['species'] if p['species_id'] == species_id)
        segment = next(p for p in record['segments'] if p['temperature_range_k'][0] <= t <= p['temperature_range_k'][1])
        a, b, c, d, e, f, g, h0 = segment['coefficients']
        x = t/1000
        h = record['formation_enthalpy_298_j_mol']+1000*(a*x+b*x*x/2+c*x**3/3+d*x**4/4-e/x+f-h0)
        s = a*math.log(x)+b*x+c*x*x/2+d*x**3/3-e/(2*x*x)+g
        return h, s

    def chemical_over_temperature(t, partial_pressures):
        return {k: ideal_properties(k, t)[0]/t-ideal_properties(k, t)[1]+
                   gas_constant*math.log(p/pref) for k, p in partial_pressures.items()}

    solid = header['solid_source_facts']['segments'][config['solid']['segment_index']]
    a, b, c, d, e, _, _, _ = map(float, solid['coefficients'])

    def cp(t):
        x = t/1000
        return a+b*x+c*x*x+d*x**3+e/(x*x)

    selected = [('initial', rows[1]['states']), ('final', rows[-1]['final'])]
    first_dry = next(r for r in rows if r['kind'] in ('step', 'sample') and
                     all(p['liquid_water_mol'] == 0 for p in r['states']))
    selected.append(('first_sample_all_liquid_depleted', first_dry['states']))
    if args.selection == 'all':
        selected = [(r['time_s'], r['states']) for r in rows if r['kind'] in ('initial', 'step', 'sample')]
    if args.selection == 'events':
        selected = [(r['time_s'], r['states']) for r in rows if r['kind'] == 'phase_event']
    reconstructions = []
    for label, points in selected:
        for index, p in enumerate(points):
            t = p['temperature_k']
            liquid = IAPWS95(T=t, P=p['pressure_pa']/1e6)
            ul = liquid.u*1000*mass+offset
            us, error = quad(cp, config['solid']['reference_temperature_k'], t,
                epsabs=quadrature['absolute_tolerance_j_mol'], epsrel=quadrature['relative_tolerance'],
                limit=quadrature['maximum_subintervals'])
            us *= config['solid']['total_mol']/header['cell_count']
            ug = math.fsum(n*(ideal_properties(k, t)[0]-gas_constant*t) for k, n in p['amounts_mol'].items())
            u = ug+p['liquid_water_mol']*ul+us
            vg = header['cell_fluid_volume_m3']-p['liquid_water_mol']*mass/liquid.rho
            pressure = math.fsum(p['amounts_mol'].values())*gas_constant*t/vg
            vapor_pressure = p['amounts_mol']['H2O']*gas_constant*t/vg
            h0, s0 = ideal_properties('H2O', t)
            mu_vapor = h0-t*(s0-gas_constant*math.log(vapor_pressure/pref))
            mu_liquid = liquid.h*1000*mass+offset-t*liquid.s*1000*mass
            reconstructions.append({'point': label, 'cell': index, 'phase': p['phase'],
                'temperature_k': t, 'solid_cp_j_mol_k': cp(t),
                'solid_energy_difference_j': us-p['solid_internal_energy_j'],
                'quadrature_estimated_absolute_error_j': error*config['solid']['total_mol']/header['cell_count'],
                'total_energy_residual_j': u-p['internal_energy_j'],
                'pressure_residual_pa': pressure-p['pressure_pa'],
                'vapor_minus_liquid_chemical_potential_j_mol': mu_vapor-mu_liquid,
                'phase_condition': 'equality' if p['liquid_water_mol'] > 0 else 'vapor_not_above_liquid'})

    def phase_criterion(p):
        t = p['temperature_k']
        v = header['cell_fluid_volume_m3']
        all_vapor_pressure = math.fsum(p['inventories_mol'].values())*gas_constant*t/v
        candidate_liquid = IAPWS95(T=t, P=all_vapor_pressure/1e6)
        h0, s0 = ideal_properties('H2O', t)
        mu = candidate_liquid.h*1000*mass+offset-t*candidate_liquid.s*1000*mass
        pe = pref*math.exp((mu-h0+t*s0)/(gas_constant*t))
        return p['inventories_mol']['H2O']*gas_constant*t/v-pe

    event_reconstructions = []
    for row in rows:
        if row['kind'] != 'phase_event':
            continue
        ends = [max(phase_criterion(cell['state']) for cell in endpoint['cells'])
                for endpoint in row['bracket_states']]
        expected_wet = [True, False] if row['transition'] == 'liquid_depleted' else [False, True]
        event_reconstructions.append({'scope': row['scope'], 'cell_index': row['cell_index'],
            'transition': row['transition'], 'time_s': row['time_s'],
            'time_bracket_width_s': row['time_bracket_s'][1]-row['time_bracket_s'][0],
            'source_criterion_bracket_pa': ends,
            'criterion_reconstruction_difference_pa': [a-b for a, b in
                zip(ends, row['criterion_bracket_pa'], strict=True)],
            'direct_source_brackets_transition': [(v > 0) for v in ends] == expected_wet})

    def reconstructed_rates(states, boundary, surface):
        """Independent scalar reconstruction of the registered face equations."""
        masses = config['molar_masses_kg_mol']
        transport = config['transfer']
        gas_settings = transport['gas']
        area, dx = config['geometry']['area_m2'], config['geometry']['length_m']/len(states)
        gases = [{'t': p['temperature_k'], 'p': p['pressure_pa'],
                  'x': {k: v/math.fsum(p['amounts_mol'].values()) for k, v in p['amounts_mol'].items()}}
                 for p in states]
        gases.append({'t': boundary['gas_temperature_k'], 'p': boundary['total_pressure_pa'],
                      'x': boundary['mole_fractions']})
        for g in gases:
            mean_mass = math.fsum(g['x'][k]*m for k, m in masses.items())
            g['y'] = {k: g['x'][k]*m/mean_mass for k, m in masses.items()}
        faces = []
        for i, (left, right) in enumerate(zip(gases[:-1], gases[1:], strict=True)):
            dr = transport['external_distance_m'] if i == len(states)-1 else dx/2
            distance, weight = dx/2+dr, dr/(dx/2+dr)
            tf = weight*left['t']+(1-weight)*right['t']
            pf = weight*left['p']+(1-weight)*right['p']
            xf = {k: weight*left['x'][k]+(1-weight)*right['x'][k] for k in masses}
            total = math.fsum(xf.values())
            xf = {k: value/total for k, value in xf.items()}
            mean_mass = math.fsum(xf[k]*m for k, m in masses.items())
            rho = pf*mean_mass/(gas_constant*tf)
            star = {k: -rho*(m/mean_mass)*gas_settings['effective_diffusivities_m2_s'][k]*(
                right['x'][k]-left['x'][k])/distance for k, m in masses.items()}
            total_star = math.fsum(star.values())
            correction_donor = left if total_star < 0 else right
            diffusion = {k: area*(v-total_star*correction_donor['y'][k])/masses[k] for k, v in star.items()}
            velocity = -gas_settings['permeability_m2']*gas_settings['relative_permeability']/gas_settings[
                'viscosity_pa_s']*(right['p']-left['p'])/distance
            donor = left if velocity > 0 else right
            advection = {k: area*rho*donor['y'][k]*velocity/m for k, m in masses.items()}
            heat = (-surface['convective_in_w'] if i == len(states)-1 else
                    transport['conductivity_w_m_k']*area*(left['t']-right['t'])/distance)
            energy = heat+math.fsum(diffusion[k]*ideal_properties(k, tf)[0]+
                advection[k]*ideal_properties(k, donor['t'])[0] for k in masses)
            faces.append({'energy_out_w': energy,
                          'exchange': {'net_mol_s': {k: diffusion[k]+advection[k] for k in masses}}})
        return faces, -surface['radiative_in_w']

    minimum = None
    negative = 0
    face_count = 0
    for row in rows:
        if row['kind'] not in ('step', 'sample'):
            continue
        if row['kind'] == 'step':
            states, boundary = row['midpoint_states'], row['boundary_midpoint']
            faces, radiation = row['rates'], row['surface_radiation_out_w']
        else:
            states, boundary = row['states'], row['boundary']
            faces, radiation = reconstructed_rates(states, boundary, row['surface'])
        temperatures = [p['temperature_k'] for p in states]+[boundary['gas_temperature_k']]
        mus = [chemical_over_temperature(p['temperature_k'], {
            k: n*gas_constant*p['temperature_k']/p['gas_volume_m3'] for k, n in p['amounts_mol'].items()})
            for p in states]
        mus.append(chemical_over_temperature(boundary['gas_temperature_k'], {
            k: y*boundary['total_pressure_pa'] for k, y in boundary['mole_fractions'].items()}))
        for i, face in enumerate(faces):
            entropy = face['energy_out_w']*(1/temperatures[i+1]-1/temperatures[i])
            entropy += math.fsum(j*(mus[i][k]-mus[i+1][k]) for k, j in face['exchange']['net_mol_s'].items())
            if i == len(states)-1:
                entropy += radiation*(1/boundary['radiation_temperature_k']-1/temperatures[i])
            minimum = entropy if minimum is None else min(minimum, entropy)
            negative += entropy < 0
            face_count += 1

    budget = settings['numerical_comparison_budget']
    result = {'trajectory': str(args.trajectory), 'settings': settings,
        'scope': 'conditional formulas; shared EOS; nominal reservoir entropy only',
        'reconstructed_states': reconstructions,
        'phase_events': event_reconstructions,
        'face_entropy': {'sampled_faces': face_count, 'minimum_w_k': minimum, 'negative_count': negative,
            'qualification': 'saved explicit midpoints or implicit observations with reconstructed face equations; not discrete total-entropy or global stability proof'},
        'max_abs_energy_residual_j': max(abs(p['total_energy_residual_j']) for p in reconstructions),
        'max_abs_solid_energy_difference_j': max(abs(p['solid_energy_difference_j']) for p in reconstructions),
        'within_reconstruction_budget': {
            'energy': all(abs(p['total_energy_residual_j'])<=budget['cell_energy_j'] for p in reconstructions),
            'pressure': all(abs(p['pressure_residual_pa'])<=budget['pressure_pa'] for p in reconstructions),
            'phase': all(abs(p['vapor_minus_liquid_chemical_potential_j_mol'])<=budget['chemical_potential_j_mol']
                if p['phase_condition'] == 'equality' else p['vapor_minus_liquid_chemical_potential_j_mol']<=
                budget['chemical_potential_j_mol'] for p in reconstructions)},
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'reconstructed_states'}, indent=2))


if __name__ == '__main__':
    main()
