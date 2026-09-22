"""Independent source/join arithmetic and thermodynamic derivative accounting."""
import argparse
import json
import math
from pathlib import Path
import sys

from scipy.integrate import quad
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_sorption import RecordedLowMoisture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    record = json.loads((root/config['sorption_record_file']).read_text())
    facts = json.loads((root/config['source_files']['curves']).read_text())
    settings = config['source_review']
    r, mass, t0 = (record[k] for k in ('gas_constant_j_mol_k', 'water_molar_mass_kg_mol', 'reference_temperature_k'))
    wj, wr = record['join']['moisture_kg_kg'], record['reference_moisture_kg_kg']
    curves = {}
    for figure, key in [(1, 'activity'), (2, 'heat')]:
        pairs = []
        for w in config['source_construction'][key+'_levels_kg_kg']:
            item = next(p for p in facts['observations'] if p['figure'] == figure and
                        float(p['requested_moisture_kg_water_per_kg_dry_matter']) == w)
            pairs.append((w, int(item['value']['numerator'])/int(item['value']['denominator'])))
        curves[key] = pairs
    a, q = np.array(curves['activity']), np.array(curves['heat'])
    chemical = lambda w: r/mass*t0*float(np.interp(w, a[:,0], np.log(a[:,1])))
    partial_h = lambda w: record['reference_ideal_vapor_minus_liquid_enthalpy_j_kg']-float(np.interp(w,q[:,0],q[:,1]))
    integrate = lambda function, nodes: quad(function, wr, wj, points=list(nodes[1:-1]),
        epsabs=settings['quad_absolute_tolerance'], epsrel=settings['quad_relative_tolerance'],
        limit=settings['quad_maximum_subintervals'])
    h, h_error = integrate(partial_h,q[:,0])
    g, g_error = integrate(chemical,a[:,0])
    s = (h-g)/t0
    b, c = partial_h(wj), (partial_h(wj)-chemical(wj))/t0
    independent = {'h_j_kg_dry': h, 'g_at_reference_j_kg_dry': g,
        's_j_kg_dry_k': s, 'partial_h_j_kg_water': b, 'partial_s_j_kg_water_k': c}
    differences = {key: value-record['join'][key] for key,value in independent.items()}
    model = RecordedLowMoisture(record)
    derived = model.evaluate(t0,wj)
    held_out = next(p for p in facts['observations'] if p['figure'] == 1 and
                   float(p['requested_moisture_kg_water_per_kg_dry_matter']) == config['observation']['moisture_target_kg_kg'])
    read_fraction = lambda p: int(p['numerator'])/int(p['denominator'])
    w = float(held_out['requested_moisture_kg_water_per_kg_dry_matter'])
    holdout = {'moisture_kg_kg': w, 'model_activity': model.evaluate(t0,w)['activity'],
        'source_activity': read_fraction(held_out['value']),
        'source_digitization_bounds': [read_fraction(v) for v in held_out['digitization_bounds']],
        'qualification': 'Same published curve, not independent experiment; heat at this point remains unknown.'}
    derivatives = []
    dt, dw = settings['temperature_difference_step_k'], settings['moisture_difference_step_kg_kg']
    for t in settings['temperatures_k']:
        for w in settings['moisture_levels_kg_kg']:
            point = model.evaluate(t,w)
            mu_from_f = mass*(model.evaluate(t,w+dw)['f_j_kg_dry']-model.evaluate(t,w-dw)['f_j_kg_dry'])/(2*dw)
            dmu_dt = (model.evaluate(t+dt,w)['mu_j_mol']-model.evaluate(t-dt,w)['mu_j_mol'])/(2*dt)
            derivatives.append({'temperature_k': t, 'moisture_kg_kg': w,
                'mu_minus_m_dfdw_j_mol': point['mu_j_mol']-mu_from_f,
                'mu_minus_t_dmu_dt_minus_partial_h_j_mol': point['mu_j_mol']-t*dmu_dt-point['partial_h_j_mol']})
    heat = record['reference_ideal_vapor_minus_liquid_enthalpy_j_kg']-derived['partial_h_j_mol']/mass
    result = {'parameters': settings, 'independent_join': independent, 'join_differences': differences,
        'quad_error_estimates': {'h_j_kg_dry':h_error,'g_j_kg_dry':g_error},
        'source_activity_join_difference': derived['activity']-a[0,1],
        'source_heat_join_difference_j_kg': heat-q[0,1], 'same_curve_holdout': holdout,
        'derivatives': derivatives, 'dry_endpoint': model.evaluate(t0,0),
        'within_budgets': {
            'join': all(abs(v)<=settings['join_quadrature_budget_j_kg'] for v in differences.values()),
            'activity': bool(abs(derived['activity']-a[0,1])<=settings['calibration_activity_budget']),
            'heat': bool(abs(heat-q[0,1])<=settings['calibration_heat_budget_j_kg']),
            'derivatives': all(max(abs(p['mu_minus_m_dfdw_j_mol']),abs(p['mu_minus_t_dmu_dt_minus_partial_h_j_mol']))<=
                               settings['mu_derivative_budget_j_mol'] for p in derivatives)},
        'material_qualified': False, 'training_eligible': False,
        'scope': 'Independent quadrature/readout of saved source nodes and caloric reference; shared ideal-vapor/liquid latent reference retained. No real-material time prediction.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('derivatives','parameters')},indent=2))


if __name__ == '__main__':
    main()
