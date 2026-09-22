"""Construct the explicitly recorded sorptive single-cell model."""
import json
from copy import deepcopy

from sludge_sandbox.equilibrium_sorptive_cell import EquilibriumSorptiveCell, EquilibriumSourceSorptiveCell
from sludge_sandbox.equilibrium_water_cell import EquilibriumWaterCell
from sludge_sandbox.gibbs_water_table import GibbsWaterTable
from sludge_sandbox.recorded_sorption import RecordedLowMoisture, RecordedSourceSorption
from sludge_sandbox.recorded_water import RecordedWaterProperties
from sludge_sandbox.thermochemistry import load_thermochemistry
from sludge_sandbox.water_properties import NumericalLimits


def build_sorptive_cell(root, config):
    direct = RecordedWaterProperties(root/config['water_facts_file'], NumericalLimits(**config['numerics']['water']))
    thermo = load_thermochemistry(root/config['thermochemistry_file'])
    representation = config['liquid_evaluation']
    water = {'direct': lambda: direct,
             'gibbs_table': lambda: GibbsWaterTable(direct, json.loads((root/representation['table_file']).read_text()))}[representation['method']]()
    fluid = EquilibriumWaterCell(water, thermo, config['molar_masses_kg_mol'],
        config['cell']['available_fluid_volume_m3'], config['reference_pressure_pa'], config['numerics'])
    excess_type, cell_type = {
        'sorptive_common_gas_cell_v1':(RecordedLowMoisture, EquilibriumSorptiveCell),
        'source_sorptive_common_gas_cell_v1':(RecordedSourceSorption, EquilibriumSourceSorptiveCell),
        'source_sorptive_common_gas_column_v1':(RecordedSourceSorption, EquilibriumSourceSorptiveCell)}[config['schema']]
    excess = excess_type(json.loads((root/config['sorption_record_file']).read_text()))
    return cell_type(fluid, excess, config['cell']['dry_mass_kg'],
        config['cell']['dry_reference_temperature_k'], config['numerics']['warm_temperature_inverse'])


def restore_sorptive_cell(header, directory):
    config = deepcopy(header['parameters'])
    records = {'water_facts_file': header['water_source']['facts'],
               'thermochemistry_file': header['thermochemistry'],
               'sorption_record_file': header['sorption_source']}
    for key, record in records.items():
        name = key+'.json'
        (directory/name).write_text(json.dumps(record,allow_nan=False))
        config[key] = name
    if config['liquid_evaluation']['method'] == 'gibbs_table':
        name = 'liquid_representation.json'
        (directory/name).write_text(json.dumps(header['water_source']['liquid_representation'],allow_nan=False))
        config['liquid_evaluation']['table_file'] = name
    return build_sorptive_cell(directory,config)
