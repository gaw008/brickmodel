"""Independent five-unknown surface balance using source integrals and mpmath."""
import mpmath as mp

from carbon_calcium_radiation_reference import RadiationSource
from review_carbon_calcium_program import independent_thermal


def gas_state(source, temperature, partial):
    t = mp.mpf(temperature)
    pressure = mp.fsum(partial.values())
    fractions = {k: value / pressure for k, value in partial.items()}
    thermal = independent_thermal(source, t, pressure, fractions)
    return {'temperature': t, 'pressure': pressure, 'partial': partial,
            'h': {k: v['h'] for k, v in thermal.items()},
            'mu': {k: v['mu'] for k, v in thermal.items()}}


def face(left, right, parameters):
    tl, tr = left['temperature'], right['temperature']
    names = parameters['gas_order']
    mean_h = {k: (left['h'][k] + right['h'][k]) / 2 for k in names}
    force = {k: left['mu'][k]/tl - right['mu'][k]/tr + mean_h[k]*(1/tr - 1/tl) for k in names}
    flow = {k: mp.mpf(parameters['gas_mobilities_mol2_k_j_s'][k]) * force[k] for k in names}
    conductance = mp.mpf(parameters['heat_conductance_w_k'])
    energy = conductance*(tl-tr) + mp.fsum(mean_h[k]*flow[k] for k in names)
    sl = (-energy + mp.fsum(left['mu'][k]*flow[k] for k in names)) / tl
    sr = (energy - mp.fsum(right['mu'][k]*flow[k] for k in names)) / tr
    production = conductance*(tl-tr)**2/(tl*tr) + mp.fsum(
        mp.mpf(parameters['gas_mobilities_mol2_k_j_s'][k])*force[k]**2 for k in names)
    return {'flow': flow, 'energy': energy, 'entropy_left': sl,
            'entropy_right': sr, 'production': production}


def solve(source, bulk, reservoir, interior, exterior, radiation, settings, initial):
    policy = settings['independent_review']
    names = exterior['gas_order']
    bath = gas_state(source, reservoir['temperature_k'],
        {k: mp.mpf(reservoir['pressure_pa'])*mp.mpf(reservoir['mole_fractions'][k]) for k in names})
    cell = gas_state(source, bulk['temperature_k'],
        {k: mp.mpf(bulk['partial_pressures_pa'][k]) for k in names})
    rad_source = RadiationSource(radiation)
    coefficient = mp.mpf(radiation['emissivity'])*mp.mpf(radiation['area_m2'])*mp.mpf(rad_source.sigma_decimal)
    tr = mp.mpf(radiation['reservoir_temperature_k'])

    def evaluate(temperature, *log_partial):
        partial = {k: mp.mpf(source.p0)*mp.exp(value) for k, value in zip(names, log_partial, strict=True)}
        surface = gas_state(source, temperature, partial)
        outer, inner = face(bath, surface, exterior), face(surface, cell, interior)
        heat = coefficient*(tr**4 - temperature**4)
        balances = [outer['flow'][k] - inner['flow'][k] for k in names]
        balances.append(outer['energy'] + heat - inner['energy'])
        return surface, outer, inner, heat, balances

    def residual(temperature, *log_partial):
        *_, balances = evaluate(temperature, *log_partial)
        return tuple(value / mp.mpf(policy['species_residual_scale_mol_s']) for value in balances[:-1]) + (
            balances[-1] / mp.mpf(policy['energy_residual_scale_w']),)

    guess = [mp.mpf(initial['temperature_k'])] + [mp.log(mp.mpf(initial['partial_pressures_pa'][k])/source.p0) for k in names]
    solution = mp.findroot(residual, guess, tol=mp.mpf(policy['root_tolerance']),
                           maxsteps=policy['maximum_root_iterations'])
    surface, outer, inner, heat, balances = evaluate(*solution)
    ts = surface['temperature']
    surface_entropy = outer['entropy_right'] + inner['entropy_left'] + heat/ts
    rad_production = heat*(1/ts-1/tr)
    production = outer['production'] + inner['production'] + rad_production
    external_entropy = inner['entropy_right'] + outer['entropy_left'] - heat/tr
    return {'surface': surface, 'outer': outer, 'inner': inner, 'radiation_energy': heat,
            'balances': balances, 'surface_entropy': surface_entropy, 'production': production,
            'body_plus_reservoir_entropy': external_entropy,
            'entropy_identity': external_entropy + surface_entropy - production,
            'scaled_root_residual': max(abs(v) for v in residual(*solution))}


def uniqueness_certificate(source, bulk, reservoir, interior, exterior, radiation, settings):
    """A uniform upper derivative bound and independently evaluated end signs."""
    names = exterior['gas_order']
    tb, tc = mp.mpf(reservoir['temperature_k']), mp.mpf(bulk['temperature_k'])
    lo, li = exterior['gas_mobilities_mol2_k_j_s'], interior['gas_mobilities_mol2_k_j_s']
    bath = gas_state(source, tb, {k: mp.mpf(reservoir['pressure_pa'])*mp.mpf(reservoir['mole_fractions'][k]) for k in names})
    cell = gas_state(source, tc, {k: mp.mpf(bulk['partial_pressures_pa'][k]) for k in names})
    tmin, tmax = map(mp.mpf, settings['surface_temperature_domain_k'])
    bound = -mp.mpf(exterior['heat_conductance_w_k']) - mp.mpf(interior['heat_conductance_w_k'])
    cp_bounds = {}
    for k in names:
        a,b,c,d,e = map(mp.mpf, source.thermal[k][0])
        cp_bounds[k] = abs(a)+abs(b)*tmax+abs(c)/tmin**2+abs(d)/mp.sqrt(tmin)+abs(e)*tmax**2
        mobility = mp.mpf(lo[k])*mp.mpf(li[k])/(mp.mpf(lo[k])+mp.mpf(li[k]))
        bound += mobility*abs(bath['h'][k]-cell['h'][k])*cp_bounds[k]*abs(1/tc-1/tb)/4
    rad = RadiationSource(radiation)
    coefficient = mp.mpf(radiation['emissivity'])*mp.mpf(radiation['area_m2'])*mp.mpf(rad.sigma_decimal)

    def energy(temperature):
        h = independent_thermal(source, temperature, mp.mpf(source.p0), {k: mp.mpf(1) for k in names})
        flows = {}
        for k in names:
            a = bath['mu'][k]/tb+(bath['h'][k]+h[k]['h'])/2*(1/temperature-1/tb)
            b = cell['mu'][k]/tc-(cell['h'][k]+h[k]['h'])/2*(1/tc-1/temperature)
            flows[k] = mp.mpf(lo[k])*mp.mpf(li[k])/(mp.mpf(lo[k])+mp.mpf(li[k]))*(a-b)
        return (mp.mpf(exterior['heat_conductance_w_k'])*(tb-temperature)
            -mp.mpf(interior['heat_conductance_w_k'])*(temperature-tc)
            +coefficient*(mp.mpf(radiation['reservoir_temperature_k'])**4-temperature**4)
            +mp.fsum((bath['h'][k]-cell['h'][k])/2*flows[k] for k in names))

    endpoints = [energy(tmin), energy(tmax)]
    return {'derivative_upper_bound_w_k': str(bound), 'cp_absolute_bounds_j_mol_k': {k: str(v) for k,v in cp_bounds.items()},
            'energy_endpoint_values_w': list(map(str,endpoints)),
            'strictly_decreasing_on_entire_source_domain': bool(bound < 0),
            'opposite_endpoint_signs': bool(endpoints[0] > 0 and endpoints[1] < 0)}
