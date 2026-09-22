"""Independent source/join arithmetic and thermodynamic derivative accounting."""
import argparse
import json
import math
from pathlib import Path
import sys

from scipy.integrate import quad
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_sorption import RecordedLowMoisture, RecordedSourceSorption


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
    model = {'sorptive_common_gas_cell_v1': RecordedLowMoisture,
             'source_sorptive_common_gas_cell_v1': RecordedSourceSorption}[config['schema']](record)
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
    if config['schema'] == 'source_sorptive_common_gas_cell_v1':
        nodes = {
            'activity': [{'moisture_kg_kg':float(w),'difference':model.evaluate(t0,float(w))['activity']-float(value)} for w,value in a],
            'heat': [{'moisture_kg_kg':float(w),'difference_j_kg':record['reference_ideal_vapor_minus_liquid_enthalpy_j_kg']-
                      model.evaluate(t0,float(w))['partial_h_j_mol']/mass-float(value)} for w,value in q]}
        crossings=[];delta=settings['join_one_sided_step_kg_kg']
        for t in settings['temperatures_k']:
            center=model.evaluate(t,wj)
            sides=[model.evaluate(t,wj+sign*delta) for sign in [-1,1]]
            crossings.append({'temperature_k':t,'one_sided_step_kg_kg':delta,
                'left_minus_join':{key:sides[0][key]-center[key] for key in ('h_j_kg_dry','s_j_kg_dry_k','mu_j_mol','partial_h_j_mol')},
                'right_minus_join':{key:sides[1][key]-center[key] for key in ('h_j_kg_dry','s_j_kg_dry_k','mu_j_mol','partial_h_j_mol')}})
        segments=[]
        moisture_nodes=sorted(set(a[:,0])|set(q[:,0]))
        for left,right in zip(moisture_nodes[:-1],moisture_nodes[1:],strict=True):
            dm=(chemical(right)-chemical(left))/(right-left)
            db=(partial_h(right)-partial_h(left))/(right-left)
            endpoints=[mass*(t/t0*dm+(1-t/t0)*db) for t in record['model_domain']['temperature_k']]
            segments.append({'moisture_interval_kg_kg':[float(left),float(right)],
                'dmu_dw_at_temperature_endpoints_j_mol':list(map(float,endpoints)),
                'strictly_positive_on_declared_temperature_interval':bool(min(endpoints)>0)})
        result['source_nodes']=nodes
        result['join_one_sided_approach']=crossings
        result['source_branch_stability']=segments
        result['within_budgets'].update({
            'all_source_activity_nodes':all(abs(p['difference'])<=settings['calibration_activity_budget'] for p in nodes['activity']),
            'all_source_heat_nodes':all(abs(p['difference_j_kg'])<=settings['calibration_heat_budget_j_kg'] for p in nodes['heat']),
            'join_one_sided_approach':all(abs(v)<=settings['join_h_s_absolute_budget'] for p in crossings for side in ('left_minus_join','right_minus_join') for v in p[side].values()),
            'positive_composition_slope':all(p['strictly_positive_on_declared_temperature_interval'] for p in segments)})
        result['continuity_scope']='The finite one-sided approach checks h/s and first partials; dmu/dW may jump at source knots and the low-W join. Temperature extrapolation remains unvalidated.'
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('derivatives','parameters')},indent=2))


if __name__ == '__main__':
    main()
