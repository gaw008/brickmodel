"""Build the explicitly selected gas phase and virtual pore material."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_reaction_affinity import RecordedThermalPhase
from sludge_sandbox.thermal_spherical_pore import ThermalSphericalPore


def build(root, parameters):
    sources = {key: json.loads((root/parameters[key]).read_text())
               for key in ['mechanical_source', 'thermal_source']}
    phase = sources['thermal_source']['phases'][parameters['gas_species']]
    gas = RecordedThermalPhase(tuple(map(float, phase['cp_coefficient_strings'])),
        parameters['model']['reference_temperature_k'], float(phase['reference_enthalpy_j_mol']),
        float(phase['reference_entropy_j_mol_k']), tuple(parameters['temperature_domain_k']))
    return ThermalSphericalPore(parameters['model'], gas), sources
