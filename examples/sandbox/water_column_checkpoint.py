"""Explicit checkpoint input and local source-snapshot restoration.

Only complete published checkpoints are restart points. A resumed integration
starts a fresh BDF history from conserved N/U and cumulative exterior exchange.
It does not claim bit-identical future adaptive steps. No digest is used.
"""
from copy import deepcopy
import json


def load_checkpoint(path):
    lines = path.read_text().splitlines(keepends=True)
    rows = [json.loads(line) for line in lines]
    index = next(i for i in range(len(rows)-1, -1, -1) if rows[i]['kind'] == 'checkpoint')
    checkpoint = rows[index]
    checkpoint['phase_events'] = [{k: v for k, v in row.items() if k not in (
        'kind', 'states', 'bracket_states', 'boundary', 'surface', 'exterior_integrals')}
        for row in rows[:index+1] if row['kind'] == 'phase_event']
    return rows[0], rows[1], checkpoint, lines[:index+1]


def restore_sources(header, directory):
    """Recreate exact recorded JSON values locally, without reading new sources."""
    config = deepcopy(header['parameters'])
    for field, name, value in (
        ('water_facts_file', 'water.json', header['water_source']['facts']),
        ('thermochemistry_file', 'gases.json', header['thermochemistry']),
        ('solid_facts_file', 'solid.json', header['solid_source_facts']),
    ):
        (directory/name).write_text(json.dumps(value, allow_nan=False))
        config[field] = name
    if config['liquid_evaluation']['method'] == 'gibbs_table':
        (directory/'liquid.json').write_text(json.dumps(header['water_source']['liquid_representation'], allow_nan=False))
        config['liquid_evaluation']['table_file'] = 'liquid.json'
    return config
