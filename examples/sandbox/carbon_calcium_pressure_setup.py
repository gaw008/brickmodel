"""Load common-source phases and explicitly approximate solid volume EOS."""
import json

from carbon_calcium_setup import build as build_standard
from sludge_sandbox.recorded_carbon_calcium_pressure import RecordedCarbonCalciumPressure


def build(root, settings):
    equilibrium = json.loads((root / settings['standard_equilibrium_parameters']).read_text())
    standard, sources = build_standard(root, equilibrium)
    volume_source = json.loads((root / settings['solid_volume_source']).read_text())
    calcium_volumes = json.loads((root / volume_source['calcium_volume_source']).read_text())
    volumes = {name: float(row['volume_cm3_mol']) * calcium_volumes['cubic_metres_per_cubic_centimetre']
               for name, row in calcium_volumes['phases'].items()}
    volumes['C'] = float(volume_source['graphite']['volume_cm3_mol']) * volume_source['cubic_metres_per_cubic_centimetre']
    parameters = {**equilibrium, **settings}
    model = RecordedCarbonCalciumPressure(standard.phases, standard.r, standard.p0, volumes, parameters)
    return model, {**sources, 'solid_volume_source': volume_source, 'calcium_volume_source': calcium_volumes}, standard
