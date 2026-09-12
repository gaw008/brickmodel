"""Passive audit of execution01 only; standard library, no model imports."""
import csv
import hashlib
import json
import math
from pathlib import Path
import time

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
RUN = Path('/private/tmp/brick-wang-startup-v1/execution01')
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a, b, *, tol=2e-12):
    assert math.isclose(a, b, rel_tol=tol, abs_tol=tol), (a, b)


def stats(errors):
    n = len(errors)
    return dict(n=n, rmse=math.sqrt(math.fsum(x*x for x in errors)/n),
                mae=math.fsum(map(abs, errors))/n,
                max_abs=max(map(abs, errors)), bias=math.fsum(errors)/n)


def singular_values(matrix):
    """Four-column Gram eigenvalues using Jacobi rotations, independent of NumPy."""
    a = [[math.fsum(row[i]*row[j] for row in matrix) for j in range(4)] for i in range(4)]
    for _ in range(200):
        p, q = max(((i, j) for i in range(4) for j in range(i+1, 4)), key=lambda ij: abs(a[ij[0]][ij[1]]))
        if abs(a[p][q]) < max(abs(a[i][i]) for i in range(4))*1e-16:
            break
        angle = .5*math.atan2(2*a[p][q], a[q][q]-a[p][p])
        c, s = math.cos(angle), math.sin(angle)
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        a[p][p] = c*c*app - 2*c*s*apq + s*s*aqq
        a[q][q] = s*s*app + 2*c*s*apq + c*c*aqq
        a[p][q] = a[q][p] = 0.
        for k in range(4):
            if k not in (p, q):
                akp, akq = a[k][p], a[k][q]
                a[k][p] = a[p][k] = c*akp-s*akq
                a[k][q] = a[q][k] = s*akp+c*akq
    return sorted((math.sqrt(max(0., a[i][i])) for i in range(4)), reverse=True)


def check_numerics(check, cells, tau, curves):
    assert check['cells'] == [cells//2, cells, 2*cells]
    groups = check['curve_diagnostics']
    assert len(groups) == 4
    for g, items in enumerate(groups):
        assert len(items) == 8
        for item, key in zip(items, sorted(curves), strict=True):
            assert (item['temperature_C'], item['rh_percent']) == key
            assert item['cells'] == (cells//2, cells, 2*cells, 2*cells)[g]
            close(item['tau_s'], tau)
            close(item['rtol'], (1e-9, 1e-9, 1e-9, 5e-10)[g], tol=1e-20)
            close(item['atol'], (1e-11, 1e-11, 1e-11, 5e-12)[g], tol=1e-22)
            assert len(item['cumulative_outflow_at_times']) == len(curves[key])
            assert item['solver_ran'] and item['solver_status'] == 0
            assert item['diagnostic_scope'] == 'accepted_steps_and_requested_times'
            assert 0. <= item['mass_balance_max_abs'] <= 1e-9
            assert item['cell_min'] >= -1e-9 and item['cell_max'] <= 1+1e-9
            assert 0. <= item['mean_increase_max'] <= 1e-9
    # Independently stored cumulative fluxes constrain MR differences via the
    # recorded mass residual. This checks consistency, not missing cell states.
    for field, first, second in [('coarse_delta', 0, 1), ('fine_delta', 1, 2), ('tighter_tolerance_delta', 2, 3)]:
        delta = max(abs(a-b) for left, right in zip(groups[first], groups[second], strict=True)
                    for a, b in zip(left['cumulative_outflow_at_times'], right['cumulative_outflow_at_times'], strict=True))
        bound = max(x['mass_balance_max_abs'] for x in groups[first])+max(x['mass_balance_max_abs'] for x in groups[second])
        assert abs(delta-check[field]) <= bound+2e-15, (field, delta, check[field], bound)
    d1, d2 = check['coarse_delta'], check['fine_delta']
    contraction = d2 <= .35*d1 or max(d1, d2) <= 1e-8
    assert check['observed_contraction'] == contraction
    accepted = d2 <= 5e-7 and check['tighter_tolerance_delta'] <= 1e-8 and contraction
    assert (check['analytic_max_abs_delta'] is None) == (tau != 0.)
    if tau == 0.:
        accepted = accepted and check['analytic_max_abs_delta'] <= 1e-6
    assert check['accepted'] == accepted
    return accepted


def main():
    began = time.perf_counter()
    start, end = read(RUN/'supervisor-start.json'), read(RUN/'supervisor-end.json')
    study, binding = read(RUN/'training/study.json'), read(RUN/'training/binding.json')
    assert end['returncode'] == 0 and end['child_reaped'] and not end['timed_out']
    assert end['hard_timeout_s'] == 630 and end['elapsed_seconds'] < 630
    assert start['inputs_before'] == end['inputs_before'] == end['inputs_after']
    for path, digest in end['inputs_before'].items():
        assert sha(Path(path)) == digest, path
    for path, digest in binding['files'].items():
        assert end['inputs_before'][path] == digest
    freeze = read(ROOT/'docs/sandbox/research/wang2021-startup-v1/review/code/REVIEW_FREEZE.json')
    for path, digest in freeze['source_sha256'].items():
        assert end['inputs_before'][str(ROOT/path)] == digest
    assert end['inputs_unchanged'] and study['inputs_unchanged']
    csv_path = Path(next(path for path in binding['files'] if path.endswith('.csv')))
    curves = {}
    skipped_t0 = 0
    with csv_path.open(newline='') as stream:
        header = next(csv.reader([next(stream)]))
        index = header.index('temperature_C')
        for line in stream:
            # Only inspect the temperature token of excluded raw lines.
            if line.split(',')[index] not in ('40', '60'):
                continue
            row = dict(zip(header, next(csv.reader([line])), strict=True))
            if float(row['time_min']) == 0.:
                skipped_t0 += 1
                continue
            key = (int(row['temperature_C']), int(row['relative_humidity_percent']))
            curves.setdefault(key, []).append(row)
    assert len(curves) == 8 and sum(map(len, curves.values())) == 117 and skipped_t0 == 8
    assert study['training_n'] == 117 and study['holdout_values_parsed'] is False
    expected_labels = ['tau-'+str(t) for t in (0, 30, 60, 120, 300, 600, 1200)]+['selected-alternate', 'joint']
    profiles = study['profiles']
    assert [p['label'] for p in profiles] == expected_labels
    assert study['optimization_cells'] == 512
    assert [x['cells'] for x in study['initial_numerical_checks']] == [64, 128, 256, 512]
    for grid in study['initial_numerical_checks']:
        passed = [check_numerics(c, grid['cells'], c['tau_s'], curves) for c in grid['checks']]
        assert all(passed) == (grid['cells'] == 512)
    assert study['policy'] == dict(total_wall_s=600., max_residual_calls=1500, max_nfev_per_fit=60,
                                   tau_grid_s=[0., 30., 60., 120., 300., 600., 1200.])
    assert study['elapsed_seconds'] < 600 and study['elapsed_seconds'] <= end['elapsed_seconds']
    assert sum(p['residual_calls'] for p in profiles) == study['residual_calls_attempted'] == study['residual_calls_completed'] == 391
    rows_out = []
    stdout = [json.loads(line) for line in (RUN/'stdout.log').read_text().splitlines()]
    assert len(stdout) == 9 and not (RUN/'stderr.log').read_bytes()
    for profile, logged in zip(profiles, stdout, strict=True):
        label = profile['label']
        assert profile['status'] == 'converged' and profile['nfev'] <= 60
        dimensions = 4 if label == 'joint' else 3
        assert profile['residual_calls'] == profile['nfev']+2*dimensions*profile['njev']
        assert check_numerics(profile['numerical_check'], 512, profile['tau_s'], curves)
        assert logged['label'] == label
        close(logged['objective'], profile['fine_objective'])
        report = read(RUN/'training'/f'{label}-training.json')
        assert report['numerical_check_passed'] is True and report['numerical_allowance'] == 1e-6
        expected = [(key, row) for key in sorted(curves) for row in curves[key]]
        errors_by_curve = {key: [] for key in curves}
        outside = 0
        for (key, source), point in zip(expected, report['points'], strict=True):
            for field, value in source.items():
                assert point[field] == (int(value) if field == 'temperature_C' else value), (label, field)
            assert point['rh_percent'] == key[1]
            close(point['time_s'], float(source['time_min'])*60)
            close(point['observed'], float(source['moisture_ratio']))
            close(point['readout_bound'], float(source['readout_bound_MR']))
            error = point['prediction']-float(source['moisture_ratio'])
            close(error, point['residual'])
            errors_by_curve[key].append(error)
            exceeded = abs(error) > float(source['readout_bound_MR'])+1e-6
            assert point['exceeds_readout_plus_numeric'] == exceeded
            outside += exceeded
        errors = [x for key in sorted(curves) for x in errors_by_curve[key]]
        for k, value in stats(errors).items():
            close(value, report['overall'][k])
        assert report['overall']['outside_count'] == outside
        for condition in report['conditions']:
            key = (condition['temperature_C'], condition['rh_percent'])
            for k, value in stats(errors_by_curve[key]).items():
                close(value, condition[k])
        objective = math.fsum(math.fsum(x*x for x in errors_by_curve[key])/len(errors_by_curve[key]) for key in curves)/8
        close(objective, profile['fine_objective'])
        flat_q = [q for d in profile['numerical_check']['curve_diagnostics'][2] for q in d['cumulative_outflow_at_times']]
        max_balance = max(abs(point['prediction']+q-1) for point, q in zip(report['points'], flat_q, strict=True))
        assert max_balance <= max(d['mass_balance_max_abs'] for d in profile['numerical_check']['curve_diagnostics'][2])+2e-15
        rows_out.append(dict(label=label, tau_s=profile['tau_s'], curve_equal_mse=objective,
                             **stats(errors), outside_count=outside, direct_saved_mass_error=max_balance))
    best_index = min(range(7), key=lambda i: (rows_out[i]['curve_equal_mse'], i))
    assert best_index == 5 and study['selected_profile'] == 'tau-600'
    gap = min(rows_out[4]['curve_equal_mse'], rows_out[6]['curve_equal_mse'])-rows_out[5]['curve_equal_mse']
    close(gap, study['profile_neighbor_gap'])
    assert gap > 1e-6 and abs(rows_out[5]['curve_equal_mse']-rows_out[7]['curve_equal_mse']) <= 1e-6
    sensitivity = study['selected_sensitivity']
    matrices = [c['jacobian'] for c in sensitivity['comparisons']]
    results = []
    for comparison, matrix in zip(sensitivity['comparisons'], matrices, strict=True):
        assert len(matrix) == 117 and all(len(row) == 4 for row in matrix)
        norms = [math.sqrt(math.fsum(row[j]**2 for row in matrix)) for j in range(4)]
        raw = singular_values(matrix)
        normal = singular_values([[row[j]/norms[j] for j in range(4)] for row in matrix])
        for a, b in zip(norms, comparison['column_norms'], strict=True):
            close(a, b)
        for actual, recorded in [(raw, comparison['scaled_singular_values']), (normal, comparison['normalized_singular_values'])]:
            for a, b in zip(actual, recorded, strict=True):
                close(a, b, tol=2e-9)
        close(raw[0]/raw[-1], comparison['scaled_condition_number'], tol=2e-9)
        close(normal[-1]/normal[0], comparison['normalized_min_max_ratio'], tol=2e-9)
        results.append(dict(raw_condition=raw[0]/raw[-1], normalized_ratio=normal[-1]/normal[0], smallest=raw[-1]))
    differences = [[[a-b for a, b in zip(ra, rb, strict=True)] for ra, rb in zip(matrices[i], matrices[j], strict=True)]
                   for i, j in ((1, 0), (2, 1), (2, 0))]
    epsilon = max(singular_values(diff)[0] for diff in differences)
    relative = math.sqrt(math.fsum(v*v for row in differences[0] for v in row)/math.fsum(v*v for row in matrices[1] for v in row))
    close(epsilon, sensitivity['observed_jacobian_error'])
    close(relative, sensitivity['step_relative_difference'])
    assert relative <= .01 and all(r['raw_condition'] <= 1e6 and r['normalized_ratio'] >= 1e-3 for r in results)
    assert results[-1]['smallest'] > 10*epsilon and sensitivity['accepted']
    joint = profiles[-1]
    lower = [math.log(1e-12), math.log(1e-10), 0., math.log(30.)]
    upper = [math.log(1e-7), math.log(1e-4), 1.5, math.log(1200.)]
    distances = [min(x-a, b-x) for x, a, b in zip(joint['x'], lower, upper, strict=True)]
    assert joint['near_search_boundary'] and distances[2] <= 1e-6
    close(joint['parameters']['ea'], joint['x'][2]*100000.)
    close(joint['tau_s'], math.exp(joint['x'][3]))
    assert joint['active_mask'][2] == 1 and study['status'] == 'joint_unresolved_no_freeze'
    assert not any(k in study for k in ['joint_sensitivity', 'candidate_parameters', 'candidate_tau_s'])
    assert {p.name for p in (RUN/'training').iterdir()} == {'binding.json', 'study.json'} | {label+'-training.json' for label in expected_labels}
    output = dict(verdict='saved_evidence_consistent_candidate_stopped_at_joint_boundary',
        source_binding_count=len(end['inputs_before']), training_points=117, selected_t0_excluded=skipped_t0,
        profiles=rows_out, selected_sensitivity_recomputed=results, selected_sensitivity_epsilon=epsilon,
        joint_boundary_coordinate='Ea_over_100000', joint_boundary_distance=distances[2],
        joint_sensitivity_present=False, joint_ea_J_mol=joint['parameters']['ea'], joint_tau_s=joint['tau_s'],
        residual_calls=391, internal_seconds=study['elapsed_seconds'], supervisor_seconds=end['elapsed_seconds'],
        input_sha256=end['inputs_after'], saved_sha256={str(p.relative_to(RUN)):sha(p) for p in sorted(RUN.rglob('*')) if p.is_file()},
        audit_seconds=time.perf_counter()-began,
        limitations=['Saved metrics and cumulative outflows are checked; missing full cell/accepted-step arrays cannot be independently replayed.',
                     'No solver, optimizer or application module imported; no independent recomputation of forward predictions.',
                     'Runtime versions and process timing are saved records; not independently measured during the original run.',
                     '50 C excluded line values were not parsed; opaque whole-file hashing remains necessary.',
                     'The passing local sensitivity is at the selected tau=600 s profile, not the joint solution.'])
    (HERE/'AUDIT.json').write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in output.items() if k not in ('saved_sha256', 'input_sha256', 'profiles')}, indent=2))


if __name__ == '__main__':
    main()
