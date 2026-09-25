"""Freeze an explicitly selected end-slope continuation; no new source nodes."""
import argparse
from copy import deepcopy
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.parameters.read_text())
    record = deepcopy(json.loads((args.parameters.resolve().parent/config['continuation']['source_record_file']).read_text()))
    record['schema'] = 'recorded_sorption_free_water_v1'
    record['continuation'] = config['continuation']
    record['model_domain']['moisture_kg_kg'] = config['continuation']['total_moisture_domain_kg_kg']
    record['assumptions'] += [
        'For sorbed W>.8 explicitly continue the final m0 and b0 slopes; material error unknown.',
        'Free/sorbed water minimizes the same excess potential at fixed total condensed W.',
        'Coexisting phases share the pure liquid volume/reference; no capillarity or dissolved species.',
        'Published approximate transition near .9 is contextual evidence, not a calibrated saturation law.']
    with args.output.open('x') as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
