"""Compare the frozen Gibbs representation with direct IAPWS states."""
import argparse
import json
from pathlib import Path
import sys

from iapws import IAPWS95
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--column-parameters', required=True, type=Path)
    parser.add_argument('--table', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    c = json.loads(args.parameters.read_text())
    column = json.loads(args.column_parameters.read_text())
    table = json.loads(args.table.read_text())
    root = args.parameters.resolve().parent
    sys.path.insert(0, str(root/'src'))
    from sludge_sandbox.gibbs_water_table import GibbsWaterTable
    from sludge_sandbox.recorded_water import RecordedWaterProperties
    from sludge_sandbox.water_properties import NumericalLimits
    water = RecordedWaterProperties(root/c['water_facts_file'], NumericalLimits(**column['numerics']['water']))
    model = GibbsWaterTable(water, table)
    mass, offset = water.reference.molar_mass_kg_mol, water.reference.energy_offset_j_mol
    rows = []
    for t in np.linspace(*c['temperature_domain_k'], c['independent_review_grid_counts'][0]):
        for pressure in np.linspace(*c['pressure_domain_pa'], c['independent_review_grid_counts'][1]):
            t, pressure = float(t), float(pressure)
            source = IAPWS95(T=t, P=pressure/1e6)
            p = model.gibbs_properties(t, pressure)
            runtime = model.state_tp(t,pressure,phase='liquid')
            fixed_temperature = model.liquid_at_temperature(t)(pressure)
            differences = {
                'gibbs_j_mol': p['native_gibbs_j_mol']-(source.h-t*source.s)*1000*mass,
                'enthalpy_j_mol': p['enthalpy_j_mol']-(source.h*1000*mass+offset),
                'internal_energy_j_mol': p['internal_energy_j_mol']-(source.u*1000*mass+offset),
                'entropy_j_mol_k': p['entropy_j_mol_k']-source.s*1000*mass,
                'molar_volume_relative': p['molar_volume_m3_mol']/(mass/source.rho)-1,
                'cp_j_mol_k': p['cp_j_mol_k']-source.cp*1000*mass,
                'cv_j_mol_k': p['cv_j_mol_k']-source.cv*1000*mass,
            }
            runtime_differences = {
                'enthalpy_j_mol':runtime.enthalpy_j_mol-(source.h*1000*mass+offset),
                'internal_energy_j_mol':runtime.internal_energy_j_mol-(source.u*1000*mass+offset),
                'entropy_j_mol_k':runtime.native_entropy_j_kg_k*mass-source.s*1000*mass,
                'molar_volume_relative':source.rho/runtime.density_kg_m3-1}
            fixed_temperature_differences = {
                'enthalpy_j_mol':fixed_temperature.enthalpy_j_mol-(source.h*1000*mass+offset),
                'internal_energy_j_mol':fixed_temperature.internal_energy_j_mol-(source.u*1000*mass+offset),
                'entropy_j_mol_k':fixed_temperature.native_entropy_j_kg_k*mass-source.s*1000*mass,
                'molar_volume_relative':source.rho/fixed_temperature.density_kg_m3-1}
            rows.append({'temperature_k': t, 'pressure_pa': pressure, 'differences': differences,
                         'runtime_state_differences':runtime_differences,
                         'fixed_temperature_differences':fixed_temperature_differences,
                         'source_phase_is_liquid': bool(source.x == 0)})

    def bound(coefficients):
        center = float(coefficients[0, 0])
        remainder = float(np.abs(coefficients).sum())-abs(center)
        return [center-remainder, center+remainder]

    v, v_p, s_t, v_t = bound(model.dp), bound(model.dpp), bound(model.dtt), bound(model.dtp)
    minimum_cp = min(-t*d for t in c['temperature_domain_k'] for d in s_t)
    minimum_cv = minimum_cp-max(c['temperature_domain_k'])*max(abs(x) for x in v_t)**2/(-v_p[1])
    stability = {'method': 'Chebyshev coefficient triangle bound: |T_n(x)|<=1 over declared rectangle',
                 'molar_volume_bound_m3_mol': v, 'dv_dp_bound_m3_mol_pa': v_p,
                 'd2g_dt2_bound_j_mol_k2': s_t, 'dv_dt_bound_m3_mol_k': v_t,
                 'cp_lower_bound_j_mol_k': minimum_cp, 'cv_lower_bound_j_mol_k': minimum_cv,
                 'positive_volume_cp_cv_and_compressibility': v[0]>0 and v_p[1]<0 and minimum_cp>0 and minimum_cv>0,
                 'qualification': 'algebraic bound for saved polynomial coefficients; not an interval-certified IAPWS approximation error'}
    maxima = {key: max(abs(r['differences'][key]) for r in rows) for key in c['comparison_budgets']}
    runtime_maxima = {key:max(abs(row['runtime_state_differences'][key]) for row in rows) for key in runtime_differences}
    fixed_temperature_maxima = {key:max(abs(row['fixed_temperature_differences'][key]) for row in rows) for key in fixed_temperature_differences}
    result = {'parameters': c, 'review_points': len(rows), 'fit_points': len(table['source_points']),
              'grid_differs_from_fit_nodes': True, 'maximum_absolute_differences': maxima,
              'within_predeclared_budget': {k: bool(maxima[k]<=limit) for k, limit in c['comparison_budgets'].items()},
              'runtime_state_maximum_absolute_differences':runtime_maxima,
              'runtime_state_within_predeclared_budget':{key:bool(value<=c['comparison_budgets'][key]) for key,value in runtime_maxima.items()},
              'fixed_temperature_maximum_absolute_differences':fixed_temperature_maxima,
              'fixed_temperature_within_predeclared_budget':{key:bool(value<=c['comparison_budgets'][key]) for key,value in fixed_temperature_maxima.items()},
              'stability_of_polynomial': stability, 'rows': rows,
              'qualification': 'numerical representation review against same EOS backend; no material qualification'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('parameters', 'rows')}, indent=2))


if __name__ == '__main__':
    main()
