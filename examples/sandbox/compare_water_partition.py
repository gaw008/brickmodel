"""Re-evaluate recorded physical states with the current phase partition.

Old inventories and temperature are held fixed. This separates an algebraic
solver change from adaptive integration. No observations are fitted or adjusted.
"""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from equilibrium_water_column_setup import build_column
from water_column_checkpoint import restore_sources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();start=time.monotonic()
    settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    results=[]
    for name,path in settings['trajectories'].items():
        rows=[json.loads(line) for line in (root/path).read_text().splitlines()]
        header=rows[0];differences=[]
        with TemporaryDirectory(prefix='brick-partition-comparison-') as folder:
            folder=Path(folder)
            model=build_column(folder,restore_sources(header,folder),header['cell_count'])
            for row in rows:
                if row['kind'] not in settings['record_kinds']:
                    continue
                for i,old in enumerate(row['states']):
                    _,new=model.host_for_cell(i).at_temperature(old['inventories_mol'],old['temperature_k'])
                    liquid_volume_per_mol = model.host_for_cell(i).fluid.molar_masses_kg_mol['H2O']/new['liquid_density_kg_m3']
                    differences.append({'kind':row['kind'],'time_s':row['time_s'],'cell':i,
                        'old_phase':old['phase'],'new_phase':new['phase'],
                        'new_liquid_mol':new['liquid_water_mol'],
                        'liquid_difference_mol':new['liquid_water_mol']-old['liquid_water_mol'],
                        'pressure_difference_pa':new['pressure_pa']-old['pressure_pa'],
                        'energy_difference_j':new['constitutive_internal_energy_j']-old['constitutive_internal_energy_j'],
                        'new_pressure_closure_residual_pa':new['pressure_closure_residual_pa'],
                        'new_water_pressure_departure_pa':new['water_pressure_departure_pa'],
                        'total_inventory_liquid_volume_ratio':sum(old['inventories_mol'].values())*
                            liquid_volume_per_mol/model.volumes[i],
                        'equilibrium_pressure_volume_over_rt':new['equilibrium_partial_pressure_pa']*
                            liquid_volume_per_mol/(model.thermochemistry.gas_constant_j_mol_k*old['temperature_k'])})
        maxima={key:max(abs(p[key]) for p in differences) for key in settings['comparison_budgets']}
        results.append({'name':name,'trajectory':path,'states_compared':len(differences),
            'maximum_absolute_differences':maxima,
            'within_numerical_budgets':{key:val<=settings['comparison_budgets'][key] for key,val in maxima.items()},
            'phase_classification_differences':sum(p['old_phase']!=p['new_phase'] for p in differences),
            'minimum_new_liquid_mol':min(p['new_liquid_mol'] for p in differences),
            'maximum_total_inventory_liquid_volume_ratio':max(p['total_inventory_liquid_volume_ratio'] for p in differences),
            'maximum_equilibrium_pressure_volume_over_rt':max(p['equilibrium_pressure_volume_over_rt'] for p in differences),
            'differences':differences})
        print(json.dumps({k:v for k,v in results[-1].items() if k!='differences'}),flush=True)
    result={'settings':settings,'results':results,'elapsed_s':time.monotonic()-start,
        'qualification':'Same recorded sources and states, two algebraic phase algorithms. Not independent material validation.'}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':
    main()
