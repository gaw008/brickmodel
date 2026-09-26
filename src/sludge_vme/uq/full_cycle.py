"""Paired Monte Carlo comparison of configured full-cycle scenarios."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from scipy.stats import norm

from ..models.full_cycle import changed, run_cycle, write_json


def compare(config: dict, out: Path) -> dict:
    started = time.monotonic()
    p = config['parameters']
    count = int(p['uq.samples']['value'])
    rng = np.random.default_rng(int(p['uq.seed']['value']))
    parameters = config['uncertain_parameters']
    draws = [{k:float(rng.uniform(*p[k]['range'])) for k in parameters} for _ in range(count)]
    records = []
    for sample, draw in enumerate(draws):
        for scenario in config['scenarios']:
            overrides = {k:v['value'] for k,v in scenario['overrides'].items()}
            if set(overrides) & set(draw):
                raise ValueError('scenario controls and uncertain material parameters overlap')
            report, _ = run_cycle(changed(config, draw | overrides))
            records.append({'sample':sample, 'scenario':scenario['id'], 'parameters':draw,
                            'summary':report['summary'], 'conservation_passed':report['conservation_passed'],
                            'physical_consistency_passed':report['physical_consistency_passed'],
                            'thermodynamics':report['thermodynamics'],
                            'worst_stage_balance':max(max(x['relative_residuals'].values()) for x in report['stages'].values())})
            write_json(out/'uncertainty.progress.json', {'completed':False,'records':records})
            print(f"UQ {len(records)}/{count*len(config['scenarios'])}: {scenario['id']}", flush=True)
    names = [s['id'] for s in config['scenarios']]
    metrics = config['ranking_metrics']
    distributions = {}
    rankings = {}
    z = float(norm.ppf((1+p['uq.confidence_level']['value'])/2))
    for metric, direction in metrics.items():
        values = np.array([[next(r['summary'][metric] for r in records if r['sample']==sample and r['scenario']==name)
                            for name in names] for sample in range(count)])
        distributions[metric] = {name:{'mean':float(values[:,i].mean()),
            'quantiles':dict(zip(map(str,p['uq.quantiles']['value']), map(float,np.quantile(values[:,i],p['uq.quantiles']['value']))))}
            for i,name in enumerate(names)}
        sign = 1 if direction == 'minimize' else -1
        medians = np.median(values,axis=0)
        order = list(np.argsort(sign*medians))
        pairwise = []
        for i in range(len(names)):
            for j in range(i+1,len(names)):
                wins = sign*values[:,i] < sign*values[:,j]
                losses = sign*values[:,j] < sign*values[:,i]
                f = float(wins.mean())
                lower = (f+z*z/(2*count)-z*np.sqrt(f*(1-f)/count+z*z/(4*count*count)))/(1+z*z/count)
                pairwise.append({'first':names[i],'second':names[j], 'first_win_fraction':f,
                    'second_win_fraction':float(losses.mean()),'tie_fraction':float((~wins & ~losses).mean()),
                    'first_win_wilson_lower_bound':float(lower),
                    'first_robustly_better':bool(lower >= p['uq.robust_fraction']['value'])})
        best = order[0]
        robust = True
        for other in order[1:]:
            fraction = float((sign*values[:,best] < sign*values[:,other]).mean())
            lower = (fraction+z*z/(2*count)-z*np.sqrt(fraction*(1-fraction)/count+z*z/(4*count*count)))/(1+z*z/count)
            robust = robust and lower >= p['uq.robust_fraction']['value']
        rankings[metric] = {'direction':direction,'order_by_median':[names[i] for i in order],
            'winner_robust_under_declared_sampling':bool(robust),'pairwise':pairwise,
            'median_ties':[[names[i],names[j]] for i in range(len(names)) for j in range(i+1,len(names)) if medians[i]==medians[j]]}
    result = {'schema':'sludge_vme_full_cycle_uq_v1','measurement_kind':'simulation',
        'sampling':'Paired iid uniform draws inside declared parameter ranges. Not experimental confidence intervals. No aggregate score across conflicting objectives.',
        'scope_note':config['uncertainty_scope_note'],
        'conditioned_parameter_values':{k:p[k]['value'] for k in config['uncertainty_fixed_parameters']},
        'samples_per_scenario':count,'scenario_count':len(names),'distributions':distributions,'rankings':rankings,
        'all_physical_consistency_passed':all(r['physical_consistency_passed'] for r in records),
        'sampled_parameter_names':parameters,
        'all_conservation_passed':all(r['conservation_passed'] for r in records),'records':records,
        'elapsed_s':time.monotonic()-started,'limitation':'Small sample ensemble is exploratory. Wilson bounds explicitly prevent calling a small unanimous sample a proven robust ranking.'}
    write_json(out/'uncertainty.json',result)
    (out/'uncertainty.progress.json').unlink()
    return result
