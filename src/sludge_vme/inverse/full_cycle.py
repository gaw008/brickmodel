"""Fit specified full-cycle parameters to labelled observations, without hashes."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import least_squares

from ..models.full_cycle import make_cycle, changed, run_cycle, write_json


from .observations import UNITS, prepare_dataset
from .case_conditions import declared_case_condition_bundle, describe_case_transformation


def predict(config: dict, observations: list[dict]):
    """Run one physical solution and map its labelled observation requests."""
    report, fields = run_cycle(config)
    return map_observations(config, observations, report, fields)


def map_observations(config: dict, observations: list[dict], report: dict, fields: dict):
    """Map an existing solution without integration; return (values, report).

    report and fields must come from the supplied configuration. liquid_water
    uses fields.rows.water_kg_per_initial_dry_kg: whole-domain liquid-water
    mass divided by initial dry mass, in kg/kg, weighted by initial cell dry
    mass. Dilatometry averages local shrinkage with initial cell volumes;
    the uniform scalar path retains its original arithmetic means.
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
    dry_mass = model.total_initial_dry_mass
    curves = {'tg':np.array([r['mass_kg']/dry_mass for r in rows]),
              'dsc':np.array([r['dsc_endothermic_w_per_initial_dry_kg'] for r in rows]),
              'dilatometry':np.array([-(np.average(r['thickness_shrinkage'],weights=model.initial_partition['initial_bulk_m3']) if model.cellwise_partition else np.mean(r['thickness_shrinkage'])) for r in rows]),
              'kiln':np.array([r['kiln_temperature_k'] for r in rows]),
              'liquid_water':np.array([(np.average(r['water_kg_per_initial_dry_kg'],weights=model.cell_dry_mass) if model.cellwise_partition else np.mean(r['water_kg_per_initial_dry_kg'])) for r in rows])}
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


def forward_call_summary(report: dict) -> dict:
    """Record one actual report; ledger availability is not ledger acceptance.

    Read the gas ledger at report.gas_species_ledger. Older or non-stored-gas
    reports without that field remain explicitly missing; no ledger is inferred
    from a physical-consistency flag or a nested whole_cycle field.
    """
    ledger_present = bool(report.get('gas_species_ledger'))
    return {
        'physical_consistency_passed':report['physical_consistency_passed'],
        'maximum_balance_relative_residual':max(
            value for budget in [report['whole_cycle'], *report['stages'].values()]
            for value in budget['relative_residuals'].values()),
        'forward_elapsed_s':report['elapsed_s'],
        'gas_ledger_present':ledger_present,
        'gas_ledger_status':'present' if ledger_present else 'missing',
        'gas_ledger_source':'report.gas_species_ledger',
        'gas_ledger_diagnostic':None if ledger_present else
            'Missing or empty report.gas_species_ledger; no gas-ledger acceptance evidence is retained.',
    }


def forward_audit(report: dict) -> dict:
    """Keep independent-readback budgets without fields or another solution.

    whole_cycle covers exactly the stages in this report, including truncated
    drying windows. Availability and the input physical flag are separate; this
    function copies evidence and does not recompute or upgrade acceptance.
    """
    audit = forward_call_summary(report)
    audit.update({key:report[key] for key in (
        'whole_cycle', 'stages', 'thermodynamics', 'state_domain', 'dimension_check')})
    audit['scope'] = {
        'stages':list(report['stages']),
        'whole_cycle_meaning':'Entire declared process window; no claim for omitted stages.',
    }
    audit['gas_species_ledger'] = (report['gas_species_ledger']
        if audit['gas_ledger_present'] else None)
    return audit


def fit(config: dict, dataset: dict, out: Path, *, case_reference: str, case_transformations: list[dict]) -> dict:
    started = time.monotonic()
    dataset = prepare_dataset(config, dataset, case_reference=case_reference,
        case_transformations=case_transformations, for_calibration=True)
    kind = dataset['measurement_kind']
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
                            **forward_call_summary(report)})
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
    audit = forward_audit(forward)
    residual_rows = [dict(row,prediction=float(value),residual=float(value-row['value']),
                         normalized_residual=float((value-row['value'])/row['scale'])) for row,value in zip(rows,values)]
    result = {'schema':'sludge_vme_full_cycle_calibration_v1','measurement_kind':kind,'source':dataset['source'],
        'observation_admission':dataset['admission'],
        'case_condition_bundle':dataset['case_condition_bundle'],
        'optimizer_success':bool(opt.success),'qualified_fit':qualified,'message':opt.message,'jacobian_rank':rank,
        'parameter_count':len(keys),'fitted_parameters':fitted,'residuals':residual_rows,
        **{'forward_'+key:value for key,value in audit.items() if key != 'forward_elapsed_s'},
        'forward_elapsed_s':audit['forward_elapsed_s'],
        'forward_example_endpoints':forward['example_endpoints'],
        'forward_summary':forward['summary'],
        'normalized_rmse':float(np.sqrt(np.mean(((values-target)/scale)**2))),
        'parameter_statuses':{k:updated['parameters'][k]['status'] for k in keys},
        'evaluation_history':evaluations,'elapsed_s':time.monotonic()-started,
        'limitations':'Same-model synthetic data establish software recoverability only. A qualified fit does not establish process endpoint acceptance; see forward_example_endpoints. Jacobian rank is local identifiability, not global uniqueness. Defects/strength/absorption are unvalidated proxies; DSC is net thermal boundary power per initial dry mass in stored-gas mode, not an instrument-specific prediction.'}
    write_json(out/'calibration.json',result)
    write_json(out/'fitted.parameters.json',updated)
    (out/'calibration.progress.json').unlink()
    return result


def synthetic_demo(config: dict, out: Path, *, case_reference: str, case_transformations: list[dict]) -> dict:
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
    truth_config = changed(config, truth)
    values,truth_report = predict(truth_config,rows)
    dataset={'schema':'full_cycle_observations_v2','source_dataset_schema':'full_cycle_observations_v2','measurement_kind':'synthetic',
             'source':'Generated by this same approximate model from explicitly recorded synthetic truth; no measurement or added noise.',
             'fit_parameters':config['calibration_parameters'],'truth':truth,
             'truth_example_endpoints':truth_report['example_endpoints'],
             'truth_audit':forward_audit(truth_report),
             'observations':[dict(row,value=float(value)) for row,value in zip(rows,values)]}
    dataset['case_condition_bundle'] = declared_case_condition_bundle(config, case_reference,
        case_transformations=case_transformations)
    dataset['synthetic_truth_case_provenance'] = {
        'original_case_reference':case_reference,
        'transformations':case_transformations + [describe_case_transformation(config,truth_config,
            operation='declared same-model synthetic truth overrides')],
        'derived_saved_file':None}
    write_json(out/'synthetic.observations.json',dataset)
    result=fit(config,dataset,out,case_reference=case_reference,case_transformations=case_transformations)
    result['synthetic_parameter_relative_errors']={k:abs(result['fitted_parameters'][k]-v)/abs(v) for k,v in truth.items()}
    result['demonstration_passed']=result['qualified_fit'] and max(result['synthetic_parameter_relative_errors'].values()) < p['calibration.recovery_relative']['value']
    write_json(out/'calibration.json',result)
    return result


def binding_synthetic_demo(config: dict, out: Path, *, case_reference: str, case_transformations: list[dict]) -> dict:
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
    truth_config = changed(window, truth)
    values, truth_report = predict(truth_config,rows)
    threshold = p['acceptance.drying_remaining_fraction']['value']
    truth_remaining = truth_report['example_endpoints']['drying_remaining_fraction']
    truth_audit = forward_audit(truth_report)
    truth_audit['window_balance'] = truth_audit.pop('whole_cycle')
    truth_audit.update({
        'drying_remaining_fraction':truth_remaining,
        'drying_endpoint_passed':bool(truth_remaining < threshold),
    })
    dataset = {
        'schema':'full_cycle_observations_v2', 'source_dataset_schema':'full_cycle_observations_v2', 'measurement_kind':'synthetic',
        'source':'Same-model same-discretization synthetic liquid-water observations; no measurement or added noise.',
        'scope':'Drying window only; no completed firing cycle or cooled-product result.',
        'fit_parameters':[key], 'truth':truth, 'initial_guess':initial,
        'stages':window['stages'], 'truth_window_audit':truth_audit,
        'scale_interpretation':'Residual normalization in kg/kg, not measurement uncertainty.',
        'observations':[dict(row,value=float(value)) for row,value in zip(rows,values)],
    }
    dataset['case_condition_bundle'] = declared_case_condition_bundle(window, case_reference,
        case_transformations=case_transformations + [describe_case_transformation(config,window,
            operation='declared synthetic drying-window selection')])
    dataset['synthetic_truth_case_provenance'] = {
        'original_case_reference':case_reference,
        'transformations':case_transformations + [
            describe_case_transformation(config,window,operation='declared synthetic drying-window selection'),
            describe_case_transformation(window,truth_config,operation='declared same-model synthetic truth overrides')],
        'derived_saved_file':None}
    write_json(out/'synthetic.observations.json',dataset)
    fit_config = changed(window, initial)
    fit_transformations = case_transformations + [
        describe_case_transformation(config, window, operation='declared synthetic drying-window selection'),
        describe_case_transformation(window, fit_config, operation='declared synthetic initial parameter guess')]
    result = fit(fit_config,dataset,out,case_reference=case_reference,
        case_transformations=fit_transformations)
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


def joint_drying_sensitivity_half_step(config: dict, previous: dict, out: Path) -> dict:
    """Compare one declared smaller physical step with a saved full-step result.

    The caller supplies the preceding diagnostic for the same nominal model,
    drying window, numerical settings, parameter order, observation times and
    scales. Its nominal observations are reused without integration. Only one
    new forward per declared parameter is performed; no fit or step search.
    Column-relative differences use the saved full-step column L2 norm, never
    a single observation as denominator. This is not a convergence proof.
    """
    started = time.monotonic()
    window = deepcopy(config)
    window['stages'] = window['stages'][:window['stages'].index('drying')+1]
    p = window['parameters']
    keys = window['local_sensitivity_parameters']
    kinds = window['local_sensitivity_observation_kinds']
    observations = previous['observations']
    baseline_run = next(run for run in previous['runs'] if run['condition'] == 'nominal')
    baseline = np.array([row['value'] for row in baseline_run['observations']])
    nominal = {key:p[key]['value'] for key in keys}
    factor = p['calibration.local_sensitivity.step_factor']['value']
    relative_step = p['calibration.difference_step']['value']*factor
    deltas = {key:relative_step*nominal[key] for key in keys}
    runs = []
    columns = []
    for key in keys:
        run_started = time.monotonic()
        overrides = {key:nominal[key]+deltas[key]}
        values, report = predict(changed(window,overrides),observations)
        remaining = report['example_endpoints']['drying_remaining_fraction']
        runs.append({
            'condition':key, 'parameter_values':{**nominal, **overrides},
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
        write_json(out/'joint_drying_sensitivity_half_step.progress.json',{
            'completed':False, 'actual_forward_count':len(runs),
            'baseline_source':'Supplied preceding diagnostic nominal run; no baseline recomputation.',
            'runs':runs})
        if not report['physical_consistency_passed']:
            raise ValueError('sensitivity half-step forward calculation failed the declared physical consistency budget')
        columns.append((values-baseline)/deltas[key])
    derivative = np.column_stack(columns)
    widths = np.array([previous['declared_parameter_range_widths'][key] for key in keys])
    scales = np.array([row['scale'] for row in observations])
    normalized = derivative*widths[None,:]/scales[:,None]
    old_derivative = np.asarray(previous['D'])
    old_normalized = np.asarray(previous['joint']['J'])

    def matrix_diagnostics(matrix):
        singular = np.linalg.svd(matrix,compute_uv=False)
        tolerance = singular.max()*max(matrix.shape)*np.finfo(singular.dtype).eps
        denominator = np.linalg.norm(matrix[:,0])*np.linalg.norm(matrix[:,1])
        return {
            'shape':list(matrix.shape), 'J':matrix.tolist(),
            'singular_values':singular.tolist(),
            'machine_rank':int(np.linalg.matrix_rank(matrix)),
            'machine_rank_tolerance':float(tolerance),
            'condition_number':float(singular[0]/singular[-1]) if singular[-1] != 0 else None,
            'uncentered_two_column_cosine':float(matrix[:,0]@matrix[:,1]/denominator) if denominator != 0 else None,
        }

    def compare_columns(old, new, indices):
        comparisons = {}
        for j,key in enumerate(keys):
            old_column, new_column = old[indices,j], new[indices,j]
            difference = new_column-old_column
            old_norm = np.linalg.norm(old_column)
            changed_sign = np.sign(old_column) != np.sign(new_column)
            comparisons[key] = {
                'signed_difference':difference.tolist(),
                'absolute_difference':np.abs(difference).tolist(),
                'maximum_absolute_difference':float(np.max(np.abs(difference))),
                'full_step_column_l2_norm':float(old_norm),
                'half_step_column_l2_norm':float(np.linalg.norm(new_column)),
                'difference_l2_norm':float(np.linalg.norm(difference)),
                'relative_l2_difference':float(np.linalg.norm(difference)/old_norm) if old_norm != 0 else None,
                'full_step_sign':np.sign(old_column).tolist(),
                'half_step_sign':np.sign(new_column).tolist(),
                'sign_changed':changed_sign.tolist(),
                'sign_changed_observation_indices':[i for i,changed_sign_i in zip(indices,changed_sign) if changed_sign_i],
            }
        return comparisons

    channels = {}
    comparisons = {}
    for kind in kinds:
        indices = [i for i,row in enumerate(observations) if row['kind'] == kind]
        channels[kind] = {'observation_indices':indices, **matrix_diagnostics(normalized[indices])}
        comparisons[kind] = {
            'observation_indices':indices,
            'D_by_parameter':compare_columns(old_derivative,derivative,indices),
            'J_by_parameter':compare_columns(old_normalized,normalized,indices),
        }
    all_indices = list(range(len(observations)))
    comparisons['joint'] = {
        'observation_indices':all_indices,
        'J_by_parameter':compare_columns(old_normalized,normalized,all_indices),
    }
    result = {
        'schema':'full_cycle_joint_drying_sensitivity_half_step_v1',
        'identity':'simulation', 'scope':'One drying-window physical-step comparison only.',
        'parameters':keys, 'parameter_statuses':{key:p[key]['status'] for key in keys},
        'observations':observations, 'baseline_source':'Supplied preceding diagnostic nominal run; reused unchanged without a new forward.',
        'baseline_reuse_precondition':'Caller confirms unchanged nominal physical model, schedule, numerical settings, parameter order, observation times and scales; no new baseline is computed by this interface.',
        'nominal_parameter_values':nominal,
        'window_stages':window['stages'],
        'numerical_parameter_values':{key:item['value'] for key,item in p.items() if key.startswith('numerics.')},
        'step_factor':factor,
        'full_step':previous,
        'half_step':{
            'relative_step':relative_step, 'parameter_increments':deltas,
            'D':derivative.tolist(), 'joint':matrix_diagnostics(normalized),
            'channels':channels, 'runs':runs,
        },
        'comparisons':comparisons,
        'comparison_definitions':{
            'difference':'Half-step minus saved full-step; D retains observation-unit/parameter-unit, J is dimensionless. D and J are compared per channel and per parameter. Joint comparisons use only dimensionless J; no joint D norm is taken across unlike observation units.',
            'relative_l2_difference':'L2(half_step_column-full_step_column)/L2(full_step_column). Null denotes an exactly zero full-step column norm, so the ratio is undefined; absolute differences remain available. No pointwise relative denominator is used.',
            'sign_changed':'Exact sign-class change among -1,0,+1; includes transitions to or from zero and uses no threshold. Indices address the common full observation list.',
            'matrix_diagnostics':previous['definitions'],
        },
        'window_physical_passed':all(run['physical_consistency_passed'] for run in runs),
        'actual_forward_count':len(runs), 'reused_previous_forward_count':previous['actual_forward_count'],
        'elapsed_s':time.monotonic()-started,
        'limitations':'One halving of a one-sided physical-parameter step at fixed model, discretization and scales. No baseline recomputation, fitting, further step search, strict derivative convergence, noise robustness or real-material identification is established. Machine rank is not a pass criterion; column norms, condition numbers and cosines depend on the declared scales.',
    }
    write_json(out/'joint_drying_sensitivity_half_step.json',result)
    (out/'joint_drying_sensitivity_half_step.progress.json').unlink()
    return result


def joint_drying_synthetic_demo(config: dict, out: Path, *, case_reference: str, case_transformations: list[dict]) -> dict:
    """Recover the root-declared parameter pair from synthetic drying channels.

    One truth solution supplies all channels at elapsed-second observation
    times. A single call to the existing fit uses its unchanged optimizer,
    budgets and range-normalized coordinates. Data are noise-free and use the
    same model and discretization as fitting. Channel scales normalize the
    residuals and are not measurement-error estimates. No nominal parameter
    is updated, and synthetic fitting preserves assumed parameter identity.
    """
    started = time.monotonic()
    window = deepcopy(config)
    design = window['joint_drying_calibration']
    window['stages'] = list(design['stages'])
    p = window['parameters']
    keys = design['fit_parameters']
    kinds = design['observation_kinds']
    truth = {key:p[design['truth_parameter_entries'][key]]['value'] for key in keys}
    initial = {key:p[design['initial_parameter_entries'][key]]['value'] for key in keys}
    rows = [
        {'kind':kind, 'time_s':float(t), 'unit':UNITS[kind],
         'scale':p['calibration.scale.'+kind]['value']}
        for kind in kinds for t in p[design['observation_times_parameter']]['value']]
    truth_started = time.monotonic()
    truth_config = changed(window, truth)
    values, truth_report = predict(truth_config,rows)
    truth_elapsed = time.monotonic()-truth_started
    threshold = p['acceptance.drying_remaining_fraction']['value']
    truth_remaining = truth_report['example_endpoints']['drying_remaining_fraction']
    truth_audit = forward_audit(truth_report)
    truth_audit['window_balance'] = truth_audit.pop('whole_cycle')
    truth_audit.update({
        'drying_remaining_fraction':truth_remaining,
        'drying_endpoint_passed':bool(truth_remaining < threshold),
        'elapsed_s':truth_elapsed,
    })
    dataset = {
        'schema':'full_cycle_observations_v2', 'source_dataset_schema':'full_cycle_observations_v2', 'measurement_kind':'synthetic',
        'source':'Same-model same-discretization synthetic joint drying observations; no measurement or added noise.',
        'scope':'Drying window only; no completed firing cycle or cooled-product result.',
        'scope_note':design['scope_note'], 'design':design,
        'fit_parameters':keys, 'truth':truth, 'initial_guess':initial,
        'stages':window['stages'], 'truth_window_audit':truth_audit,
        'scale_interpretation':'Channel residual normalization in each observation unit, not measurement uncertainty.',
        'observations':[dict(row,value=float(value)) for row,value in zip(rows,values)],
    }
    dataset['case_condition_bundle'] = declared_case_condition_bundle(window, case_reference,
        case_transformations=case_transformations + [describe_case_transformation(config,window,
            operation='declared synthetic drying-window selection')])
    dataset['synthetic_truth_case_provenance'] = {
        'original_case_reference':case_reference,
        'transformations':case_transformations + [
            describe_case_transformation(config,window,operation='declared synthetic drying-window selection'),
            describe_case_transformation(window,truth_config,operation='declared same-model synthetic truth overrides')],
        'derived_saved_file':None}
    write_json(out/'synthetic.observations.json',dataset)
    fit_config = changed(window, initial)
    fit_transformations = case_transformations + [
        describe_case_transformation(config, window, operation='declared synthetic drying-window selection'),
        describe_case_transformation(window, fit_config, operation='declared synthetic initial parameter guess')]
    result = fit(fit_config,dataset,out,case_reference=case_reference,
        case_transformations=fit_transformations)
    remaining = result.pop('forward_example_endpoints')['drying_remaining_fraction']
    result.pop('forward_summary')
    result['forward_window_balance'] = result.pop('forward_whole_cycle')
    result['fit_elapsed_s'] = result['elapsed_s']
    errors = {key:abs(result['fitted_parameters'][key]-truth[key])/abs(truth[key]) for key in keys}
    recovery_threshold = p['calibration.recovery_relative']['value']
    recovered = {key:bool(error < recovery_threshold) for key,error in errors.items()}
    channel_errors = {}
    for kind in kinds:
        residuals = [row for row in result['residuals'] if row['kind'] == kind]
        physical = np.array([row['residual'] for row in residuals])
        normalized = np.array([row['normalized_residual'] for row in residuals])
        channel_errors[kind] = {
            'unit':UNITS[kind], 'observation_count':len(residuals),
            'rmse':float(np.sqrt(np.mean(physical**2))),
            'maximum_absolute_residual':float(np.max(np.abs(physical))),
            'normalized_rmse':float(np.sqrt(np.mean(normalized**2))),
            'source':'Final fitted residual rows already returned by fit; no additional forward calculation.',
        }
    result.update({
        'scope':'Drying window only; no completed firing cycle or cooled-product result.',
        'scope_note':design['scope_note'], 'design':design,
        'truth':truth, 'initial_guess':initial, 'truth_window_audit':truth_audit,
        'window_physical_passed':bool(truth_report['physical_consistency_passed']
            and result['forward_physical_consistency_passed']
            and all(row['physical_consistency_passed'] for row in result['evaluation_history'])),
        'local_rank_passed':bool(result['jacobian_rank'] == len(keys)),
        'local_rank_interpretation':'Default NumPy machine rank of the local optimizer Jacobian equals the parameter count; not a real-material identifiability criterion.',
        'synthetic_parameter_relative_errors':errors,
        'parameter_recovery_relative_threshold':recovery_threshold,
        'parameter_recovery_passed_by_parameter':recovered,
        'parameter_recovery_passed':all(recovered.values()),
        'channel_errors':channel_errors,
        'drying_remaining_fraction':remaining, 'drying_remaining_fraction_threshold':threshold,
        'drying_endpoint_passed':bool(remaining < threshold),
        'actual_forward_count':len(result['evaluation_history'])+2,
        'forward_count_definition':'One shared truth solution plus every recorded residual evaluation, including numerical differences, plus the final fitted readback. Channel error summaries use saved residuals; max_nfev is not total forward count.',
        'elapsed_s':time.monotonic()-started,
        'limitations':'One noise-free same-model same-discretization joint synthetic recovery. Parameter statuses remain assumed and nominal parameters are unchanged. Scales are residual normalization, not measurement uncertainty. Optimizer success, local Jacobian rank, window physics, parameter recovery and drying endpoint acceptance are separate results. Local machine rank does not establish real-material identification, global uniqueness or noise robustness; this window makes no firing or cooled-product claim.',
    })
    write_json(out/'calibration.json',result)
    return result
