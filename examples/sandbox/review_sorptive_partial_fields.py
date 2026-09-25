"""Recorded-state physical field comparison and quadrature cost attribution."""
import argparse
from copy import deepcopy
import cProfile
import json
from pathlib import Path
import pstats
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sorptive_column_setup import cell_parameters
from sorptive_source_formulas import EvaporatingSurfaceSource


class IntegratedPartialSource(EvaporatingSurfaceSource):
    """Retain the previous H/S quadrature route for the same partial mu."""
    def excess_partial_chemical_potential(self,t,w):
        return self.excess(t,w)[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent
    settings=json.loads(args.parameters.read_text())
    audit=json.loads((root/settings['source_audit_parameters']).read_text())
    selected=[]
    with (root/settings['trajectory']).open() as stream:
        header=json.loads(next(stream))
        for line in stream:
            row=json.loads(line)
            if row['kind'] in ('initial','sample') and row['time_s'] in settings['times_s']:
                selected.append({'time_s':row['time_s'],'states':row['states']})
    records=[]
    for tolerance in settings['root_coordinate_tolerances']:
        single=deepcopy(header)
        single['parameters']=cell_parameters(single['parameters'],single['cell_count'])
        single['parameters']['surface_equilibrium']['coordinate_tolerance']=tolerance
        routes=[]
        for source_type in (IntegratedPartialSource,EvaporatingSurfaceSource):
            source=source_type(single,audit['source_quadrature'])
            values=[];profiler=cProfile.Profile();started=time.monotonic()
            profiler.enable()
            for row in selected:
                values.append({'time_s':row['time_s'],
                    'states':{str(i):source.reconstruct(row['states'][i]) for i in settings['cell_indices']},
                    'internal_faces':{str(i):source.between_states(row['states'][i],row['states'][i+1],
                        header['geometry']['internal_transfer']) for i in settings['internal_face_left_indices']},
                    'surface':source.fluxes(row['time_s'],row['states'][-1])})
            profiler.disable();elapsed=time.monotonic()-started
            stats=pstats.Stats(profiler).stats
            functions=[{'module':Path(key[0]).name,'line':key[1],'function':key[2],
                'primitive_calls':value[0],'total_calls':value[1],'self_time_s':value[2],
                'cumulative_time_s':value[3]} for key,value in stats.items()]
            functions.sort(key=lambda row:row['cumulative_time_s'],reverse=True)
            quad=[r for r in functions if r['module']=='_quadpack_py.py' and r['function']=='quad']
            routes.append({'route':source_type.__name__,'elapsed_profiled_s':elapsed,'values':values,
                'quad_profile':quad,'top_functions':functions[:settings['profile_top_functions']],
                'liquid_cache_info':source.liquid_at.cache_info()._asdict()})
        record={'root_coordinate_tolerance':tolerance,'routes':routes,
            'all_physical_fields_exactly_equal':routes[0]['values']==routes[1]['values']}
        records.append(record)
        print(json.dumps({'root_tolerance':tolerance,'exact':record['all_physical_fields_exactly_equal'],
            'routes':[{k:r[k] for k in ['route','elapsed_profiled_s','quad_profile']} for r in routes]}),flush=True)
    result={'settings':settings,'recorded_times_s':[r['time_s'] for r in selected],'records':records,
        'all_selected_times_present':[r['time_s'] for r in selected]==settings['times_s'],
        'all_physical_fields_exactly_equal':all(r['all_physical_fields_exactly_equal'] for r in records),
        'scope':'Recorded source states, faces and surface roots only. Timings include profiling and concurrent machine load; no universal speedup or material-accuracy inference.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':
    main()
