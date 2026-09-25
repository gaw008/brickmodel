"""Independent high-precision pure-gas flux and closed vessel equilibrium identities."""
import argparse
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.dusty_gas_finite_reservoir_column import FiniteReservoirDustyGasColumn


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    p=json.loads(args.parameters.read_text())
    with (args.parameters.resolve().parent/p['reference_property_trajectory']).open() as stream:
        h=json.loads(next(stream))
    mp.mp.dps=p['verification']['source_reference_decimal_precision']
    r,t=mp.mpf(h['gas_constant_j_mol_k']),mp.mpf(p['temperature_k'])
    rt=r*t
    pore=p['pore']
    dk=mp.mpf(2)/3*mp.mpf(pore['mean_pore_radius_m'])*mp.mpf(pore['porosity'])/mp.mpf(pore['tortuosity'])*mp.sqrt(8*rt/(mp.pi*mp.mpf(h['molar_masses_kg_mol'][0])))
    alpha=mp.mpf(pore['permeability_m2'])*rt/mp.mpf(h['pure_viscosities_pa_s'][0])
    vl,vr=[mp.mpf(p['reservoir_volumes_m3'][side]) for side in ['left','right']]
    pl,pr=[mp.mpf(p['initial_reservoir_partial_pressures_pa'][side][0]) for side in ['left','right']]
    vp=mp.mpf(pore['porosity'])*mp.mpf(p['geometry']['area_m2'])*mp.mpf(p['geometry']['length_m'])
    peq=(vl*pl+vr*pr+vp*(pl+pr)/2)/(vl+vr+vp)
    records=[]
    for mesh,count in p['meshes'].items():
        column=FiniteReservoirDustyGasColumn(p,count,h['gas_constant_j_mol_k'],h['molar_masses_kg_mol'],h['pure_viscosities_pa_s'],h['diffusivity_pressure_products_pa_m2_s'])
        for name,values in [('linear_initial',column.initial),('uniform_equilibrium',np.full(count+2,float(peq/rt)))]:
            c,faces=column.observe(values)
            rates=column.balances(c,faces)
            nodes=list(map(mp.mpf,values))
            distances=[mp.mpf(column.width)/2]+[mp.mpf(column.width)]*(count-1)+[mp.mpf(column.width)/2]
            flux=[-(dk*(b-a)+alpha*(b*b-a*a)/2)/d for a,b,d in zip(nodes[:-1],nodes[1:],distances,strict=True)]
            entropy=[-r*j*mp.log(b/a) for a,b,j in zip(nodes[:-1],nodes[1:],flux,strict=True)]
            flux_error=max(float(abs(mp.mpf(face['molar_fluxes_mol_m2_s'][0])-value)) for face,value in zip(faces,flux,strict=True))
            entropy_error=column.area*max(float(abs(mp.mpf(face['entropy_from_jump_w_m2_k'])-value)) for face,value in zip(faces,entropy,strict=True))
            n_rate=rates['inventory_rates_mol_s'][:,0]
            energy_error=float(np.max(np.abs(rates['internal_energy_rates_w']+np.diff(rates['stream_energy_fluxes_w'])-rates['bath_heat_into_cells_w'])))
            entropy_identity=abs(float(rates['cell_entropy_rates_w_k'].sum())+rates['bath_entropy_rate_w_k']-rates['all_faces_entropy_production_w_k'])
            peq_discrete=float(np.dot(column.volumes,column.initial)/column.volumes.sum()*column.rt)
            v=p['verification']
            flags={'source_flux':flux_error<=v['source_flux_absolute_budget_mol_m2_s'],
                'source_entropy':entropy_error<=v['source_entropy_rate_budget_w_k'],
                'total_inventory_rate':abs(float(n_rate.sum()))<=column.area*v['source_flux_absolute_budget_mol_m2_s'],
                'closed_bath_heat':abs(float(rates['bath_heat_into_cells_w'].sum()))<=v['source_energy_rate_budget_w'],
                'local_energy':energy_error<=v['source_energy_rate_budget_w'],
                'entropy_identity':entropy_identity<=v['source_entropy_rate_budget_w_k'],
                'equilibrium_inventory':abs(peq_discrete-float(peq))<=v['equilibrium_pressure_budget_pa']}
            records.append({'mesh':mesh,'profile':name,'flux_error_mol_m2_s':flux_error,'entropy_rate_error_w_k':entropy_error,
                'local_energy_error_w':energy_error,'entropy_identity_error_w_k':entropy_identity,'equilibrium_pressure_pa':peq_discrete,
                'net_inventory_rate_mol_s':float(n_rate.sum()),'net_bath_heat_w':float(rates['bath_heat_into_cells_w'].sum()),'within_budgets':flags})
    result={'settings':p,'equilibrium_pressure_pa_decimal':str(peq),'effective_knudsen_diffusivity_m2_s_decimal':str(dk),
        'records':records,'all_source_budgets_met':all(all(row['within_budgets'].values()) for row in records),
        'scope':'Frozen pure-gas law checked with MP80 arithmetic and independently derived finite-volume identities. Static scope, no dynamic or real-material qualification.',
        'material_qualified':False,'training_eligible':False}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'all_source_budgets_met':result['all_source_budgets_met'],'equilibrium_pressure_pa_decimal':str(peq)}))


if __name__=='__main__':main()
