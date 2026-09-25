"""Construct the explicitly selected USGS water-gas-shift inventory."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.recorded_reaction_affinity import RecordedThermalPhase
from sludge_sandbox.restricted_water_gas_shift import RestrictedWaterGasShift


def build(root, parameters):
    sources = [json.loads((root / path).read_text()) for path in parameters['sources']]
    data = {name: values for source in sources for name, values in source['phases'].items()
            if name in parameters['species']}
    phases = {name: RecordedThermalPhase(tuple(map(float, values['cp_coefficient_strings'])),
              parameters['reference_temperature_k'], float(values['reference_enthalpy_j_mol']),
              float(values['reference_entropy_j_mol_k']), tuple(parameters['temperature_domain_k']))
              for name, values in data.items()}
    return RestrictedWaterGasShift(phases, parameters['stoichiometry'],
                                  parameters['gas_constant_j_mol_k'], parameters['standard_pressure_pa']), sources
