"""Recorded-state equilibrium-chart and directional derivative study."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sorptive_column_setup import restore_column
from sorptive_primitive_jacobian import PrimitiveColumnJacobian


def review(model, row, species, policy, settings):
    n=model.count;w=len(species)+1
    seed=[s['temperature_k'] for s in row['states']]
    def decode(vector):
        pairs=[model.host.decode(dict(zip(species,map(float,v[:-1]),strict=True)),float(v[-1]),t)
            for v,t in zip(vector[:n*w].reshape(n,w),seed,strict=True)]
        return [x[0] for x in pairs],[x[1] for x in pairs]
    jac=PrimitiveColumnJacobian(model,decode,species,policy)
    def rhs(vector):
        gases,states=decode(vector);faces,_=model.rates(gases,row['time_s'],states)
        flux=np.array([jac.flux(f) for f in faces]);derivative=-flux.copy();derivative[1:]+=flux[:-1]
        return np.concatenate((derivative.ravel(),flux[-1]))
    vector=np.array(row['conserved_state']);gases,states=decode(vector)
    differences={'temperature_k':0.,'pressure_pa':0.,'inventory_mol':0.,'energy_j':0.}
    condition=[];direction=[]
    for i,(gas,state) in enumerate(zip(gases,states,strict=True)):
        direct=jac.direct(jac.coordinates(gas,state))[1]
        differences['inventory_mol']=max(differences['inventory_mol'],float(np.max(np.abs(jac.conserved(direct)[:-1]-jac.conserved(state)[:-1]))))
        differences['energy_j']=max(differences['energy_j'],abs(direct['constitutive_internal_energy_j']-state['constitutive_internal_energy_j']))
        returned=model.host.decode(direct['inventories_mol'],direct['constitutive_internal_energy_j'],state['temperature_k'])[1]
        for k in ('temperature_k','pressure_pa'):
            differences[k]=max(differences[k],abs(returned[k]-state[k]))
        _,capacity,_,cond=jac.local_chart(gas,state);condition.append(cond)
        direction.extend(capacity@np.array(settings['direction_primitive_changes'])*settings['direction_cell_factors'][i])
    direction=np.array(direction+[0.]*w)
    matrix=jac(row['time_s'],vector);nominal=matrix@direction
    amplitude=settings['direction_amplitude']
    independent=(rhs(vector+amplitude*direction)-rhs(vector-amplitude*direction))/(2*amplitude)
    fine=deepcopy(policy)
    fine['central_steps']={k:v*settings['difference_step_factor'] for k,v in policy['central_steps'].items()}
    refined=PrimitiveColumnJacobian(model,decode,species,fine)(row['time_s'],vector)@direction
    scales=np.tile(settings['flux_scales'],n+1)
    derivative=float(np.max(np.abs(nominal-independent)/scales))
    refinement=float(np.max(np.abs(nominal-refined)/scales))
    # Every physical face contributes with opposite signs, including ledger.
    ledger=float(np.max(np.abs(matrix.toarray().reshape(n+1,w,(n+1)*w).sum(axis=0))))
    b=settings['budgets']
    flags={k:v<=b['roundtrip_'+k] for k,v in differences.items()}
    flags.update(directional=derivative<=b['derivative_scaled_absolute'],step_refinement=refinement<=b['step_refinement_scaled_absolute'],
                 conserved_jacobian=ledger<=b['ledger_derivative_absolute'])
    return {'time_s':row['time_s'],'roundtrip_maxima':differences,'capacity_scaled_condition_numbers':condition,
        'directional_scaled_absolute_difference':derivative,'step_refinement_scaled_absolute_difference':refinement,
        'maximum_conserved_jacobian_column_sum':ledger,'within_budgets':flags}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent
    settings=json.loads(args.parameters.read_text());policy=json.loads((root/settings['jacobian_parameters']).read_text())
    started=time.monotonic();records=[]
    for name in settings['trajectories']:
        with (root/name).open() as stream:
            header=json.loads(next(stream));selected=[]
            for line in stream:
                row=json.loads(line)
                if row['kind'] in ('initial','sample') and row['time_s'] in settings['times_s']:
                    selected.append(row)
        if [r['time_s'] for r in selected]!=settings['times_s']:
            raise ValueError('requested physical observations not present')
        with TemporaryDirectory(prefix='primitive-chart-') as directory:
            model=restore_column(header,Path(directory));species=header['parameters']['boundary_program']['values']['species_order']
            records.append({'trajectory':name,'observations':[review(model,row,species,policy,settings) for row in selected]})
    result={'settings':settings,'jacobian_policy':policy,'records':records,'elapsed_s':time.monotonic()-started,
        'all_numerical_budgets_met':all(all(p['within_budgets'].values()) for r in records for p in r['observations']),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
