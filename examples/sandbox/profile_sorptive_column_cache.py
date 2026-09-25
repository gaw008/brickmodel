"""Measure exact liquid-property caching on complete recorded column observations."""
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
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;p=json.loads(args.parameters.read_text());selected=[]
    with (root/p['trajectory']).open() as stream:
        header=json.loads(next(stream))
        for line in stream:
            row=json.loads(line)
            if row['kind'] in ('initial','sample') and row['time_s'] in p['times_s']:
                selected.append({'time_s':row['time_s'],'states':row['states']})
                if len(selected)==len(p['times_s']):break
    audit=json.loads((root/p['source_audit_parameters']).read_text());single=deepcopy(header)
    single['parameters']=cell_parameters(single['parameters'],single['cell_count'])
    single['parameters']['transfer']=header['geometry']['boundary_transfer'];routes=[]
    for capacity in p['liquid_cache_capacities']:
        source=source_for_column(single,{**audit['source_quadrature'],'liquid_cache_entries':capacity});observations=[]
        for row in selected:
            before=source.liquid_at.cache_info()._asdict();started=time.monotonic();states=row['states']
            values={'states':[source.reconstruct(state) for state in states],
                    'internal_faces':[source.between_states(a,b,header['geometry']['internal_transfer']) for a,b in zip(states[:-1],states[1:],strict=True)],
                    'surface':source.fluxes(row['time_s'],states[-1])}
            observations.append({'time_s':row['time_s'],'elapsed_s':time.monotonic()-started,'cache_before':before,
                                 'cache_after':source.liquid_at.cache_info()._asdict(),'values':values})
        routes.append({'capacity':capacity,'observations':observations})
        print(json.dumps({'capacity':capacity,'observations':[{k:v for k,v in row.items() if k!='values'} for row in observations]}),flush=True)
    equal=all(a['values']==b['values'] for a,b in zip(routes[0]['observations'],routes[1]['observations'],strict=True))
    result={'settings':p,'recorded_times_s':[r['time_s'] for r in selected],'all_requested_times_present':[r['time_s'] for r in selected]==p['times_s'],
            'routes':routes,'all_physical_fields_exactly_equal':equal,'scope':'Exact source-output equivalence and workload timing only. No trajectory qualification or extrapolated speedup.',
            'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
