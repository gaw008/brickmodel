"""Manufactured support-gate probes only; no CSV or PDE solver execution."""
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import types

import numpy as np

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT/'docs/sandbox/research/wang2021-drying-holdout-v1/reproduce'))
stub = types.ModuleType('startup_model')


def forbidden_solver(*args, **kwargs):
    raise AssertionError('a support-only probe must not call the PDE solver')


stub.startup_curve = forbidden_solver
sys.modules['startup_model'] = stub
target = Path(os.environ.get('SUPPORT_REVIEW_TARGET', str(HERE/'support-before-review.py')))
spec = importlib.util.spec_from_file_location('reviewed_support', target)
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def test_optimizer_endpoints_map_to_exact_original_box():
    lower = support.parameters(support.LOWER)
    upper = support.parameters(support.UPPER)
    assert (lower.dref, lower.kref, lower.ea) == (1e-12, 1e-10, 0.)
    assert (upper.dref, upper.kref, upper.ea) == (1e-7, 1e-4, 150000.)


def test_weighting_is_per_curve_equal_not_per_point_equal():
    curves = {(40, 30): [dict(observed=0.)],
              (60, 30): [dict(observed=0.) for _ in range(3)]}
    residual = support.weighted_residual(curves, np.array([1., 2., 3., 4.]))
    assert math.isclose(float(np.dot(residual, residual)), .5*(1.+(4.+9.+16.)/3.), rel_tol=1e-15)


def test_column_normalization_does_not_pass_unresolvable_weak_direction(monkeypatch, tmp_path):
    # This is a manufactured local response map, not a drying model or data fit.
    curves = {(40, 30): [dict(observed=0.) for _ in range(4)]}
    scales = np.array([1., 1., 1., 1e-12])

    def predict(curves, x, tau, cells, guard, **kwargs):
        return scales*np.r_[x, math.log(tau)], []

    monkeypatch.setattr(support, 'predictions', predict)
    result = support.sensitivities(curves, np.array([-20., -14., .8]), 300., 32, lambda: None)
    singular = result['comparisons'][0]['scaled_singular_values']
    observed = dict(accepted=result['accepted'], raw_condition=singular[0]/singular[-1],
                    result=result)
    (tmp_path/'WEAK_DIRECTION.json').write_text(json.dumps(observed, indent=2)+'\n')
    assert not result['accepted'], 'normalized columns hide a raw condition number of approximately 1e12'


def test_grid_agreement_does_not_admit_known_mass_balance_failure(monkeypatch, tmp_path):
    curves = {(40, 30): [dict(observed=.9, time_s=60.)]}

    def corrupted_output(p, t, h, times, **kwargs):
        return np.ones(len(times)), dict(mass_balance_max_abs=.125,
            cell_min=1., cell_max=1., mean_increase_max=0.)

    monkeypatch.setattr(support, 'startup_curve', corrupted_output)
    try:
        result, _ = support.refinement(curves, support.D1_SEED, 600., 64, lambda: None)
    except ValueError:
        return
    (tmp_path/'BAD_MASS_GATE.json').write_text(json.dumps(result, indent=2)+'\n')
    assert not result['accepted'], 'grid agreement must not override a reported 0.125 mass defect'


def test_zero_spectrum_is_serializable_unresolved(monkeypatch):
    curves = {(40, 30): [dict(observed=0.) for _ in range(4)]}
    monkeypatch.setattr(support, 'predictions', lambda *args, **kwargs: (np.zeros(4), []))
    result = support.sensitivities(curves, np.array([-20., -14., .8]), 300., 32, lambda: None)
    assert not result['accepted']
    json.dumps(result, allow_nan=False)


def test_one_sided_sensitivity_intervals_stay_in_original_box(monkeypatch):
    curves = {(40, 30): [dict(observed=0.) for _ in range(4)]}
    seen = []

    def predict(curves, x, tau, cells, guard, **kwargs):
        q = np.r_[x, math.log(tau)]
        seen.append(q)
        return q, []

    monkeypatch.setattr(support, 'predictions', predict)
    support.sensitivities(curves, support.LOWER.copy(), 30., 32, lambda: None)
    for point in seen:
        assert np.all(point >= np.r_[support.LOWER, math.log(30.)])
        assert np.all(point <= np.r_[support.UPPER, math.log(1200.)])


def test_jacobian_error_uses_all_three_pairs(monkeypatch, tmp_path):
    curves = {(40, 30): [dict(observed=0.) for _ in range(4)]}
    calls = 0

    def predict(curves, x, tau, cells, guard, **kwargs):
        nonlocal calls
        group = calls // 8
        calls += 1
        # Three manufactured numerical response approximations with errors
        # in the same direction; their endpoint difference is the largest.
        scale = np.array([100., 100., 100., 1. + .09*group])
        return scale*np.r_[x, math.log(tau)], []

    monkeypatch.setattr(support, 'predictions', predict)
    result = support.sensitivities(curves, np.array([-20., -14., .8]), 300., 32, lambda: None)
    matrices = [np.array(item['jacobian']) for item in result['comparisons']]
    all_pairs = max(float(np.linalg.norm(matrices[i]-matrices[j], ord=2))
                    for i in range(3) for j in range(i))
    (tmp_path/'PAIRWISE_ERROR.json').write_text(json.dumps(dict(result=result, all_pairs=all_pairs), indent=2)+'\n')
    assert math.isclose(result['observed_jacobian_error'], all_pairs, rel_tol=1e-12)
    assert not result['accepted']
