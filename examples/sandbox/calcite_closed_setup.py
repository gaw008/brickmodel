"""Build the recorded reaction and its same-source inert nitrogen carrier."""
import json

from calcite_affinity_setup import build, from_records
from sludge_sandbox.recorded_reaction_affinity import RecordedThermalPhase


def nitrogen_from_record(source):
    return RecordedThermalPhase(
        tuple(0. if v is None else float(v) for v in source['cp_coefficient_strings']),
        float(source['reference_temperature_k']),float(source['reference_enthalpy_j_mol']),
        float(source['reference_entropy_j_mol_k']),tuple(source['selected_temperature_domain_k']))


def build_closed(root, config):
    affinity=json.loads((root/config['affinity_parameters']).read_text())
    reaction,source,facts=build(root,affinity)
    nitrogen=json.loads((root/config['nitrogen_source_file']).read_text())
    return reaction,nitrogen_from_record(nitrogen),affinity,source,facts,nitrogen
