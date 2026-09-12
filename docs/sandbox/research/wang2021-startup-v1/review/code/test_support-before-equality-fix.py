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
    assert np.dot(residual, residual) == .5*(1.+(4.+9.+16.)/3.)


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
