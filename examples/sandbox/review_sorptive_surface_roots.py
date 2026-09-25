"""Replay every boundary state and dense node under explicit root tolerances.

Only the last cell is decoded. The independent source surface equations are
unchanged. Each tolerance is a separate numerical experiment, never a fallback.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_sorptive_gas_cell import polynomial
from sorptive_column_setup import restore_column, cell_parameters
from sorptive_source_formulas import source_for_column


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    audit = json.loads((root/settings['source_audit_parameters']).read_text())
    path = root/settings['trajectory'];started = time.monotonic()
    with path.open() as stream:
        header = json.loads(next(stream))
    n = header['cell_count'];species = header['parameters']['boundary_program']['values']['species_order'];width = len(species)+1
    sources = [];reviews = []
    for policy in settings['surface_policies']:
        single = deepcopy(header)
        single['parameters'] = cell_parameters(single['parameters'],n)
        single['parameters']['surface_equilibrium']['coordinate_tolerance'] = policy['coordinate_tolerance']
        sources.append(source_for_column(single,audit['source_quadrature']))
        reviews.append({'policy':policy,'evaluations':0,'failures':0,'first_failure':None,
            'maximum_species_residual_mol_s':0.,'maximum_energy_residual_w':0.,
            'worst_species':None,'worst_energy':None,'minimum_entropy_production_w_k':None})
    def examine(at,point,location):
        for source,review in zip(sources,reviews,strict=True):
            review['evaluations'] += 1
            try:
                rates = source.fluxes(at,point)
            except (ValueError,RuntimeError,OverflowError) as error:
                review['failures'] += 1
                if review['first_failure'] is None:
                    review['first_failure'] = {'time_s':at,'location':location,'state':point,'error':str(error)}
                continue
            amounts = max(map(abs,rates['surface_inventory_residuals_mol_s'].values()))
            energy = abs(rates['surface_energy_residual_w'])
            for name,value,worst in [('maximum_species_residual_mol_s',amounts,'worst_species'),('maximum_energy_residual_w',energy,'worst_energy')]:
                if value>review[name]:
                    review[name] = value
                    review[worst] = {'time_s':at,'location':location,'state':point,'surface':rates['surface_state'],'value':value}
            production = min(rates['individual_productions_w_k'])
            previous = review['minimum_entropy_production_w_k']
            review['minimum_entropy_production_w_k'] = production if previous is None else min(previous,production)
    with TemporaryDirectory(prefix='surface-root-review-') as directory:
        model = restore_column(header,Path(directory));seed = None;accepted = 0
        with path.open() as stream:
            next(stream)
            for line in stream:
                row = json.loads(line)
                if row['kind'] in settings['state_kinds']:
                    point = row['states'][-1];seed = point['temperature_k']
                    examine(row['time_s'],point,{'kind':row['kind']})
                if row['kind']!='accepted':
                    continue
                accepted += 1;dense = row['dense_output']
                left,right = dense['start_time_s'],dense['end_time_s']
                for order in settings['quadrature_orders']:
                    nodes,_ = leggauss(order)
                    for index,node in enumerate(nodes):
                        at = float((left+right)/2+(right-left)*node/2)
                        vector = polynomial(dense,at)[(n-1)*width:n*width]
                        _,point = model.host.decode(dict(zip(species,map(float,vector[:-1]),strict=True)),float(vector[-1]),seed)
                        seed = point['temperature_k']
                        examine(at,point,{'kind':'dense_node','quadrature_order':order,'node_index':index,'interval_end_s':right})
                if accepted%settings['progress_every_steps']==0:
                    print(json.dumps({'accepted_intervals':accepted,'time_s':right,'elapsed_s':time.monotonic()-started,
                        'policies':[{'failures':r['failures'],'maximum_energy_residual_w':r['maximum_energy_residual_w']} for r in reviews]}),flush=True)
    budget = audit['comparison_budgets']
    for review in reviews:
        review['within_budgets'] = {
            'root_completion':review['failures']==0,
            'surface_species':review['maximum_species_residual_mol_s']<=budget['surface_inventory_rate_mol_s'],
            'surface_energy':review['maximum_energy_residual_w']<=budget['surface_energy_rate_w']}
    result = {'settings':settings,'original_surface_policy':header['parameters']['surface_equilibrium'],
        'source_audit_parameters':audit,'reviews':reviews,'elapsed_s':time.monotonic()-started,
        'scope':'Independent surface root replay on recorded physical states and every original 2/4 Gauss node. No reintegration, no time accuracy or material qualification.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'policies':[r['within_budgets'] for r in reviews],'elapsed_s':result['elapsed_s']}))


if __name__=='__main__':
    main()
