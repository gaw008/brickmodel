"""Finite training-only startup profile, then conditional four-parameter fit.

This program never parses the previously exposed 50 C observations.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
D1 = HERE.parents[1]/'wang2021-drying-holdout-v1'/'reproduce'
sys.path[:0] = [str(HERE), str(D1)]

import numpy as np
import scipy
from scipy.optimize import least_squares
from study_io import load_curves, save
from study_support import (D1_SEED, LOWER, UPPER, parameters, predictions,
                           weighted_residual, metrics, refinement, sensitivities)

TAUS = (0., 30., 60., 120., 300., 600., 1200.)
MAX_WALL_S = 600.
MAX_RESIDUAL_CALLS = 1500


def input_binding(csv_path):
    files = [csv_path, HERE.parent/'PREREGISTRATION.md',
             HERE/'startup_model.py', HERE/'study_support.py', HERE/'probe.py',
             D1/'wang_d1.py', D1/'study_io.py']
    return dict(files={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in files}, python=platform.python_version(),
                numpy=np.__version__, scipy=scipy.__version__)


class Study:
    def __init__(self, curves, output, began):
        self.curves, self.output, self.began = curves, output, began
        self.calls_attempted = 0
        self.calls_completed = 0
        self.cells = None
        self.result = dict(status='started', profiles=[], initial_numerical_checks=[],
            holdout_values_parsed=False, training_n=sum(map(len, curves.values())),
            policy=dict(total_wall_s=MAX_WALL_S, max_residual_calls=MAX_RESIDUAL_CALLS,
                        max_nfev_per_fit=60, tau_grid_s=TAUS))

    def guard(self):
        if time.monotonic()-self.began >= MAX_WALL_S:
            raise TimeoutError('original total study wall budget exhausted')

    def checkpoint(self):
        self.result.update(elapsed_seconds=time.monotonic()-self.began,
            residual_calls_attempted=self.calls_attempted,
            residual_calls_completed=self.calls_completed)
        save(self.output/'study.json', self.result)

    def residual(self, x, tau):
        self.guard()
        if self.calls_attempted >= MAX_RESIDUAL_CALLS:
            raise RuntimeError('original total residual call budget exhausted')
        self.calls_attempted += 1
        y, _ = predictions(self.curves, x, tau, self.cells, self.guard)
        answer = weighted_residual(self.curves, y)
        self.calls_completed += 1
        return answer

    def select_grid(self):
        for cells in (64, 128, 256, 512):
            checks = []
            for tau in (0., 600., 1200.):
                check, _ = refinement(self.curves, D1_SEED, tau, cells, self.guard)
                checks.append(dict(tau_s=tau, **check))
            self.result['initial_numerical_checks'].append(dict(cells=cells, checks=checks))
            self.checkpoint()
            if all(check['accepted'] for check in checks):
                self.cells = cells
                self.result['optimization_cells'] = cells
                return
        raise ValueError('predeclared grid ladder failed before optimization')

    def fit(self, initial, tau, label, *, joint=False):
        record = dict(label=label, initial=np.asarray(initial).tolist(),
                      fixed_tau_s=tau, status='started')
        self.result['profiles'].append(record)
        self.checkpoint()
        began = time.monotonic()
        start_calls = self.calls_attempted
        lower = np.r_[LOWER, math.log(30.)] if joint else LOWER
        upper = np.r_[UPPER, math.log(1200.)] if joint else UPPER

        def residual(x):
            return self.residual(x[:3], math.exp(x[3]) if joint else tau)

        def jacobian(x):
            columns = []
            for i in range(len(x)):
                a, b = x.copy(), x.copy()
                a[i] = max(lower[i], x[i]-5e-4)
                b[i] = min(upper[i], x[i]+5e-4)
                columns.append((residual(b)-residual(a))/(b[i]-a[i]))
            return np.array(columns).T

        try:
            fit = least_squares(residual, initial, jac=jacobian,
                bounds=(lower, upper), max_nfev=60,
                xtol=1e-7, ftol=1e-7, gtol=1e-7)
            self.guard()
            fitted_tau = math.exp(fit.x[3]) if joint else tau
            check, fine = refinement(self.curves, fit.x[:3], fitted_tau,
                                     self.cells, self.guard)
            objective = float(np.dot(fit.fun, fit.fun))
            fine_r = weighted_residual(self.curves, fine)
            fine_objective = float(np.dot(fine_r, fine_r))
            record.update(status='converged' if fit.success else 'not_converged',
                x=fit.x.tolist(), parameters=vars(parameters(fit.x[:3])),
                tau_s=fitted_tau, objective=objective, fine_objective=fine_objective,
                nfev=fit.nfev, njev=fit.njev, termination=str(fit.message),
                optimality=float(fit.optimality), active_mask=fit.active_mask.tolist(),
                near_search_boundary=bool(np.any(np.minimum(fit.x-lower, upper-fit.x)<=1e-6)),
                numerical_check=check)
            save(self.output/(label+'-training.json'),
                 metrics(self.curves, fine, numerical_checked=check['accepted']))
            if not check['accepted']:
                raise ValueError('profile numerical comparison failed at fitted parameters')
        except Exception as exc:
            record.update(status='failed', reason=type(exc).__name__+': '+str(exc))
            raise
        finally:
            record.update(elapsed_seconds=time.monotonic()-began,
                          residual_calls=self.calls_attempted-start_calls)
            self.checkpoint()
        print(json.dumps(dict(label=label, tau_s=fitted_tau,
            objective=fine_objective, elapsed_s=record['elapsed_seconds'])), flush=True)
        return record

    def execute(self):
        self.select_grid()
        profiles = [self.fit(D1_SEED, tau, 'tau-'+str(int(tau))) for tau in TAUS]
        if not all(r['status'] == 'converged' for r in profiles):
            self.result.update(status='profile_not_converged_no_freeze')
            return
        best_index = min(range(len(profiles)), key=lambda i:(profiles[i]['fine_objective'], i))
        best = profiles[best_index]
        self.result['selected_profile'] = best['label']
        if best_index in (0, 1, len(profiles)-1):
            self.result.update(status='profile_boundary_no_freeze',
                reason='lowest grid objective at zero or positive search edge; no range expansion')
            return
        gap = min(profiles[best_index-1]['fine_objective'],
                  profiles[best_index+1]['fine_objective'])-best['fine_objective']
        self.result['profile_neighbor_gap'] = gap
        if gap <= 1e-6:
            self.result.update(status='profile_flat_no_freeze')
            return
        alternate = self.fit(np.array([math.log(1e-8), math.log(1e-6), .4]),
                             best['tau_s'], 'selected-alternate')
        if alternate['status'] != 'converged':
            self.result.update(status='alternate_not_converged_no_freeze')
            return
        if abs(alternate['fine_objective']-best['fine_objective']) > 1e-6:
            self.result.update(status='start_sensitive_no_freeze')
            return
        best = min((best, alternate), key=lambda r:r['fine_objective'])
        diagnostic = sensitivities(self.curves, np.array(best['x']),
            best['tau_s'], self.cells, self.guard)
        self.result['selected_sensitivity'] = diagnostic
        self.checkpoint()
        if not diagnostic['accepted']:
            self.result.update(status='locally_unresolved_no_freeze')
            return
        joint = self.fit(np.r_[best['x'], math.log(best['tau_s'])], None,
                         'joint', joint=True)
        if joint['status'] != 'converged' or joint['near_search_boundary']:
            self.result.update(status='joint_unresolved_no_freeze')
            return
        diagnostic = sensitivities(self.curves, np.array(joint['x'][:3]),
                                   joint['tau_s'], self.cells, self.guard)
        self.result['joint_sensitivity'] = diagnostic
        if not diagnostic['accepted']:
            self.result.update(status='joint_locally_unresolved_no_freeze')
            return
        self.result.update(status='training_screen_complete_pending_review',
            candidate_parameters=joint['parameters'], candidate_tau_s=joint['tau_s'],
            qualification='candidate only; separate reviewed lock required before reused condition evaluation')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=False, exist_ok=False)
    began = time.monotonic()
    original = input_binding(Path(args.csv))
    save(output/'binding.json', original)
    study = None
    try:
        curves = load_curves(args.csv, (40, 60))
        if sum(map(len, curves.values())) != 117:
            raise ValueError('original 117 training observations required')
        study = Study(curves, output, began)
        study.execute()
        if input_binding(Path(args.csv)) != original:
            raise ValueError('input or runtime changed during study')
        study.result['inputs_unchanged'] = True
        study.checkpoint()
    except Exception as exc:
        failure = dict(status='execution_failed_no_freeze',
            reason=type(exc).__name__+': '+str(exc), traceback=traceback.format_exc())
        if study is not None:
            study.result.update(failure)
            study.checkpoint()
        else:
            save(output/'failure.json', failure)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
