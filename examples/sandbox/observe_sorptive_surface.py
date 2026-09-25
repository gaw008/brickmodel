"""Reconstruct fixed-position surface observables from saved cell samples."""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.gas_transport import ideal_gas_state,ideal_gas_reservoir
from sorptive_column_setup import restore_column


def observe(path):
    rows=[]
    with path.open() as stream,TemporaryDirectory(prefix='sorptive-surface-observe-') as directory:
        header=json.loads(next(stream));model=restore_column(header,Path(directory));config=header['parameters']
        gas_inputs={'molar_masses_kg_mol':config['molar_masses_kg_mol'],
                    'gas_constant_j_mol_k':model.host.fluid.thermochemistry.gas_constant_j_mol_k}
        for line in stream:
            item=json.loads(line);terminal=item
            if item['kind'] not in ('initial','sample'):
                continue
            point=item['states'][-1];time=item['time_s'];boundary=model.program.at(time)
            gas=ideal_gas_state(point['amounts_mol'],temperature_k=point['temperature_k'],gas_volume_m3=point['gas_volume_m3'],**gas_inputs)
            reservoir=ideal_gas_reservoir(temperature_k=boundary.gas_temperature_k,pressure_pa=boundary.total_pressure_pa,
                mole_fractions=boundary.mole_fractions,**gas_inputs)
            result=model.evaporating_surface.rate(gas,point,reservoir)
            rows.append({'time_s':time,'surface_temperature_k':result.surface['temperature_k'],
                'surface_pressure_pa':result.surface['pressure_pa'],'surface_moisture_kg_kg':result.surface['moisture_kg_kg_dry'],
                'surface_evaporation_mol_s':result.interior_face.condensed_face.molar_flow_mol_s,
                'external_water_mol_s':result.exterior_face.exchange.net_mol_s['H2O'],
                'maximum_inventory_rate_residual_mol_s':max(map(abs,result.inventory_rate_residuals_mol_s.values())),
                'energy_rate_residual_w':result.energy_rate_residual_w})
    return {'trajectory':str(path),'cell_count':header['cell_count'],'samples':rows,
            'completed':terminal['kind']=='summary' and terminal['status']=='completed'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();policy=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    results={name:observe(root/name) for name in policy['trajectories']};comparisons=[]
    for pair in policy['comparisons']:
        a,b=results[pair['left']]['samples'],results[pair['right']]['samples']
        if [p['time_s'] for p in a]!=[p['time_s'] for p in b]:
            raise ValueError('surface comparison requires matching saved times')
        fields=('surface_temperature_k','surface_pressure_pa','surface_moisture_kg_kg','surface_evaporation_mol_s','external_water_mol_s')
        maxima={key:max(abs(x[key]-y[key]) for x,y in zip(a,b,strict=True)) for key in fields}
        comparisons.append({**pair,'maximum_differences':maxima,
            'within_temperature_budget':maxima['surface_temperature_k']<=policy['temperature_budget_k'][pair['type']]})
    result={'policy':policy,'results':results,'comparisons':comparisons,'material_qualified':False,'training_eligible':False,
        'scope':'Surface at the same physical column endpoint. Postprocessing uses the recorded source and production surface root; independent source and entropy qualification are separate.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(comparisons,indent=2))


if __name__=='__main__':
    main()
