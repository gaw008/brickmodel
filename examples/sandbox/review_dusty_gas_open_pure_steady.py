"""MP steady Darcy-Knudsen pressure potential and explicit isothermal bath."""
import argparse
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.dusty_gas_open_isothermal_column import OpenIsothermalDustyGasColumn


def steady_reference(p, header, count):
    mp.mp.dps = p['verification']['source_reference_decimal_precision']
    gas_constant, temperature = mp.mpf(header['gas_constant_j_mol_k']), mp.mpf(p['temperature_k'])
    rt, length = gas_constant*temperature, mp.mpf(p['geometry']['length_m'])
    pore = p['pore']
    knudsen = (mp.mpf(2)/3*mp.mpf(pore['mean_pore_radius_m'])*mp.mpf(pore['porosity'])
        /mp.mpf(pore['tortuosity'])*mp.sqrt(8*rt/(mp.pi*mp.mpf(header['molar_masses_kg_mol'][0]))))
    alpha = mp.mpf(pore['permeability_m2'])*rt/mp.mpf(header['pure_viscosities_pa_s'][0])
    left, right = [mp.mpf(p['boundary_partial_pressures_pa'][side][0])/rt for side in ['left','right']]
    potential = lambda c: knudsen*c+alpha*c*c/2
    slope = (potential(right)-potential(left))/length

    def concentration(position):
        value = potential(left)+slope*position
        return 2*value/(knudsen+mp.sqrt(knudsen**2+2*alpha*value))

    width = length/count
    centers = [concentration((i+mp.mpf('0.5'))*width) for i in range(count)]
    edges = [concentration(i*width) for i in range(count+1)]
    averages = [(knudsen*(b*b-a*a)/2+alpha*(b*b*b-a*a*a)/3)/(slope*width)
        for a,b in zip(edges[:-1],edges[1:],strict=True)]
    return {'knudsen': knudsen, 'alpha': alpha, 'flux': -slope, 'centers': centers,
        'averages': averages, 'rt': rt, 'gas_constant': gas_constant}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    with (root/p['reference_property_trajectory']).open() as stream:
        header = json.loads(next(stream))
    records = []
    for mesh, count in p['meshes'].items():
        exact = steady_reference(p, header, count)
        column = OpenIsothermalDustyGasColumn(p, count, header['gas_constant_j_mol_k'],
            header['molar_masses_kg_mol'], header['pure_viscosities_pa_s'],
            header['diffusivity_pressure_products_pa_m2_s'])
        for name, values in [('steady_centers', np.array(exact['centers'], dtype=float)), ('uniform_initial', column.initial)]:
            concentration, faces = column.observe(values)
            rates = column.balances(concentration, faces)
            nodes = [mp.mpf(p['boundary_partial_pressures_pa']['left'][0])/exact['rt']]
            nodes += list(map(mp.mpf, values))
            nodes.append(mp.mpf(p['boundary_partial_pressures_pa']['right'][0])/exact['rt'])
            distances = [mp.mpf(column.width)/2]+[mp.mpf(column.width)]*(count-1)+[mp.mpf(column.width)/2]
            reference_flux, reference_entropy = [], []
            for left,right,distance in zip(nodes[:-1],nodes[1:],distances,strict=True):
                flux = -(exact['knudsen']*(right-left)+exact['alpha']*(right*right-left*left)/2)/distance
                reference_flux.append(flux)
                reference_entropy.append(-exact['gas_constant']*flux*mp.log(right/left))
            flux_error = max(float(abs(mp.mpf(face['molar_fluxes_mol_m2_s'][0])-value))
                for face,value in zip(faces,reference_flux,strict=True))
            entropy_error = column.area*max(float(abs(mp.mpf(face['entropy_from_jump_w_m2_k'])-value))
                for face,value in zip(faces,reference_entropy,strict=True))
            energy_error = float(np.max(np.abs(rates['internal_energy_rates_w']
                -np.diff(-rates['stream_energy_fluxes_w'])-rates['bath_heat_into_cells_w'])))
            entropy_identity = abs(float(np.sum(rates['cell_entropy_rates_w_k']))
                +rates['material_reservoir_entropy_rate_w_k']+rates['bath_entropy_rate_w_k']
                -rates['all_faces_entropy_production_w_k'])
            flags = {'face_flux': flux_error <= p['verification']['source_flux_absolute_budget_mol_m2_s'],
                'face_entropy': entropy_error <= p['verification']['source_entropy_rate_budget_w_k'],
                'local_energy_identity': energy_error <= p['verification']['source_energy_rate_budget_w'],
                'combined_entropy_identity': entropy_identity <= p['verification']['source_entropy_rate_budget_w_k']}
            row = {'mesh': mesh, 'cell_count': count, 'profile': name,
                'source_flux_error_mol_m2_s': flux_error, 'source_entropy_rate_error_w_k': entropy_error,
                'energy_identity_error_w': energy_error, 'combined_entropy_identity_error_w_k': entropy_identity,
                'bath_heat_into_whole_column_w': float(np.sum(rates['bath_heat_into_cells_w'])),
                'combined_entropy_production_w_k': rates['all_faces_entropy_production_w_k'], 'within_budgets': flags}
            if name == 'steady_centers':
                steady_error = max(float(abs(mp.mpf(face['molar_fluxes_mol_m2_s'][0])-exact['flux'])/abs(exact['flux'])) for face in faces)
                flags['steady_relative_flux'] = steady_error <= p['verification']['steady_relative_flux_budget']
                row.update(steady_flux_decimal=str(exact['flux']), steady_relative_flux_error=steady_error,
                    center_pressures_pa_decimal=[str(exact['rt']*value) for value in exact['centers']],
                    cell_average_pressures_pa_decimal=[str(exact['rt']*value) for value in exact['averages']],
                    maximum_center_vs_cell_average_pressure_pa=float(max(abs(a-b)*exact['rt']
                        for a,b in zip(exact['centers'],exact['averages'],strict=True))))
            records.append(row)
    result = {'settings': p, 'records': records,
        'all_requested_source_budgets_met': all(all(row['within_budgets'].values()) for row in records),
        'scope': 'Static original pure-gas flux and open bath/stream identities, plus exact steady center and cell-average comparison. No dynamic qualification yet.',
        'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'all_requested_source_budgets_met': result['all_requested_source_budgets_met']}), flush=True)


if __name__ == '__main__':
    main()
