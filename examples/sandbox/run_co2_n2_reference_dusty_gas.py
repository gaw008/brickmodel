"""Closed CO2/N2 pore column with explicitly selected reference correlations."""
import argparse
import json
from pathlib import Path

from run_dusty_gas_isothermal_column import record_column
from sludge_sandbox.co2_dilute_viscosity import CarbonDioxideDiluteViscosity
from sludge_sandbox.co2_n2_diffusion import CarbonDioxideNitrogenDiffusion
from sludge_sandbox.lemmon2004_dilute_transport import dilute_transport


def reference_properties(p, root):
    sources = {name: json.loads((root/path).read_text()) for name, path in p['property_sources'].items()}
    c = sources['molecular_constants']['constants']
    gas_constant = float(c['boltzmann_j_k'])*float(c['avogadro_mol_inverse'])
    masses = [float(sources['molecular_constants']['species'][name]['molar_mass_g_mol'])*float(c['gram_kg'])
        for name in p['species_order']]
    temperature = p['temperature_k']
    viscosities = {
        'CO2': CarbonDioxideDiluteViscosity(sources['CO2_viscosity']).viscosity_pa_s(temperature),
        'N2': dilute_transport(temperature, 'N2', sources['N2_viscosity'])['viscosity_pa_s']}
    diffusion = CarbonDioxideNitrogenDiffusion(sources['CO2_N2_diffusion'])
    pressure = p['binary_property_reference_pressure_pa']
    product = pressure*diffusion.diffusivity_m2_s(temperature, pressure)
    return {'property_source_settings': sources, 'gas_constant_j_mol_k': gas_constant,
        'molar_masses_kg_mol': masses,
        'pure_viscosities_pa_s': [viscosities[name] for name in p['species_order']],
        'diffusivity_pressure_products_pa_m2_s': [[0.0, product], [product, 0.0]],
        'property_scope': p['property_scope']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--mesh', required=True)
    parser.add_argument('--tolerance', choices=['base', 'refined'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    record_column(p, reference_properties(p, args.parameters.resolve().parent), args)


if __name__ == '__main__':
    main()
