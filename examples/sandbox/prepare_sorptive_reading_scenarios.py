"""Explicit endpoint scenarios from existing digitization intervals.

Nominal source facts stay unchanged. Each derived table labels its scenario
and retains the nominal reading beside the selected interval endpoint.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    nominal = json.loads((root/settings['nominal_parameters_file']).read_text())
    original = json.loads((root/settings['source_facts_file']).read_text())
    for scenario in settings['scenarios']:
        name = scenario['name']
        facts = deepcopy(original)
        facts['scenario_definition'] = {**scenario, 'nominal_source_file': settings['source_facts_file'],
                                        'classification': 'declared_digitization_endpoint_scenario_not_new_observation'}
        for figure, key in [(1, 'activity'), (2, 'heat')]:
            levels = nominal['source_construction'][key+'_levels_kg_kg']
            for row in facts['observations']:
                if row['figure'] == figure and float(row['requested_moisture_kg_water_per_kg_dry_matter']) in levels:
                    row['nominal_reading'] = row['value']
                    row['nominal_status'] = row['status']
                    row['value'] = row['digitization_bounds'][scenario[key+'_endpoint']]
                    row['status'] = 'declared_digitization_endpoint_scenario'
                    row['scenario_definition'] = facts['scenario_definition']
        fact_path = Path(settings['output_directory'])/(name+'-facts.json')
        write(root/fact_path, facts)
        config = deepcopy(nominal)
        config['classification'] = 'conditional_reading_scenario_with_virtual_gas_connection_not_brick'
        config['source_files']['curves'] = str(fact_path)
        config['sorption_record_file'] = str(Path(settings['output_directory'])/(name+'-sorption.json'))
        config['reading_scenario'] = facts['scenario_definition']
        config['reading_scenario']['scope'] = settings['scope']
        write(root/(settings['output_parameters_prefix']+name+'.json'), config)
        print(json.dumps({'scenario': name, 'facts': str(fact_path), 'sorption_record': config['sorption_record_file']}))


if __name__ == '__main__':
    main()
