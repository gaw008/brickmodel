"""Fit specified full-cycle parameters to labelled observations, without hashes."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import least_squares

from ..models.full_cycle import make_cycle, changed, run_cycle, write_json


UNITS = {'tg':'1', 'dsc':'W/kg', 'dilatometry':'1', 'kiln':'K',
         'absorption':'kg/kg', 'strength':'Pa', 'defects':'1', 'liquid_water':'kg/kg',
         'surface_temperature':'K'}


def predict(config: dict, observations: list[dict]):
    """Run one physical solution and map its labelled observation requests."""
    report, fields = run_cycle(config)
    return map_observations(config, observations, report, fields)


def map_observations(config: dict, observations: list[dict], report: dict, fields: dict):
    """Map an existing solution without integration; return (values, report).

    report and fields must come from the supplied configuration. liquid_water
    uses fields.rows.water_kg_per_initial_dry_kg: whole-domain liquid-water
    mass divided by initial dry mass, in kg/kg. Its arithmetic cell mean is
    valid because this model assigns every cell the same initial dry mass.
    It is neither the wettest cell nor TG, uses no current-dry-mass denominator,
    and excludes pore vapor and mineral-bound water. Binding acts on this same
    condensed-water inventory; its energy weight is not added as extra water.
    surface_temperature uses fields.rows.surface_temperature_k in K: the
    model outer-boundary temperature, distinct from kiln temperature and the
    outermost cell-center temperature. This field is read only when requested.
    Observation time_s is elapsed simulation time in seconds; the existing linear interpolation and
    process-time range and unit errors apply. Dataset source and explicit
    synthetic/measured identity remain managed by fit, not this mapping.
    """
    rows = fields['rows']
    time_s = np.array([r['time_s'] for r in rows])
    model = make_cycle(config)
    dry_mass = model.n*model.md
    curves = {'tg':np.array([r['mass_kg']/dry_mass for r in rows]),
              'dsc':np.array([r['dsc_endothermic_w_per_initial_dry_kg'] for r in rows]),
              'dilatometry':np.array([-np.mean(r['thickness_shrinkage']) for r in rows]),
              'kiln':np.array([r['kiln_temperature_k'] for r in rows]),
              'liquid_water':np.array([np.mean(r['water_kg_per_initial_dry_kg']) for r in rows])}
    if any(row['kind'] == 'surface_temperature' for row in observations):
        curves['surface_temperature'] = np.array([r['surface_temperature_k'] for r in rows])
    products = {'absorption':'absorption_kg_kg','strength':'strength_pa','defects':'defect_indicator'}
    values = []
    for row in observations:
        kind = row['kind']
        if row['unit'] != UNITS[kind]:
            raise ValueError(f'unit mismatch for observation {kind}')
        if kind in curves:
            if row['time_s'] < time_s[0] or row['time_s'] > time_s[-1]:
                raise ValueError('observation time outside the configured process')
            values.append(float(np.interp(row['time_s'], time_s, curves[kind])))
        else:
            values.append(report['summary'][products[kind]])
    return np.array(values), report


def fit(config: dict, dataset: dict, out: Path) -> dict:
    started = time.monotonic()
    kind = dataset['measurement_kind']
    if kind not in ('synthetic', 'measured') or not dataset['source']:
        raise ValueError('observations require explicit synthetic/measured identity and source')
    rows = dataset['observations']
    target = np.array([r['value'] for r in rows])
    scale = np.array([r['scale'] for r in rows])
    if np.any(scale <= 0) or not np.all(np.isfinite(target)):
        raise ValueError('finite values and positive residual normalization scales are required')
    keys = dataset['fit_parameters']
    p = config['parameters']
    bounds = np.array([p[k]['range'] for k in keys])
    widths = bounds[:,1]-bounds[:,0]
    if np.any(widths <= 0):
        raise ValueError('selected fit parameters require a nonzero declared range')
    x0 = (np.array([p[k]['value'] for k in keys])-bounds[:,0])/widths
    evaluations = []

    def residual(x):
        overrides = dict(zip(keys, bounds[:,0]+x*widths))
        values, report = predict(changed(config, overrides), rows)
        values = (values-target)/scale
        evaluations.append({'evaluation':len(evaluations)+1,'normalized_residual_norm':float(np.linalg.norm(values)),
                            'parameters':{k:float(v) for k,v in overrides.items()},
                            'physical_consistency_passed':report['physical_consistency_passed'],
                            'maximum_balance_relative_residual':max(
                                value for budget in [report['whole_cycle'],*report['stages'].values()]
                                for value in budget['relative_residuals'].values()),
                            'forward_elapsed_s':report['elapsed_s']})
        write_json(out/'calibration.progress.json',{'completed':False,'evaluation_history':evaluations})
        if not report['physical_consistency_passed']:
            raise ValueError('calibration forward calculation failed the declared physical consistency budget')
        print(f"calibration evaluation {len(evaluations)}: residual={np.linalg.norm(values):.6g}",flush=True)
        return values

    opt = least_squares(residual, x0, bounds=(np.zeros_like(x0),np.ones_like(x0)),
        max_nfev=int(p['calibration.max_nfev']['value']),
        ftol=p['calibration.tolerance']['value'],xtol=p['calibration.tolerance']['value'],gtol=p['calibration.tolerance']['value'],
        diff_step=p['calibration.difference_step']['value'])
    fitted = dict(zip(keys, map(float, bounds[:,0]+opt.x*widths)))
    values, forward = predict(changed(config, fitted), rows)
    rank = int(np.linalg.matrix_rank(opt.jac))
    qualified = bool(opt.success and rank == len(keys) and forward['physical_consistency_passed'])
    updated = changed(config, fitted)
    source_id = 'calibration_observations'
    updated['sources'][source_id] = {'identity':kind,'location':dataset['source'],'note':'Parameter estimate fitted to labelled observations; not a direct measurement of each constitutive constant.'}
    for key in keys:
        entry = updated['parameters'][key]
        original = deepcopy(config['parameters'][key])
        entry['calibration'] = {'measurement_kind':kind,'qualified_fit':qualified,'original_parameter':original,
                                'dataset_source':dataset['source'],'synthetic_fitted':kind=='synthetic'}
        if qualified and kind == 'measured':
            entry['status']='measured'
            entry['source']=source_id
        # Synthetic fits retain their original parameter identity, never measured.
    residual_rows = [dict(row,prediction=float(value),residual=float(value-row['value']),
                         normalized_residual=float((value-row['value'])/row['scale'])) for row,value in zip(rows,values)]
    result = {'schema':'sludge_vme_full_cycle_calibration_v1','measurement_kind':kind,'source':dataset['source'],
        'optimizer_success':bool(opt.success),'qualified_fit':qualified,'message':opt.message,'jacobian_rank':rank,
        'parameter_count':len(keys),'fitted_parameters':fitted,'residuals':residual_rows,
        'forward_physical_consistency_passed':forward['physical_consistency_passed'],
        'forward_example_endpoints':forward['example_endpoints'],
        'forward_summary':forward['summary'],'forward_thermodynamics':forward['thermodynamics'],
        'forward_whole_cycle':forward['whole_cycle'],'forward_stages':forward['stages'],
        'forward_state_domain':forward['state_domain'],'forward_dimension_check':forward['dimension_check'],
        'forward_elapsed_s':forward['elapsed_s'],
        'normalized_rmse':float(np.sqrt(np.mean(((values-target)/scale)**2))),
        'parameter_statuses':{k:updated['parameters'][k]['status'] for k in keys},
        'evaluation_history':evaluations,'elapsed_s':time.monotonic()-started,
        'limitations':'Same-model synthetic data establish software recoverability only. A qualified fit does not establish process endpoint acceptance; see forward_example_endpoints. Jacobian rank is local identifiability, not global uniqueness. Defects/strength/absorption are unvalidated proxies; DSC is net thermal boundary power per initial dry mass in stored-gas mode, not an instrument-specific prediction.'}
    write_json(out/'calibration.json',result)
    write_json(out/'fitted.parameters.json',updated)
    (out/'calibration.progress.json').unlink()
    return result


def synthetic_demo(config: dict, out: Path) -> dict:
    model = make_cycle(config)
    p = config['parameters']
    times = np.unique(np.r_[np.linspace(0,model.times[-1],int(p['calibration.sample_count']['value'])), model.times])
    rows = []
    for kind in ('tg','dsc','dilatometry','kiln'):
        for t in times:
            rows.append({'kind':kind,'time_s':float(t),'unit':UNITS[kind], 'scale':p['calibration.scale.'+kind]['value']})
    for kind in ('absorption','strength','defects'):
        rows.append({'kind':kind,'unit':UNITS[kind], 'scale':p['calibration.scale.'+kind]['value']})
    truth = {k:v['value'] for k,v in config['synthetic_truth_overrides'].items()}
    values,truth_report = predict(changed(config,truth),rows)
    dataset={'schema':'full_cycle_observations_v1','measurement_kind':'synthetic',
             'source':'Generated by this same approximate model from explicitly recorded synthetic truth; no measurement or added noise.',
             'fit_parameters':config['calibration_parameters'],'truth':truth,
             'truth_example_endpoints':truth_report['example_endpoints'],
             'observations':[dict(row,value=float(value)) for row,value in zip(rows,values)]}
    write_json(out/'synthetic.observations.json',dataset)
    result=fit(config,dataset,out)
    result['synthetic_parameter_relative_errors']={k:abs(result['fitted_parameters'][k]-v)/abs(v) for k,v in truth.items()}
    result['demonstration_passed']=result['qualified_fit'] and max(result['synthetic_parameter_relative_errors'].values()) < p['calibration.recovery_relative']['value']
    write_json(out/'calibration.json',result)
    return result


def binding_synthetic_demo(config: dict, out: Path) -> dict:
    """Recover one binding-energy hypothesis from a synthetic drying window.

    Root-declared times are elapsed seconds and liquid-water observations are
    kg/kg initial dry mass. Their scale normalizes residuals; it is not a
    measurement-error estimate. Truth and fitting use the same model and
    discretization with no added noise. Only binding energy is fitted; binding
    heat capacity and every other constitutive parameter remain fixed. This
    local recovery exercise supplies no measured identity or global uniqueness.
    """
    started = time.monotonic()
    window = deepcopy(config)
    window['stages'] = window['stages'][:window['stages'].index('drying')+1]
    p = window['parameters']
    key = 'water.binding_energy'
    truth = {key:p['calibration.binding.truth']['value']}
    initial = {key:p['calibration.binding.initial']['value']}
    rows = [{'kind':'liquid_water','time_s':float(t),'unit':UNITS['liquid_water'],
             'scale':p['calibration.scale.liquid_water']['value']}
            for t in p['calibration.binding.observation_times']['value']]
    values, truth_report = predict(changed(window,truth),rows)
    threshold = p['acceptance.drying_remaining_fraction']['value']
    truth_remaining = truth_report['example_endpoints']['drying_remaining_fraction']
    truth_audit = {
        'physical_consistency_passed':truth_report['physical_consistency_passed'],
        'window_balance':truth_report['whole_cycle'], 'stages':truth_report['stages'],
        'thermodynamics':truth_report['thermodynamics'],
        'state_domain':truth_report['state_domain'], 'dimension_check':truth_report['dimension_check'],
        'drying_remaining_fraction':truth_remaining,
        'drying_endpoint_passed':bool(truth_remaining < threshold),
        'forward_elapsed_s':truth_report['elapsed_s'],
    }
    dataset = {
        'schema':'full_cycle_observations_v1', 'measurement_kind':'synthetic',
        'source':'Same-model same-discretization synthetic liquid-water observations; no measurement or added noise.',
        'scope':'Drying window only; no completed firing cycle or cooled-product result.',
        'fit_parameters':[key], 'truth':truth, 'initial_guess':initial,
        'stages':window['stages'], 'truth_window_audit':truth_audit,
        'scale_interpretation':'Residual normalization in kg/kg, not measurement uncertainty.',
        'observations':[dict(row,value=float(value)) for row,value in zip(rows,values)],
    }
    write_json(out/'synthetic.observations.json',dataset)
    result = fit(changed(window,initial),dataset,out)
    remaining = result.pop('forward_example_endpoints')['drying_remaining_fraction']
    result.pop('forward_summary')
    result['forward_window_balance'] = result.pop('forward_whole_cycle')
    result['fit_elapsed_s'] = result['elapsed_s']
    relative_error = abs(result['fitted_parameters'][key]-truth[key])/abs(truth[key])
    result.update({
        'scope':'Drying window only; no completed firing cycle or cooled-product result.',
        'truth':truth, 'initial_guess':initial, 'truth_window_audit':truth_audit,
        'window_physical_passed':bool(truth_report['physical_consistency_passed']
            and result['forward_physical_consistency_passed']
            and all(row['physical_consistency_passed'] for row in result['evaluation_history'])),
        'synthetic_parameter_relative_errors':{key:relative_error},
        'parameter_recovery_relative_threshold':p['calibration.recovery_relative']['value'],
        'parameter_recovery_passed':bool(relative_error < p['calibration.recovery_relative']['value']),
        'drying_remaining_fraction':remaining, 'drying_remaining_fraction_threshold':threshold,
        'drying_endpoint_passed':bool(remaining < threshold),
        'actual_forward_count':len(result['evaluation_history'])+2,
        'forward_count_definition':'Truth plus every recorded residual evaluation including numerical differences plus final fitted readback; optimizer max_nfev is not the total forward count.',
        'elapsed_s':time.monotonic()-started,
        'limitations':'Noise-free same-model same-discretization synthetic recovery only. Parameter status remains assumed. Residual scale is not measurement uncertainty. Jacobian rank is local sensitivity, not global uniqueness. Optimizer success, window physics, parameter recovery and drying endpoint acceptance are separate results; this window makes no firing or cooled-product claim.',
    })
    write_json(out/'calibration.json',result)
    return result


def joint_drying_sensitivity(config: dict, out: Path) -> dict:
    """Evaluate forward-difference sensitivity of root-declared drying channels.

    One nominal solution is shared by all parameter perturbations and channels.
    The difference step is relative to the physical parameter, not to the
    optimizer coordinate used by fit. D uses physical parameter units; J is
    transformed to the same range-normalized coordinates as fit and uses
    observation normalization scales, not measurement sigmas.
    No optimization, noise model or derivative-convergence claim is made.
    """
    started = time.monotonic()
    window = deepcopy(config)
    window['stages'] = window['stages'][:window['stages'].index('drying')+1]
    p = window['parameters']
    keys = window['local_sensitivity_parameters']
    kinds = window['local_sensitivity_observation_kinds']
    relative_step = p['calibration.difference_step']['value']
    observations = [
        {'kind':kind, 'time_s':float(t), 'unit':UNITS[kind],
         'scale':p['calibration.scale.'+kind]['value']}
        for kind in kinds for t in p['calibration.binding.observation_times']['value']]
    nominal = {key:p[key]['value'] for key in keys}
    deltas = {key:relative_step*nominal[key] for key in keys}
    runs = []

    def evaluate(label, overrides):
        run_started = time.monotonic()
        values, report = predict(changed(window,overrides),observations)
        remaining = report['example_endpoints']['drying_remaining_fraction']
        runs.append({
            'condition':label, 'parameter_values':{**nominal, **overrides},
            'observations':[dict(row,value=float(value)) for row,value in zip(observations,values)],
            'physical_consistency_passed':report['physical_consistency_passed'],
            'window_balance':report['whole_cycle'], 'stages':report['stages'],
            'thermodynamics':report['thermodynamics'], 'state_domain':report['state_domain'],
            'dimension_check':report['dimension_check'],
            'drying_remaining_fraction':remaining,
            'drying_remaining_fraction_threshold':p['acceptance.drying_remaining_fraction']['value'],
            'drying_endpoint_passed':bool(remaining < p['acceptance.drying_remaining_fraction']['value']),
            'forward_elapsed_s':report['elapsed_s'], 'elapsed_s':time.monotonic()-run_started,
        })
        write_json(out/'joint_drying_sensitivity.progress.json',{
            'completed':False, 'actual_forward_count':len(runs), 'runs':runs})
        if not report['physical_consistency_passed']:
            raise ValueError('sensitivity forward calculation failed the declared physical consistency budget')
        return values

    baseline = evaluate('nominal', {})
    columns = []
    for key in keys:
        perturbed = evaluate(key, {key:nominal[key]+deltas[key]})
        columns.append((perturbed-baseline)/deltas[key])
    derivative = np.column_stack(columns)
    widths = np.array([p[key]['range'][1]-p[key]['range'][0] for key in keys])
    scales = np.array([row['scale'] for row in observations])
    normalized = derivative*widths[None,:]/scales[:,None]

    def matrix_diagnostics(matrix):
        singular = np.linalg.svd(matrix,compute_uv=False)
        tolerance = singular.max()*max(matrix.shape)*np.finfo(singular.dtype).eps
        denominator = np.linalg.norm(matrix[:,0])*np.linalg.norm(matrix[:,1])
        return {
            'shape':list(matrix.shape),
            'J':matrix.tolist(), 'singular_values':singular.tolist(),
            'machine_rank':int(np.linalg.matrix_rank(matrix)),
            'machine_rank_tolerance':float(tolerance),
            'condition_number':float(singular[0]/singular[-1]) if singular[-1] != 0 else None,
            'uncentered_two_column_cosine':float(matrix[:,0]@matrix[:,1]/denominator) if denominator != 0 else None,
        }

    channels = {}
    for kind in kinds:
        indices = [i for i,row in enumerate(observations) if row['kind'] == kind]
        channels[kind] = {'observation_indices':indices, **matrix_diagnostics(normalized[indices])}
    result = {
        'schema':'full_cycle_joint_drying_sensitivity_v1',
        'identity':'simulation', 'parameter_identity':'assumed',
        'scope':'Drying window only; no completed firing cycle or cooled-product result.',
        'scope_note':window['local_sensitivity_scope_note'],
        'parameters':keys, 'observation_kinds':kinds, 'observations':observations,
        'nominal_parameter_values':nominal, 'relative_step':relative_step,
        'difference_scheme':'One-sided physical-parameter relative step: delta_p=calibration.difference_step*p_nominal; transformed to the same range-normalized coordinates as fit, not the same optimizer-coordinate perturbation points.',
        'parameter_increments':deltas,
        'parameter_units':{key:p[key]['unit'] for key in keys},
        'parameter_statuses':{key:p[key]['status'] for key in keys},
        'declared_parameter_ranges':{key:p[key]['range'] for key in keys},
        'declared_parameter_range_widths':dict(zip(keys,widths.tolist())),
        'D':derivative.tolist(), 'channels':channels,
        'joint':matrix_diagnostics(normalized), 'runs':runs,
        'definitions':{
            'D':'D[i,j]=(y_plus_j[i]-y_nominal[i])/delta_parameter[j]; units are observation unit divided by parameter unit. Rows follow observations and columns follow parameters.',
            'J':'J[i,j]=D[i,j]*declared_parameter_range_width[j]/observation_scale[i]; dimensionless, using the same parameter coordinate as fit. Scales are residual normalization, not measurement uncertainty.',
            'machine_rank':'NumPy matrix_rank default: count singular values greater than max(singular_values)*max(J.shape)*machine_epsilon. The actual tolerance is reported for each matrix.',
            'condition_number':'Largest divided by smallest singular value (2-norm); null means an exactly zero smallest singular value, hence infinite condition number.',
            'uncentered_two_column_cosine':'dot(J[:,0],J[:,1])/(norm(J[:,0])*norm(J[:,1])); columns are not mean-centered. Null means a zero column norm and undefined cosine.',
        },
        'window_physical_passed':all(run['physical_consistency_passed'] for run in runs),
        'actual_forward_count':len(runs), 'elapsed_s':time.monotonic()-started,
        'limitations':'Local one-sided finite differences at the declared nominal state and discretization, without optimization. Machine rank is not a pass criterion for real material, global identifiability, noise robustness or numerical derivative convergence. Condition numbers and column cosines depend on declared coordinate and observation scaling; stacking channels does not by itself establish statistical information gain. No parameter statuses or nominal model values are updated.',
    }
    write_json(out/'joint_drying_sensitivity.json',result)
    (out/'joint_drying_sensitivity.progress.json').unlink()
    return result
