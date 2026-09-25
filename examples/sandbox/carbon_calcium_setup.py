"""Combine the two already recorded, common-USGS standard-state phase sets."""
import json

from carbon_gas_setup import build as build_carbon
from calcite_affinity_setup import build as build_calcite
from sludge_sandbox.recorded_carbon_calcium_equilibrium import RecordedCarbonCalciumEquilibrium


def build(root,settings):
    carbon_settings=json.loads((root/settings['carbon_parameters']).read_text());carbon,carbon_source=build_carbon(root,carbon_settings)
    calcite_settings=json.loads((root/settings['calcite_affinity_parameters']).read_text());reaction,calcite_source,facts=build_calcite(root,calcite_settings)
    model=RecordedCarbonCalciumEquilibrium(carbon,reaction.phases['calcite'],reaction.phases['lime'],settings)
    return model,{'carbon_source':carbon_source,'calcite_source':calcite_source,'calcite_facts':facts,
        'carbon_parameters':carbon_settings,'calcite_parameters':calcite_settings}
