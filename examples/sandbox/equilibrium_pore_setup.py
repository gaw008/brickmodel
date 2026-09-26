"""Connect the independently qualified gas equilibrium to pore mechanics."""
import json

from water_gas_shift_setup import build as build_equilibrium
from sludge_sandbox.equilibrium_spherical_pore import EquilibriumSphericalPore


def build(root, parameters):
    equilibrium = json.loads((root/parameters['equilibrium_parameters']).read_text())
    gas, sources = build_equilibrium(root, equilibrium)
    mechanical = json.loads((root/parameters['mechanical_source']).read_text())
    return EquilibriumSphericalPore(parameters['model'], gas, parameters['gas_feed_fractions']), {
        'mechanical_source': mechanical, 'thermal_sources': sources,
        'equilibrium_parameters': equilibrium}
