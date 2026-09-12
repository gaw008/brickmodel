"""Bounded point/exact-polynomial/fake-child review; no trajectory integration."""
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.integrate._ivp.bdf import BdfDenseOutput


SUBJECT = Path('/Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research/cooling-spatial-v1')


def load(name):
    spec = importlib.util.spec_from_file_location('independent_spatial_' + name, SUBJECT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


d = load('run_spatial')
s = load('supervise')


def candidate_augmented_rhs(model, temperature):
    result = model.evaluate(temperature)
    return np.r_[result.temperature_rates_k_s, result.cell_heat_in_w,
                 result.cell_mechanical_power_w, result.total_entropy_production_w_k]


@pytest.mark.parametrize('n', [16, 32, 64])
@pytest.mark.parametrize('direction_kind', ['common', 'mixed'])
def test_jacobian_matches_actual_candidate_at_off_grid_manufactured_state(n, direction_kind):
    system = d.SpatialSystem(n)
    position = (np.arange(n) + .5) / n
    temperature = 300.7 + 1.3 * np.cos(3 * np.pi * position) + .2 * np.sin(4 * np.pi * position)
    direction = (np.ones(n) if direction_kind == 'common' else
                 .2 + np.cos(5 * np.pi * position) + .3 * np.sin(2 * np.pi * position))
    jacobian = system.jacobian(temperature).toarray()
    assert np.array_equal(jacobian[:, n:], np.zeros((3 * n + 1, 2 * n + 1)))
    derivative = jacobian[:, :n] @ direction
    estimates = []
    for delta in (.01, .005):
        estimates.append((candidate_augmented_rhs(system.model, temperature + delta * direction)
                          - candidate_augmented_rhs(system.model, temperature - delta * direction)) / (2 * delta))
    richardson = (4 * estimates[1] - estimates[0]) / 3
    # Candidate arithmetic and independent analytic solve, including all Q/P/S rows.
    np.testing.assert_allclose(derivative, richardson, rtol=2e-7, atol=2e-8)
    # Also check each physical block at its own scale: the common-direction
    # power derivative is about 1e-11 and cannot be covered by a 1e-8 floor.
    for start, stop in ((0, n), (n, 2 * n), (2 * n, 3 * n), (3 * n, 3 * n + 1)):
        scale = float(np.max(np.abs(derivative[start:stop])))
        error = float(np.max(np.abs(derivative[start:stop] - richardson[start:stop])))
        assert error <= 1e-6 * scale


def multiply_exact(left, right):
    possibilities = [a * b for a in left for b in right]
    return min(possibilities), max(possibilities)


@pytest.mark.parametrize('order', [1, 2, 3, 4, 5])
def test_dense_bounds_cover_exact_rational_whole_interval(order):
    n, size = 16, 49
    left, right, h = 1.13, 1.151, .031
    coefficients = np.zeros((order + 1, size))
    coefficients[0, :n] = 300. + np.arange(n) / 13.
    for row in range(1, order + 1):
        coefficients[row, :n] = (-1.) ** (np.arange(n) + row) * (np.arange(n) + 1.) / (17. * row)
    dense = BdfDenseOutput(left, right, h, order, coefficients)
    envelope = d.dense_envelope(dense, n, size, left, right)
    bounds = envelope['temperature_bounds_k']
    # Exact Fraction arithmetic bounds the stored Newton polynomial for every
    # real time in [left,right]; it does not substitute time samples for a proof.
    for cell in range(n):
        lower = upper = Fraction(float(coefficients[0, cell]))
        product = (Fraction(1), Fraction(1))
        for row in range(order):
            shift, denominator = Fraction(float(dense.t_shift[row])), Fraction(float(dense.denom[row]))
            factor = ((Fraction(left) - shift) / denominator,
                      (Fraction(right) - shift) / denominator)
            product = multiply_exact(product, factor)
            coefficient = Fraction(float(coefficients[row + 1, cell]))
            term = multiply_exact(product, (coefficient, coefficient))
            lower += term[0]
            upper += term[1]
        assert Fraction(bounds[0][cell]) <= lower
        assert Fraction(bounds[1][cell]) >= upper
    # Separate finite check of the actual SciPy binary64 evaluation path.
    observed = dense(np.linspace(left, right, 49))[:n]
    assert np.all(observed >= np.asarray(bounds[0])[:, None])
    assert np.all(observed <= np.asarray(bounds[1])[:, None])


@pytest.mark.parametrize('failure_kind,exit_code', [('post_hash', 7), ('prefix_utf8', 0), ('worker_list', 0)])
def test_post_child_read_errors_keep_terminal_record(tmp_path, monkeypatch, failure_kind, exit_code):
    original_hashes = s.hashes
    calls = 0

    def hashes(paths):
        nonlocal calls
        calls += 1
        if calls == 2 and failure_kind == 'post_hash':
            raise FileNotFoundError('independent manufactured post-child read failure')
        return original_hashes(paths)

    monkeypatch.setattr(s, 'hashes', hashes)
    output = tmp_path / 'supervision'

    def child(command, **kwargs):
        assert kwargs['timeout'] == 29.5
        assert command[command.index('--deadline-monotonic') + 1] == '130.0'
        worker = Path(command[command.index('--output') + 1])
        (worker / 'coarse').mkdir(parents=True)
        prefix = json.dumps({'time_s': 0., 'state': [302.] * 16 + [0.] * 33}) + '\n'
        (worker / 'coarse' / 'accepted.jsonl').write_bytes(
            prefix.encode() if failure_kind != 'prefix_utf8' else b'\xff\n')
        (worker / 'result.json').write_text(json.dumps(
            [] if failure_kind == 'worker_list' else {'status': 'completed', 'real_time_integration': True}))
        return SimpleNamespace(returncode=exit_code)

    ticks = iter([100., 100.5, 101., 101.01])
    record = s.supervise('/independent/fake-python', 16, output,
                         run_child=child, clock=lambda: next(ticks))
    saved = json.loads((output / 'EXECUTION.json').read_text())
    assert saved == record
    assert record['returncode'] == exit_code
    assert record['child_reaped'] is True
    assert record['timed_out'] is False
    assert record['passed'] is False
    if failure_kind != 'prefix_utf8':
        assert record['accepted_prefixes']['coarse']['count'] == 1
