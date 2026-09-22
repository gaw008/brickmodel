"""Physical entropy-production study of the declared isothermal gas faces.

No integration, fitted observations or state correction. Chemical-potential
differences follow the ideal-mixture expression; same-T standards cancel.
"""
import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.gas_transport import ideal_gas_reservoir, face_exchange


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    config=json.loads((root/settings['source_column_parameters']).read_text())
    thermo=json.loads((root/config['thermochemistry_file']).read_text())
    r=thermo['gas_constant']['value_j_mol_k']
    states=[]
    for p in settings['pressures_pa']:
        for water in settings['water_mole_fractions']:
            x={k:(1-water)*value for k,value in settings['dry_carrier_mole_fractions'].items()}
            x['H2O']=water
            gas=ideal_gas_reservoir(temperature_k=settings['temperature_k'],pressure_pa=p,
                mole_fractions=x,molar_masses_kg_mol=config['molar_masses_kg_mol'],gas_constant_j_mol_k=r)
            states.append(({'pressure_pa':p,'mole_fractions':x},gas))
    rows=[]
    for left_input,left in states:
        for right_input,right in states:
            flux=face_exchange(left,right,**settings['face'],**config['transfer']['gas'])
            forces={k:r*math.log(left.pressure_pa*left.mole_fractions[k]/(
                right.pressure_pa*right.mole_fractions[k])) for k in left.mole_fractions}
            rows.append({'left':left_input,'right':right_input,
                'diffusive_mol_s':dict(flux.diffusive_mol_s),'advective_mol_s':dict(flux.advective_mol_s),
                'chemical_over_t_difference_j_mol_k':forces,
                'diffusive_entropy_production_w_k':math.fsum(v*forces[k] for k,v in flux.diffusive_mol_s.items()),
                'advective_entropy_production_w_k':math.fsum(v*forces[k] for k,v in flux.advective_mol_s.items()),
                'total_entropy_production_w_k':math.fsum(v*forces[k] for k,v in flux.net_mol_s.items())})
    result={'settings':settings,'column_parameters':config,'gas_constant_j_mol_k':r,'faces':rows,
        'minimum_face':min(rows,key=lambda p:p['total_entropy_production_w_k']),
        'negative_face_count':sum(row['total_entropy_production_w_k']<0 for row in rows),
        'material_qualified':False,'qualification':'Finite isothermal face study; not a continuous-domain theorem.'}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'faces':len(rows),'negative_face_count':result['negative_face_count'],
        'minimum_face':result['minimum_face']},indent=2))


if __name__=='__main__':
    main()
