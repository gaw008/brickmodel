"""Reconstruct each property source before whole-trajectory DGM balances."""
import argparse
import json
from pathlib import Path

import mpmath as mp

from audit_dusty_gas_four_species_column import audit
from audit_dusty_gas_open_pure_column import time_comparison


def property_review(header):
    p, sources = header['settings'], header['property_source_settings']
    mp.mp.dps = p['verification']['source_property_decimal_precision']
    t = mp.mpf(p['temperature_k'])
    c = sources['molecular_constants']['constants']
    r = mp.mpf(c['boltzmann_j_k'])*mp.mpf(c['avogadro_mol_inverse'])
    co2 = sources['CO2_viscosity']
    a = list(map(mp.mpf, co2['coefficients']))
    theta = t/mp.mpf(co2['kelvin_scale'])
    denominator = (a[0]+a[1]*mp.root(theta,6)+a[2]*mp.exp(a[3]*mp.root(theta,3))
        +(a[4]+a[5]*mp.root(theta,3))/mp.exp(mp.root(theta,3))+a[6]*mp.sqrt(theta))
    eta_co2 = mp.mpf(co2['millipascal_to_pascal'])*mp.mpf(co2['experimental_scaling_factor'])*mp.sqrt(theta)/denominator
    nitrogen = sources['N2_viscosity']; n = nitrogen['species']['N2']
    reduced = mp.log(t/mp.mpf(n['well_depth_over_kb_k']))
    omega = mp.exp(mp.fsum(mp.mpf(b)*reduced**i for i,b in enumerate(nitrogen['collision_log_coefficients'])))
    eta_n2 = (mp.mpf(nitrogen['unit_conversion']['micro_pa_s_to_pa_s'])*mp.mpf(nitrogen['viscosity_prefactor'])
        *mp.sqrt(mp.mpf(n['molar_mass_g_mol'])*t)/(mp.mpf(n['diameter_nm'])**2*omega))
    diffusion = sources['CO2_N2_diffusion']; d = diffusion['coefficients']; dc = diffusion['constants']
    theta = t/mp.mpf(dc['kelvin_scale'])
    denominator = (mp.mpf(d['constant'])+mp.mpf(d['inverse_sixth_power'])/mp.root(theta,6)
        +mp.mpf(d['sixth_power_exponential'])*mp.root(theta,6)*mp.exp(-mp.root(theta,3)))
    diffusion_r = mp.mpf(dc['boltzmann_j_k'])*mp.mpf(dc['avogadro_mol_inverse'])
    product = mp.mpf(dc['rho_diffusivity_scale_mol_m_s'])*mp.sqrt(theta)/denominator*diffusion_r*t
    source_values = {'gas_constant': r, 'CO2_viscosity': eta_co2, 'N2_viscosity': eta_n2,
        'CO2_N2_diffusion_pressure_product': product}
    observed = {'gas_constant': header['gas_constant_j_mol_k'],
        'CO2_N2_diffusion_pressure_product': header['diffusivity_pressure_products_pa_m2_s'][0][1]}
    for i, name in enumerate(p['species_order']):
        observed[name+'_viscosity'] = header['pure_viscosities_pa_s'][i]
        observed[name+'_molar_mass'] = header['molar_masses_kg_mol'][i]
        source_values[name+'_molar_mass'] = mp.mpf(sources['molecular_constants']['species'][name]['molar_mass_g_mol'])*mp.mpf(c['gram_kg'])
    errors = {name: float(abs(mp.mpf(observed[name])/value-1)) for name,value in source_values.items()}
    limit = p['verification']['source_property_relative_budget']
    return {'source_values_decimal': {k:str(v) for k,v in source_values.items()},
        'relative_errors': errors, 'budget': limit, 'within_budget': all(v<=limit for v in errors.values()),
        'scope': 'Independent source expressions evaluated from recorded parameter coefficients; gas diffusivity retains dilute equimolar approximation and Wilke mixture viscosity remains approximate.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    reviews, rows, properties = {}, {}, {}
    for name,path in p['trajectories'].items():
        reviews[name],rows[name] = audit(root/path)
        properties[name] = property_review(rows[name][0])
    time = time_comparison(rows['base'], rows['refined'])
    result = {'settings':p, 'property_reviews':properties, 'trajectory_reviews':reviews, 'time_comparison':time,
        'all_requested_budgets_met':all(r['all_requested_budgets_met'] for r in reviews.values())
            and all(r['within_budget'] for r in properties.values()) and time['within_budget'],
        'scope':'Selected source correlations, independent original DGM face equations, full local/global inventories and entropy, union BDF-node time comparison. Spatial qualification is separate.',
        'material_qualified':False, 'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_budgets_met':result['all_requested_budgets_met'],'time_comparison':time}))


if __name__ == '__main__':
    main()
