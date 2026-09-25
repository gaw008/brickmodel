"""Conservative condensed-water face arithmetic and reference-coordinate study."""
import argparse
from dataclasses import asdict
from fractions import Fraction as F
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sorptive_column_setup import build_column
from sludge_sandbox.recorded_condensed_transport import condensed_exchange


def exact_face(left,right,geometry,mobility_density):
    tl,tr=F(left['temperature_k']),F(right['temperature_k'])
    ml,mr=F(left['condensed_chemical_potential_j_mol']),F(right['condensed_chemical_potential_j_mol'])
    h=(F(left['condensed_partial_enthalpy_j_mol'])+F(right['condensed_partial_enthalpy_j_mol']))/2
    force=ml/tl-mr/tr+h*(1/tr-1/tl)
    mobility=F(geometry['area_m2'])/F(geometry['distance_m'])*F(mobility_density)
    return {'flow':mobility*force,'energy':h*mobility*force,'entropy':mobility*force*force,'force':force}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();p=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    c=json.loads((root/p['model_parameters_file']).read_text());model=build_column(root,c,p['cell_count']);host=model.host
    geometry={'area_m2':c['geometry']['face_area_m2'],'distance_m':c['geometry']['length_m']/p['cell_count']}
    mobility=c['condensed_transfer']['mobility_density_mol2_k_j_s_m'];budget=p['budgets'];rows=[]
    for case in p['cases']:
        points=[]
        for key in ('left','right'):
            spec=case[key]
            inventories=host.inventories_at_tp_moisture(spec['temperature_k'],spec['pressure_pa'],spec['moisture_kg_kg'],c['initial']['carrier_mole_fractions'])
            points.append(host.at_temperature(inventories,spec['temperature_k'])[1])
        left,right=points
        call=lambda a,b:condensed_exchange(a,b,**geometry,mobility_density_mol2_k_j_s_m=mobility)
        actual=call(left,right);reverse=call(right,left);exact=exact_face(left,right,geometry,mobility)
        shift=p['reference_shift_j_mol']
        def shifted(point):
            return {**point,'condensed_chemical_potential_j_mol':point['condensed_chemical_potential_j_mol']+shift,
                    'condensed_partial_enthalpy_j_mol':point['condensed_partial_enthalpy_j_mol']+shift}
        translated=call(shifted(left),shifted(right))
        tl,tr=F(left['temperature_k']),F(right['temperature_k'])
        chemical=F(left['condensed_chemical_potential_j_mol'])/tl-F(right['condensed_chemical_potential_j_mol'])/tr
        rounded_entropy=F(actual.carried_energy_w)*(1/tr-1/tl)+F(actual.molar_flow_mol_s)*chemical
        differences={'flow_mol_s':float(F(actual.molar_flow_mol_s)-exact['flow']),
            'energy_w':float(F(actual.carried_energy_w)-exact['energy']),
            'entropy_w_k':float(F(actual.entropy_production_w_k)-exact['entropy']),
            'orientation_flow_sum_mol_s':actual.molar_flow_mol_s+reverse.molar_flow_mol_s,
            'orientation_energy_sum_w':actual.carried_energy_w+reverse.carried_energy_w,
            'reference_flow_difference_mol_s':translated.molar_flow_mol_s-actual.molar_flow_mol_s,
            'reference_energy_difference_minus_shifted_inventory_w':translated.carried_energy_w-actual.carried_energy_w-shift*actual.molar_flow_mol_s,
            'reference_entropy_difference_w_k':translated.entropy_production_w_k-actual.entropy_production_w_k}
        flags={key:abs(value)<=budget['molar_flow_mol_s' if 'mol_s' in key else ('entropy_w_k' if 'w_k' in key else 'energy_w')] for key,value in differences.items()}
        flags['exact_entropy_nonnegative']=exact['entropy']>=0
        flags['rounded_rate_entropy_nonnegative']=rounded_entropy>=0
        rows.append({'name':case['name'],'states':points,'face':asdict(actual),'differences':differences,
                     'rounded_rate_entropy_w_k':float(rounded_entropy),'within_budgets':flags})
    output={'parameters':p,'model_parameters':c,'rows':rows,'all_within_budgets':all(all(x['within_budgets'].values()) for x in rows),
            'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(output,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_within_budgets':output['all_within_budgets'],'cases':[{k:v for k,v in row.items() if k!='states'} for row in rows]},indent=2))


if __name__=='__main__':
    main()
