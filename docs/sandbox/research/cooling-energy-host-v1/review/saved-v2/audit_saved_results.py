"""Standard-library audit of terminal native02 records; no host/model calls."""

from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path('/private/tmp/brick-cooling-energy-v1/native02')
BASE = ROOT.parent
OWN = Path(__file__).resolve().parent
ENERGY_LIMIT = F(80) * F(1e-8)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def rational(value: dict) -> F:
    return F(int(value['numerator']), int(value['denominator']))


def binary(values: list[float]) -> bytes:
    return struct.pack('<' + 'd' * len(values), *values)


def main() -> None:
    original_paths = sorted(path for path in ROOT.rglob('*') if path.is_file())
    before = {str(path): sha(path) for path in original_paths}
    execution = read(ROOT / 'EXECUTION.json')
    inputs, final = read(ROOT / 'worker/INPUTS.json'), read(ROOT / 'worker/RESULT.json')
    assert execution['passed'] is True and final['passed'] is True
    assert execution['returncode'] == 0 and execution['child_reaped'] is True
    assert not execution['timed_out'] and execution['terminal_status'] == 'completed'
    assert execution['complete_worker_artifacts_present'] is True
    assert execution['real_native_integration'] is True and final['real_native_integration'] is True
    assert execution['timeout_s'] == 130.0 and 0 <= execution['elapsed_s'] < 130.0
    assert 0 <= final['elapsed_s'] <= execution['elapsed_s']
    expected_hashes = execution['input_sha256_before']
    assert len(expected_hashes) == 353 and expected_hashes == execution['input_sha256_after']
    assert expected_hashes == final['input_sha256_before'] == final['input_sha256_after']
    assert expected_hashes == inputs['input_sha256_before']
    assert all(sha(Path(path)) == expected for path, expected in expected_hashes.items())
    assert len(inputs['freeze']['files']) == 351
    assert sha(BASE / 'EXECUTION_FREEZE_V2.json') == 'a30f6540e8703de7d2bc4f1b5e1ae8ec70f1b8d146aefd0295eab454591f2202'
    for record in (inputs, final):
        assert not any(record['qualifications'][key] for key in
            ('material_qualified', 'chemical_mass_qualified', 'full_cycle_qualified', 'source_material_qualified'))
    inverse_policy = dict(energy_tolerance_j=1e-10, temperature_tolerance_k=1e-9,
                          maximum_iterations=200, square_root_bits=160)
    assert inputs['inverse_policy'] == inverse_policy
    assert inputs['target_input_uncertainty_j'] == [0.0, 0.0]
    assert inputs['initialization_roundoff_kept_separate'] is True
    refs = inputs['references']
    old = Path('/Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research/cooling-stress-v1/execution/cooling01/worker')
    fine_reference, dense_reference = read(old / 'fine.json'), read(old / 'reference.json')
    ref_times = refs['times_s']
    assert len(ref_times) == 101
    assert [value.hex() for value in ref_times] == [value.hex() for value in fine_reference['times_s']]
    assert [value.hex() for value in ref_times] == [value.hex() for value in dense_reference['times_s']]
    assert refs['fine_temperatures_k'] == [row[:2] for row in fine_reference['samples']]
    assert refs['reference_temperatures_k'] == dense_reference['temperatures_k']
    assert refs['fine_stress_pa'] == [[point['stress_pa'] for point in row['points']] for row in fine_reference['observations']]

    initial = inputs['initial_state']
    parameters = inputs['parameters']
    capacity, modulus, alpha, reference = (F(parameters[key]) for key in
        ('stress_free_heat_capacity_j_m3_k', 'biaxial_modulus_pa', 'linear_expansion_per_k', 'reference_temperature_k'))
    geometry = initial['energy_model_identity'][2]
    volume = F((float.fromhex(geometry[1]) / int(geometry[3])) * float.fromhex(geometry[2]))
    coupling = modulus * alpha**2
    tlo, thi = map(F, parameters['temperature_bounds_k'])
    slo, shi = map(F, parameters['strain_bounds'])
    true_dmin = volume * (capacity - 2 * coupling * thi)
    assert true_dmin > 0 and tlo > 0
    assert all(slo <= value <= shi for value in
        (alpha * (tlo - reference), alpha * (thi - reference), alpha * (tlo - thi), alpha * (thi - tlo)))

    def exact_energy(temperatures: list[float]) -> tuple[F, ...]:
        values = tuple(map(F, temperatures))
        assert len(values) == 2
        mean = sum(values, F()) / 2
        return tuple(volume * (capacity * (value - reference) + coupling * (mean**2 - value**2)) for value in values)

    checked_certificates = 0

    def check_certificate(certificate: dict) -> None:
        nonlocal checked_certificates
        assert certificate['policy'] == inverse_policy
        target, decoded = certificate['target'], certificate['state']
        assert target['absolute_error_j'] == [0.0, 0.0] and certificate['target_interval_admissible'] is True
        actual = exact_energy(decoded['temperatures_k'])
        residuals = tuple(value - F(wanted) for value, wanted in zip(actual, target['cell_energy_j'], strict=True))
        assert binary(certificate['cell_energy_residual_j']) == binary([float(value) for value in residuals])
        errors = tuple(abs(value - F(wanted)) for value, wanted in zip(actual, target['cell_energy_j'], strict=True))
        for error, bound, combined in zip(errors, certificate['energy_residual_abs_bound_j'], certificate['combined_energy_residual_bound_j'], strict=True):
            assert error <= F(bound) <= F(combined) <= F(1e-10)
        lower, radius = F(certificate['minimum_energy_jacobian_eigenvalue_j_k']), F(certificate['temperature_error_bound_k'])
        assert 0 < lower <= true_dmin and 0 <= radius <= F(1e-9)
        assert sum((error**2 for error in errors), F()) <= (radius * lower)**2
        # The residual ball lies inside the original positive-Ce rectangle.
        assert all(tlo <= F(value) - radius and F(value) + radius <= thi for value in decoded['temperatures_k'])
        assert 0 <= certificate['iterations'] <= 200 and not decoded['material_qualified']
        exact_mean = sum(map(F, decoded['temperatures_k']), F()) / 2
        exact_strain = alpha * (exact_mean - reference)
        assert decoded['mean_temperature_k'] == float(exact_mean)
        assert decoded['in_plane_strain'] == float(exact_strain)
        assert abs(F(decoded['plate_evaluation']['in_plane_strain']) - exact_strain) <= F(decoded['plate_strain_difference_bound'])
        assert decoded['plate_evaluation']['temperatures_k'] == decoded['temperatures_k']
        for exact, represented, bound, point, point_bound in zip(actual, decoded['cell_energy_j'],
            decoded['energy_roundoff_bound_j'], decoded['plate_evaluation']['points'], decoded['plate_energy_difference_bound_j'], strict=True):
            assert abs(exact - F(represented)) <= F(bound)
            assert abs(exact - volume * F(point['internal_energy_j_m3'])) <= F(point_bound)
        checked_certificates += 1

    forward = inputs['initialization_forward_certificate']
    assert forward['temperatures_k'] == [304.0, 304.0]
    for exact, represented, bound in zip(exact_energy(forward['temperatures_k']), forward['cell_energy_j'], forward['energy_roundoff_bound_j'], strict=True):
        assert abs(exact - F(represented)) <= F(bound)
    paths, comparison_sets = {}, {}
    total_states = total_steps = total_rhs = total_trials = 0
    for name, nominal in (('coarse', 0.005), ('fine', 0.0025)):
        raw, audit = read(ROOT / 'worker' / f'{name}.json'), read(ROOT / 'worker' / f'{name}-audit.json')
        result, summary = raw['result'], raw['rhs_summary']
        for record in (raw, audit):
            assert record['real_native_integration'] is True
            assert record['qualifications'] == inputs['qualifications']
        states, times, ledgers = result['states'], result['times_s'], result['steps']
        policy = raw['policy']
        expected_policy = dict(initial_step_s=nominal, maximum_step_s=nominal, minimum_step_s=1e-8,
            relative_tolerance=1e-9, amount_absolute_tolerance_mol=1e-12, energy_absolute_tolerance_j=1e-11,
            amount_scale_mol=1.0, energy_scale_j=80.0, maximum_steps=12000, maximum_rejections=1000, maximum_wall_seconds=60.0)
        assert all(policy[key] == value for key, value in expected_policy.items())
        assert result['status'] == 'completed' and result['reason'] is None
        assert 0 <= result['elapsed_seconds'] < 60.0
        assert times[0] == 0.0 and times[-1] == 10.0
        assert len(states) == len(times) == len(ledgers) + 1 and len(ledgers) <= 12000
        assert states[0] == initial
        assert summary['calls_started'] == summary['calls_succeeded'] == result['evaluations']
        assert summary['calls_failed'] == result['rejected_trials'] == 0
        assert audit['native_rhs_summary'] == summary
        accepted_summary = audit['accepted_state_decode_summary']
        assert accepted_summary['calls_started'] == accepted_summary['calls_succeeded'] == len(states)
        assert accepted_summary['calls_failed'] == 0
        for group in (summary, accepted_summary):
            assert group['all_decodes_certified'] and group['inventory_and_rate_contract']
            assert 0 <= group['maximum_energy_residual_bound_j'] <= 1e-10
            assert 0 <= group['maximum_temperature_error_bound_k'] <= 1e-9
        heat, work, boundary = [F(), F()], [F(), F()], F()
        local_max = global_max = constraint_max = F()
        component_cumulative = [F(), F()]
        energy0 = tuple(map(F, initial['internal_energy_j']))
        for index, (at, state) in enumerate(zip(times, states, strict=True)):
            assert state['amounts_mol'] == [[2.0], [3.0]]
            assert state['amounts_binary64_bytes_hex'] == binary([2.0, 3.0]).hex() and state['amounts_dtype'] == '<f8'
            assert state['energy_model_identity'] == initial['energy_model_identity'] and state['mechanical_stretches'] is None
            assert state['internal_energy_binary64_hex'] == [float(e).hex() for e in state['internal_energy_j']]
            if index:
                step = ledgers[index - 1]
                assert step['start_s'] == times[index - 1] < step['end_s'] == at
                assert at - step['start_s'] <= nominal + math.ulp(at) + math.ulp(step['start_s'])
                assert not any(step['start_s'] < knot < at for knot in ref_times[1:-1])
                assert all(value == 0.0 for rows in (step['face_species_mol'], step['reaction_species_mol']) for row in rows for value in row)
                assert step['stretch_increment'] is None and step['stretch_quadrature_roundoff'] is None
                assert list(step['cell_work_components_j']) == ['mechanical_constraint']
                assert binary(step['cell_work_components_j']['mechanical_constraint']) == binary(step['cell_work_j'])
                assert list(step['component_quadrature_roundoff_j']) == ['mechanical_constraint']
                assert len(step['component_quadrature_roundoff_j']['mechanical_constraint']) == 2
                for value in step['component_quadrature_roundoff_j']['mechanical_constraint']:
                    rational(value)
                for cell in range(2):
                    actual_component_residual = F(step['cell_work_j'][cell]) - F(step['cell_work_components_j']['mechanical_constraint'][cell])
                    assert actual_component_residual == rational(step['component_sum_residual_j'][cell])
                    component_cumulative[cell] += abs(actual_component_residual)
                faces = tuple(map(F, step['face_energy_j']))
                for cell in range(2):
                    heat[cell] += faces[cell] - faces[cell + 1]
                    work[cell] += F(step['cell_work_j'][cell])
                boundary += faces[0] - faces[-1]
            delta = tuple(F(e) - old for e, old in zip(state['internal_energy_j'], energy0, strict=True))
            local = tuple(de - q - p for de, q, p in zip(delta, heat, work, strict=True))
            global_error, constraint = sum(delta, F()) - boundary, sum(work, F())
            recorded = audit['ledger']['all_prefixes'][index]
            assert recorded['time_s'] == at
            assert tuple(map(rational, recorded['local_energy_residual_j'])) == local
            assert rational(recorded['global_heat_residual_j']) == global_error
            assert rational(recorded['cumulative_boundary_heat_j']) == boundary
            assert tuple(map(rational, recorded['cumulative_cell_heat_j'])) == tuple(heat)
            assert tuple(map(rational, recorded['cumulative_cell_work_j'])) == tuple(work)
            assert rational(recorded['total_constraint_work_residual_j']) == constraint
            local_max = max(local_max, *map(abs, local))
            global_max, constraint_max = max(global_max, abs(global_error)), max(constraint_max, abs(constraint))
        assert component_cumulative == list(map(rational, result['cumulative_absolute_component_residual_j']))
        assert local_max <= ENERGY_LIMIT and global_max <= ENERGY_LIMIT
        for key, value in (('maximum_local_energy_residual_j', local_max), ('maximum_global_heat_residual_j', global_max),
                           ('maximum_total_constraint_work_residual_j', constraint_max)):
            assert rational(audit['ledger'][key]) == value
        rows = audit['comparison_points']
        assert len(rows) == 101 and [row['time_s'].hex() for row in rows] == [value.hex() for value in ref_times]
        assert [row['reference_index'] for row in rows] == list(range(101))
        for row in rows:
            index = row['accepted_index']
            assert times[index].hex() == row['time_s'].hex()
            certificate = row['inverse']
            assert binary(certificate['target']['cell_energy_j']) == binary(states[index]['internal_energy_j'])
            assert row['temperatures_k'] == certificate['state']['temperatures_k']
            check_certificate(certificate)
            for key, reference_key in (('fine_temperature_difference_k', 'fine_temperatures_k'),
                                       ('reference_temperature_difference_k', 'reference_temperatures_k')):
                expected = [t - r for t, r in zip(row['temperatures_k'], refs[reference_key][row['reference_index']], strict=True)]
                assert row[key] == expected
        maxima = {key: max(abs(value) for row in rows for value in row[key]) for key in
                  ('fine_temperature_difference_k', 'reference_temperature_difference_k')}
        assert all(value <= 4e-6 for value in maxima.values())
        assert all(audit['maximum_absolute_differences'][key] == value for key, value in maxima.items())
        for group in (summary, accepted_summary):
            for key in ('worst_energy_certificate', 'worst_temperature_certificate'):
                witness = group[key]
                assert binary(witness['inverse']['target']['cell_energy_j']) == binary(witness['state_energy_j'])
                if group is accepted_summary:
                    assert binary(states[times.index(witness['time_s'])]['internal_energy_j']) == binary(witness['state_energy_j'])
                check_certificate(witness['inverse'])
        trial_count = 0
        with (ROOT / 'worker' / f'{name}-rhs-trials.jsonl').open() as stream:
            for line in stream:
                witness = json.loads(line)
                trial_count += 1
                assert witness['kind'] == 'RHS_trial_not_accepted_state'
                assert witness['accepted_prefix_status'] == 'unknown_until_integrate_returns'
                assert witness['real_native_integration'] is True
                assert witness['summary']['calls_started'] == 512 * trial_count
        assert trial_count == result['evaluations'] // 512
        assert all(audit['gates'].values()) and audit['gates'] == final['gates'][name]
        paths[name] = dict(accepted_states=len(states), accepted_steps=len(ledgers), rhs_calls=result['evaluations'],
            rejected_trials=result['rejected_trials'], native_elapsed_s=result['elapsed_seconds'],
            comparison_points=len(rows), maximum_local_energy_residual_j=float(local_max),
            maximum_global_heat_residual_j=float(global_max), maximum_total_constraint_work_residual_j=float(constraint_max),
            maximum_temperature_difference_to_old_fine_k=maxima['fine_temperature_difference_k'],
            maximum_temperature_difference_to_independent_reference_k=maxima['reference_temperature_difference_k'],
            recorded_maximum_native_power_reconstruction_difference_w=summary['maximum_native_power_reconstruction_difference_w'],
            trial_witness_records=trial_count, all_registered_path_gates_independently_consistent=True)
        comparison_sets[name] = rows
        total_states += len(states)
        total_steps += len(ledgers)
        total_rhs += result['evaluations']
        total_trials += trial_count
    time_difference = max(abs(t - u) for left, right in zip(comparison_sets['coarse'], comparison_sets['fine'], strict=True)
                          for t, u in zip(left['temperatures_k'], right['temperatures_k'], strict=True))
    assert time_difference == final['maximum_coarse_fine_temperature_difference_k'] <= 4e-7
    assert final['time_convergence_gate'] is True and final['run_status'] == {'coarse': 'completed', 'fine': 'completed'}
    assert checked_certificates == 210
    prior = read(BASE / 'review/saved/SAVED_PREFIX_AUDIT.json')
    assert all(sha(Path(path)) == expected for path, expected in prior['saved_artifact_sha256_before'].items())
    assert read(BASE / 'native01/worker/RESULT.json')['passed'] is False
    after = {str(path): sha(path) for path in original_paths}
    assert before == after
    report = dict(scope='terminal_saved_results_standard_library_only', audit_passed=True,
        extra_time_integrations=0, extra_host_calls=0, independently_decoded_all_saved_energies=False,
        registered_files=351, observed_input_identities_verified=353,
        supervisor_elapsed_s=execution['elapsed_s'], supervisor_cap_s=130.0, native_cap_s_each=60.0,
        paths=paths, total_accepted_states=total_states, total_accepted_steps=total_steps, total_rhs_calls=total_rhs,
        retained_complete_inverse_records_recalculated=checked_certificates, initialization_forward_roundoff_checked=True,
        maximum_coarse_fine_temperature_difference_k=time_difference, coarse_fine_temperature_limit_k=4e-7,
        absolute_conservation_limit_j=float(ENERGY_LIMIT), trial_witness_records_checked=total_trials,
        actual_per_rhs_power_field_replay=False, native_power_note='online summary maxima; full per-RHS rate fields not archived',
        extra_panel_branch_count='not logged; no exact repair-branch count inferred',
        original_native01_preserved_failed=True, saved_artifact_sha256_before=before, saved_artifact_sha256_after=after,
        material_qualified=False, chemical_mass_qualified=False, full_cycle_qualified=False)
    with (OWN / 'SAVED_RESULTS_AUDIT.json').open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in report.items() if 'sha256' not in key}, indent=2))


if __name__ == '__main__':
    main()
