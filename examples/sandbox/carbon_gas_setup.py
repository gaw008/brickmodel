"""Construct the explicitly selected source standard-pressure C/O mixture."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_reaction_affinity import RecordedThermalPhase
from sludge_sandbox.recorded_carbon_gas_equilibrium import RecordedCarbonGasEquilibrium


def build(root,settings):
    source=json.loads((root/settings['source_file']).read_text())
    phases={name:RecordedThermalPhase(tuple(map(float,p['cp_coefficient_strings'])),
        float(source['reference_temperature_k']),float(p['reference_enthalpy_j_mol']),float(p['reference_entropy_j_mol_k']),
        tuple(settings['temperature_domain_k'])) for name,p in source['phases'].items()}
    return RecordedCarbonGasEquilibrium(phases,float(source['gas_constant_j_mol_k']),float(source['reference_pressure_pa']),settings['equilibrium_numerics']),source
