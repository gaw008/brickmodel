"""Source/flux/entropy study of an explicitly zero-storage sorptive surface."""
import argparse
from copy import deepcopy
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.gas_transport import ideal_gas_reservoir
from sludge_sandbox.recorded_sorptive_surface import SorptiveEvaporatingSurface
from sorptive_column_setup import build_column,cell_parameters
from sorptive_source_formulas import MobileWaterSource


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    config=json.loads((root/settings['model_parameters_file']).read_text())
    column=build_column(root,config,settings['cell_count']);host=column.host
    interface=SorptiveEvaporatingSurface(host,config,settings['cell_count'])
    with (root/settings['source_header_file']).open() as f:header=json.loads(next(f))
    header=deepcopy(header);header['parameters']=cell_parameters(config,settings['cell_count'])
    source=MobileWaterSource(header,settings['source_quadrature']);budget=settings['budgets'];rows=[]
    for case in settings['cases']:
        inventories=host.inventories_at_tp_moisture(case['cell_temperature_k'],case['cell_pressure_pa'],
            case['cell_moisture_kg_kg'],config['initial']['carrier_mole_fractions'])
        gas,point=host.at_temperature(inventories,case['cell_temperature_k'])
        if case['reservoir']=='same_equilibrium':
            reservoir=gas
        else:
            b=case['reservoir'];xv=b['water_mole_fraction']
            reservoir=ideal_gas_reservoir(temperature_k=b['temperature_k'],pressure_pa=b['pressure_pa'],
                mole_fractions={**{k:(1-xv)*v for k,v in config['initial']['carrier_mole_fractions'].items()},'H2O':xv},
                molar_masses_kg_mol=config['molar_masses_kg_mol'],gas_constant_j_mol_k=source.r)
        actual=interface.rate(gas,point,reservoir);surface=actual.surface
        endpoint=lambda g:{'t':g.temperature_k,'p':g.pressure_pa,'x':dict(g.mole_fractions)}
        surface_endpoint={'t':surface['temperature_k'],'p':surface['pressure_pa'],'x':surface['gas_mole_fractions']}
        inner=source.connection(endpoint(gas),deepcopy(surface_endpoint),asdict(interface.inside))
        outer=source.connection(deepcopy(surface_endpoint),endpoint(reservoir),asdict(interface.outside))
        left_mu_h=source.condensed_fields(point);surface_mu_h=source.condensed_fields(surface)
        tl,ts=point['temperature_k'],surface['temperature_k']
        h=(left_mu_h['condensed_partial_enthalpy_j_mol']+surface_mu_h['condensed_partial_enthalpy_j_mol'])/2
        force=left_mu_h['condensed_chemical_potential_j_mol']/tl-surface_mu_h['condensed_chemical_potential_j_mol']/ts+h*(1/ts-1/tl)
        mobility=interface.inside.area_m2/interface.inside_distance*config['condensed_transfer']['mobility_density_mol2_k_j_s_m']
        flow=mobility*force;energy=h*flow;production=flow*force
        net={**inner['net_mol_s'],'H2O':inner['net_mol_s']['H2O']+flow}
        energy_inner=inner['energy_out_w']+energy
        mu_v=source.ideal('H2O',ts)[0]-ts*source.ideal('H2O',ts)[1]+source.r*ts*math.log(surface['gas_mole_fractions']['H2O']*surface['pressure_pa']/source.pref)
        differences={k:surface_mu_h[k]-surface[k] for k in surface_mu_h}
        differences['phase_mu_j_mol']=mu_v-surface_mu_h['condensed_chemical_potential_j_mol']
        balances={k:net[k]-outer['net_mol_s'][k] for k in source.config['boundary_program']['values']['species_order']}
        face_rate=max(abs(net[k]-actual.exchange.net_mol_s[k]) for k in net)
        energy_rate=abs(energy_inner-actual.energy_out_w)
        productions={'interior_gas_w_k':inner['production_w_k'],'interior_condensed_w_k':production,'exterior_gas_w_k':outer['production_w_k']}
        flags={'source_mu':max(abs(differences['condensed_chemical_potential_j_mol']),abs(differences['phase_mu_j_mol']))<=budget['source_mu_j_mol'],
            'source_h':abs(differences['condensed_partial_enthalpy_j_mol'])<=budget['source_h_j_mol'],
            'surface_inventory_balance':max(map(abs,balances.values()))<=budget['inventory_rate_mol_s'],
            'surface_energy_balance':abs(energy_inner-outer['energy_out_w'])<=budget['energy_rate_w'],
            'face_inventory':face_rate<=budget['inventory_rate_mol_s'],'face_energy':energy_rate<=budget['energy_rate_w'],
            'nonnegative_production':min(productions.values())>=-budget['entropy_rate_w_k']}
        row={'name':case['name'],'surface':surface,'root_evaluations':actual.root_evaluations,
            'source_differences':differences,'independent_surface_inventory_residuals_mol_s':balances,
            'independent_surface_energy_residual_w':energy_inner-outer['energy_out_w'],
            'maximum_face_inventory_difference_mol_s':face_rate,'face_energy_difference_w':energy_rate,
            'entropy_productions':productions,'surface_evaporation_mol_s':flow,'within_budgets':flags}
        rows.append(row);print(json.dumps(row),flush=True)
    result={'settings':settings,'config':config,'rows':rows,'all_within_budgets':all(all(r['within_budgets'].values()) for r in rows),
        'material_qualified':False,'training_eligible':False,'scope':'Static zero-storage surface; direct-source arithmetic with shared liquid EOS family. No time or spatial accuracy qualification.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':
    main()
