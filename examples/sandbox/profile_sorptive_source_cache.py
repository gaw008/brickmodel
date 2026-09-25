"""Measure exact T/P reuse on recorded source-state and surface reconstructions."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sorptive_column_setup import cell_parameters
from sorptive_source_formulas import source_for_column


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent;settings = json.loads(args.parameters.read_text())
    audit = json.loads((root/settings['source_audit_parameters']).read_text());selected = []
    with (root/settings['trajectory']).open() as stream:
        header = json.loads(next(stream))
        for line in stream:
            row = json.loads(line)
            if row['kind'] in ('initial','sample') and row['time_s'] in settings['times_s']:
                selected.append({'time_s':row['time_s'],'point':row['states'][-1]})
    records = []
    for tolerance in settings['root_coordinate_tolerances']:
        single = deepcopy(header);single['parameters'] = cell_parameters(single['parameters'],single['cell_count'])
        single['parameters']['surface_equilibrium']['coordinate_tolerance'] = tolerance
        plain = source_for_column(single,audit['source_quadrature'])
        cached = source_for_column(single,{**audit['source_quadrature'],'liquid_cache_entries':settings['liquid_cache_entries']})
        route_results = []
        for source in (plain,cached):
            started = time.monotonic();values = []
            for point in selected:
                values.append({'time_s':point['time_s'],'source_state':source.reconstruct(point['point']),
                    'surface':source.fluxes(point['time_s'],point['point'])})
            route_results.append({'elapsed_s':time.monotonic()-started,'values':values})
        records.append({'root_coordinate_tolerance':tolerance,'uncached':route_results[0],'cached':route_results[1],
            'all_recorded_fields_exactly_equal':route_results[0]['values']==route_results[1]['values'],
            'liquid_cache_info':cached.liquid_at.cache_info()._asdict()})
    result = {'settings':settings,'recorded_times_s':[p['time_s'] for p in selected],'records':records,
        'scope':'Exact numerical source reuse on listed physical observations. Timings include this machine load; no interpolation, model change or universal speedup claim.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps([{'tolerance':r['root_coordinate_tolerance'],'exactly_equal':r['all_recorded_fields_exactly_equal'],
        'uncached_s':r['uncached']['elapsed_s'],'cached_s':r['cached']['elapsed_s'],'cache':r['liquid_cache_info']} for r in records]))


if __name__=='__main__':
    main()
