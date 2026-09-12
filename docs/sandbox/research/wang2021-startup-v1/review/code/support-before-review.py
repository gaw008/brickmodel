"""Study-specific comparisons; no material qualification or statistical inference."""
import math
import numpy as np

from wang_d1 import Parameters, mean_curve
from startup_model import startup_curve

LOWER = np.array([math.log(1e-12), math.log(1e-10), 0.])
UPPER = np.array([math.log(1e-7), math.log(1e-4), 1.5])
D1_SEED = np.array([math.log(3.3624766406072073e-9),
                    math.log(8.743254174514625e-7), 1.5])


def parameters(x):
    """Exactly map declared optimization endpoints without float overshoot."""
    values = []
    for i, (lo, hi) in enumerate(((1e-12, 1e-7), (1e-10, 1e-4))):
        values.append(lo if x[i] == LOWER[i] else hi if x[i] == UPPER[i]
                      else math.exp(float(x[i])))
    return Parameters(*values, float(x[2])*100000.)


def predictions(curves, x, tau, cells, guard, *, rtol=1e-9, atol=1e-11):
    p = parameters(x)
    values, diagnostics = [], []
    for (t, h), rows in sorted(curves.items()):
        guard()
        times = [r['time_s'] for r in rows]
        y, diagnostic = startup_curve(p, t, h/100., times, tau_s=float(tau),
            cells=cells, rtol=rtol, atol=atol, guard=guard)
        values.extend(y)
        diagnostics.append(dict(temperature_C=t, rh_percent=h, **diagnostic))
    return np.array(values), diagnostics


def weighted_residual(curves, values):
    pieces, offset = [], 0
    for rows in (rows for _, rows in sorted(curves.items())):
        n = len(rows)
        observed = np.array([r['observed'] for r in rows])
        pieces.extend((values[offset:offset+n]-observed)/math.sqrt(len(curves)*n))
        offset += n
    if offset != len(values):
        raise ValueError('prediction length differs from selected observations')
    return np.array(pieces)


def metrics(curves, values):
    points, conditions, offset = [], [], 0
    for (t, h), rows in sorted(curves.items()):
        errors = []
        for row, predicted in zip(rows, values[offset:offset+len(rows)], strict=True):
            error = float(predicted)-row['observed']
            errors.append(error)
            points.append(dict(row, temperature_C=t, rh_percent=h,
                prediction=float(predicted), residual=error,
                exceeds_readout_plus_numeric=abs(error)>row['readout_bound']+1e-6))
        conditions.append(dict(temperature_C=t, rh_percent=h, **error_metrics(errors)))
        offset += len(rows)
    if offset != len(values):
        raise ValueError('extra predictions')
    return dict(points=points, conditions=conditions,
                overall=dict(**error_metrics([r['residual'] for r in points]),
                    outside_count=sum(r['exceeds_readout_plus_numeric'] for r in points)),
                numerical_allowance=1e-6,
                qualification='readout resolution comparison, not experimental confidence')


def error_metrics(errors):
    values = np.array(errors)
    return dict(n=len(values), rmse=float(np.sqrt(np.mean(values**2))),
        mae=float(np.mean(np.abs(values))), max_abs=float(np.max(np.abs(values))),
        bias=float(np.mean(values)))


def refinement(curves, x, tau, cells, guard):
    """Observed grid/tolerance checks, not a rigorous interval error bound."""
    coarse, dc = predictions(curves, x, tau, cells//2, guard)
    middle, dm = predictions(curves, x, tau, cells, guard)
    fine, df = predictions(curves, x, tau, 2*cells, guard)
    tighter, dt = predictions(curves, x, tau, 2*cells, guard, rtol=5e-10, atol=5e-12)
    d1 = float(np.max(np.abs(middle-coarse)))
    d2 = float(np.max(np.abs(fine-middle)))
    temporal = float(np.max(np.abs(tighter-fine)))
    analytic = None
    if tau == 0:
        exact = []
        for (t, h), rows in sorted(curves.items()):
            y, _ = mean_curve(parameters(x), t, h/100.,
                [r['time_s'] for r in rows], guard=guard)
            exact.extend(y)
        analytic = float(np.max(np.abs(fine-exact)))
    contraction = d2 <= .35*d1 or max(d1, d2) <= 1e-8
    accepted = d2 <= 5e-7 and temporal <= 1e-8 and contraction
    accepted = accepted and (analytic is None or analytic <= 1e-6)
    return dict(cells=[cells//2, cells, 2*cells], coarse_delta=d1, fine_delta=d2,
        tighter_tolerance_delta=temporal, observed_contraction=contraction,
        analytic_max_abs_delta=analytic, accepted=bool(accepted),
        curve_diagnostics=[dc, dm, df, dt]), fine


def sensitivities(curves, x, tau, cells, guard):
    """Scaled local finite differences; rank diagnostics are not uniqueness proof."""
    if tau <= 0:
        raise ValueError('positive tau required for logarithmic derivative')
    point = np.r_[x, math.log(tau)]
    lower = np.r_[LOWER, math.log(30.)]
    upper = np.r_[UPPER, math.log(1200.)]
    matrices, descriptions = [], []
    for step in (1e-3, 5e-4):
        columns, schemes = [], []
        for column in range(4):
            a, b = point.copy(), point.copy()
            a[column] = max(lower[column], point[column]-step)
            b[column] = min(upper[column], point[column]+step)
            if b[column] <= a[column]:
                raise ValueError('empty sensitivity interval')
            va, _ = predictions(curves, a[:3], math.exp(a[3]), cells, guard)
            vb, _ = predictions(curves, b[:3], math.exp(b[3]), cells, guard)
            columns.append((weighted_residual(curves, vb)-weighted_residual(curves, va)) /
                           (b[column]-a[column]))
            schemes.append([float(a[column]), float(b[column])])
        jac = np.array(columns).T
        norms = np.linalg.norm(jac, axis=0)
        unit = np.divide(jac, norms, out=np.zeros_like(jac), where=norms>0)
        singular = np.linalg.svd(jac, compute_uv=False)
        normalized = np.linalg.svd(unit, compute_uv=False)
        descriptions.append(dict(step=step, perturbation_intervals=schemes,
            column_norms=norms.tolist(), scaled_singular_values=singular.tolist(),
            normalized_singular_values=normalized.tolist(),
            normalized_min_max_ratio=float(normalized[-1]/normalized[0]),
            column_cosines=(unit.T@unit).tolist(), jacobian=jac.tolist()))
        matrices.append(jac)
    relative = float(np.linalg.norm(matrices[1]-matrices[0]) /
                     max(np.linalg.norm(matrices[1]), np.finfo(float).tiny))
    ratios = [d['normalized_min_max_ratio'] for d in descriptions]
    accepted = relative <= .01 and min(ratios) >= 1e-3
    return dict(coordinates=['ln_Dref', 'ln_kref', 'Ea_over_100000', 'ln_tau_s'],
        comparisons=descriptions, step_relative_difference=relative,
        accepted=bool(accepted), qualification='local numerical screen, no statistical interval')
