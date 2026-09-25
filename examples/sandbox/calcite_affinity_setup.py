"""Build the bounded same-USGS-source standard reaction, without legacy loaders."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_reaction_affinity import RecordedThermalPhase, RecordedSingleGasReaction


def build(root, settings):
    source=json.loads((root/settings['source_file']).read_text())
    facts=json.loads((root/source['reference_facts_file']).read_text())
    tref=float(facts['reference_state']['temperature_k']);phases={}
    domain=tuple(map(float,facts['reaction']['common_selected_temperature_domain_k']))
    for phase in facts['species']:
        name=phase['id'];c=phase['cp']['coefficients_nominal']
        phases[name]=RecordedThermalPhase(tuple(float(c[k]) for k in ('A1','A2','A3','A4','A5')),tref,
            float(phase['reference_298']['hf_kj_mol'])*settings['joules_per_kilojoule'],
            float(source['phases'][name]['entropy_reference_j_mol_k']),domain)
    reaction=RecordedSingleGasReaction(phases,{k:float(v) for k,v in facts['reaction']['stoichiometry_mol_per_mol_extent'].items()},
        settings['gas_phase'],float(facts['reference_state']['gas_constant_j_mol_k']),
        float(facts['reference_state']['pressure_pa']),settings['total_pressure_pa'])
    return reaction,source,facts
