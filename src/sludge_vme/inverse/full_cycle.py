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
         'absorption':'kg/kg', 'strength':'Pa', 'defects':'1'}


def predict(config: dict, observations: list[dict]):
    report, fields = run_cycle(config)
    rows = fields['rows']
    time_s = np.array([r['time_s'] for r in rows])
    model = make_cycle(config)
    dry_mass = model.n*model.md
    curves = {'tg':np.array([r['mass_kg']/dry_mass for r in rows]),
              'dsc':np.array([r['dsc_endothermic_w_per_initial_dry_kg'] for r in rows]),
              'dilatometry':np.array([-np.mean(r['thickness_shrinkage']) for r in rows]),
              'kiln':np.array([r['kiln_temperature_k'] for r in rows])}
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
        if not report['physical_consistency_passed']:
            raise ValueError('calibration forward calculation failed the declared physical consistency budget')
        values = (values-target)/scale
        evaluations.append({'evaluation':len(evaluations)+1,'normalized_residual_norm':float(np.linalg.norm(values)),
                            'parameters':{k:float(v) for k,v in overrides.items()}})
        write_json(out/'calibration.progress.json',{'completed':False,'evaluation_history':evaluations})
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
        'forward_summary':forward['summary'],'forward_thermodynamics':forward['thermodynamics'],
        'normalized_rmse':float(np.sqrt(np.mean(((values-target)/scale)**2))),
        'parameter_statuses':{k:updated['parameters'][k]['status'] for k in keys},
        'evaluation_history':evaluations,'elapsed_s':time.monotonic()-started,
        'limitations':'Same-model synthetic data establish software recoverability only. Jacobian rank is local identifiability, not global uniqueness. Defects/strength/absorption are unvalidated proxies; DSC is net thermal boundary power per initial dry mass in stored-gas mode, not an instrument-specific prediction.'}
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
    values,_ = predict(changed(config,truth),rows)
    dataset={'schema':'full_cycle_observations_v1','measurement_kind':'synthetic',
             'source':'Generated by this same approximate model from explicitly recorded synthetic truth; no measurement or added noise.',
             'fit_parameters':config['calibration_parameters'],'truth':truth,
             'observations':[dict(row,value=float(value)) for row,value in zip(rows,values)]}
    write_json(out/'synthetic.observations.json',dataset)
    result=fit(config,dataset,out)
    result['synthetic_parameter_relative_errors']={k:abs(result['fitted_parameters'][k]-v)/abs(v) for k,v in truth.items()}
    result['demonstration_passed']=result['qualified_fit'] and max(result['synthetic_parameter_relative_errors'].values()) < p['calibration.recovery_relative']['value']
    write_json(out/'calibration.json',result)
    return result
