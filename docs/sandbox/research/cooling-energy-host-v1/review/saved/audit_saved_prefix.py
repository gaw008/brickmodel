"""Audit only saved native01 JSON with standard-library arithmetic; no model calls."""

from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path('/private/tmp/brick-cooling-energy-v1/native01')
OWN = Path(__file__).resolve().parent
PATHS = tuple(ROOT / name for name in ('EXECUTION.json', 'START.json', 'worker/RESULT.json',
    'worker/INPUTS.json', 'worker/coarse.json', 'worker/coarse-audit.json', 'worker/coarse-rhs-trials.jsonl'))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fraction(value: dict) -> F:
    return F(int(value['numerator']), int(value['denominator']))


def read(name: str) -> dict:
    return json.loads((ROOT / name).read_text())


def main() -> None:
    before = {str(path): digest(path) for path in PATHS}
    execution, final = read('EXECUTION.json'), read('worker/RESULT.json')
    inputs, raw, audit = read('worker/INPUTS.json'), read('worker/coarse.json'), read('worker/coarse-audit.json')
    result = raw['result']
    states, times, steps = result['states'], result['times_s'], result['steps']
    assert result['status'] == 'numerical_failure' and result['reason'] == 'unresolvable_stage_time'
    assert final['run_status'] == {'coarse': 'numerical_failure', 'fine': 'not_started'}
    assert not execution['passed'] and not final['passed'] and not execution['timed_out']
    assert execution['child_reaped'] and execution['returncode'] == 1
    assert execution['input_sha256_before'] == execution['input_sha256_after']
    assert len(execution['input_sha256_before']) == 339
    assert (len(states), len(times), len(steps)) == (61, 61, 60)
    assert times[0] == 0.0 and times[-1] == 0.3
    assert result['evaluations'] == raw['rhs_summary']['calls_started'] == 421
    assert raw['rhs_summary']['calls_failed'] == result['rejected_trials'] == 0
    assert not (ROOT / 'worker/fine.json').exists()

    initial = states[0]
    energy0 = tuple(map(F, initial['internal_energy_j']))
    fixed_bytes = struct.pack('<dd', 2.0, 3.0).hex()
    heat, work, boundary = [F(), F()], [F(), F()], F()
    local_max = global_max = constraint_max = F()
    worst_local = worst_global = 0
    for index, (at, state) in enumerate(zip(times, states, strict=True)):
        assert state['amounts_mol'] == [[2.0], [3.0]]
        assert state['amounts_binary64_bytes_hex'] == fixed_bytes and state['amounts_dtype'] == '<f8'
        assert state['mechanical_stretches'] is None
        assert state['energy_model_identity'] == initial['energy_model_identity']
        assert state['internal_energy_binary64_hex'] == [float(e).hex() for e in state['internal_energy_j']]
        if index:
            step = steps[index - 1]
            assert step['start_s'] == times[index - 1] < step['end_s'] == at
            assert all(value == 0.0 for rows in (step['face_species_mol'], step['reaction_species_mol']) for row in rows for value in row)
            assert step['stretch_increment'] is None and step['stretch_quadrature_roundoff'] is None
            assert list(step['cell_work_components_j']) == ['mechanical_constraint']
            assert step['cell_work_components_j']['mechanical_constraint'] == step['cell_work_j']
            assert list(step['component_quadrature_roundoff_j']) == ['mechanical_constraint']
            assert all(fraction(value) == 0 for value in step['component_sum_residual_j'])
            faces = tuple(map(F, step['face_energy_j']))
            for cell in range(2):
                heat[cell] += faces[cell] - faces[cell + 1]
                work[cell] += F(step['cell_work_j'][cell])
            boundary += faces[0] - faces[-1]
        delta = tuple(F(e) - old for e, old in zip(state['internal_energy_j'], energy0, strict=True))
        local = tuple(de - q - p for de, q, p in zip(delta, heat, work, strict=True))
        global_error, constraint = sum(delta, F()) - boundary, sum(work, F())
        reported = audit['ledger']['all_prefixes'][index]
        assert reported['time_s'] == at
        assert tuple(map(fraction, reported['local_energy_residual_j'])) == local
        assert fraction(reported['global_heat_residual_j']) == global_error
        assert fraction(reported['cumulative_boundary_heat_j']) == boundary
        assert tuple(map(fraction, reported['cumulative_cell_heat_j'])) == tuple(heat)
        assert tuple(map(fraction, reported['cumulative_cell_work_j'])) == tuple(work)
        assert fraction(reported['total_constraint_work_residual_j']) == constraint
        if max(map(abs, local)) > local_max:
            local_max, worst_local = max(map(abs, local)), index
        if abs(global_error) > global_max:
            global_max, worst_global = abs(global_error), index
        constraint_max = max(constraint_max, abs(constraint))
    for key, value in (('maximum_local_energy_residual_j', local_max),
                       ('maximum_global_heat_residual_j', global_max),
                       ('maximum_total_constraint_work_residual_j', constraint_max)):
        assert fraction(audit['ledger'][key]) == value
    threshold = F(80) * F(1e-8)
    assert local_max <= threshold and global_max <= threshold

    reference_times = inputs['references']['times_s']
    matches = [(i, reference_times.index(at)) for i, at in enumerate(times) if at in reference_times]
    assert matches == [(0, 0), (20, 1), (40, 2)]
    assert [(row['accepted_index'], row['reference_index']) for row in audit['comparison_points']] == matches
    assert float(reference_times[3]).hex() != float(times[-1]).hex()

    parameters = inputs['parameters']
    capacity, modulus, alpha, reference = (F(parameters[name]) for name in
        ('stress_free_heat_capacity_j_m3_k', 'biaxial_modulus_pa', 'linear_expansion_per_k', 'reference_temperature_k'))
    geometry = initial['energy_model_identity'][2]
    volume = F((float.fromhex(geometry[1]) / int(geometry[3])) * float.fromhex(geometry[2]))
    coupling = modulus * alpha**2
    true_dmin = volume * (capacity - 2 * coupling * F(parameters['temperature_bounds_k'][1]))

    def exact_energy(temperatures: list[float]) -> tuple[F, ...]:
        values = tuple(map(F, temperatures))
        mean = sum(values, F()) / 2
        return tuple(volume * (capacity * (t - reference) + coupling * (mean**2 - t**2)) for t in values)

    forward = inputs['initialization_forward_certificate']
    for exact, represented, bound in zip(exact_energy(forward['temperatures_k']), forward['cell_energy_j'], forward['energy_roundoff_bound_j'], strict=True):
        assert abs(exact - F(represented)) <= F(bound)
    certificates = [row['inverse'] for row in audit['comparison_points']]
    for group in (raw['rhs_summary'], audit['accepted_state_decode_summary']):
        for witness in ('worst_energy_certificate', 'worst_temperature_certificate'):
            certificate = group[witness]['inverse']
            assert certificate['target']['cell_energy_j'] == group[witness]['state_energy_j']
            certificates.append(certificate)
    for certificate in certificates:
        assert certificate['policy'] == inputs['inverse_policy']
        target = certificate['target']
        assert target['absolute_error_j'] == [0.0, 0.0] and certificate['target_interval_admissible']
        actual = exact_energy(certificate['state']['temperatures_k'])
        errors = tuple(abs(value - F(wanted)) for value, wanted in zip(actual, target['cell_energy_j'], strict=True))
        for error, bound, combined in zip(errors, certificate['energy_residual_abs_bound_j'], certificate['combined_energy_residual_bound_j'], strict=True):
            assert error <= F(bound) <= F(combined) <= F(1e-10)
        lower, radius = F(certificate['minimum_energy_jacobian_eigenvalue_j_k']), F(certificate['temperature_error_bound_k'])
        assert 0 < lower <= true_dmin and radius <= F(1e-9)
        assert sum((error**2 for error in errors), F()) <= (radius * lower)**2
        assert certificate['state']['material_qualified'] is False
    nominal_uniform_root = reference + F(40) / (volume * capacity)
    initial_certificate = certificates[0]
    initial_error_squared = sum((F(t) - nominal_uniform_root)**2 for t in initial_certificate['state']['temperatures_k'])
    assert initial_error_squared <= F(initial_certificate['temperature_error_bound_k'])**2
    for row in audit['comparison_points']:
        assert row['inverse']['target']['cell_energy_j'] == states[row['accepted_index']]['internal_energy_j']
        assert row['temperatures_k'] == row['inverse']['state']['temperatures_k']
        for key, reference_key in (('fine_temperature_difference_k', 'fine_temperatures_k'),
                                   ('reference_temperature_difference_k', 'reference_temperatures_k')):
            assert row[key] == [actual - expected for actual, expected in zip(row['temperatures_k'], inputs['references'][reference_key][row['reference_index']], strict=True)]
    for key in ('fine_temperature_difference_k', 'reference_temperature_difference_k'):
        assert audit['maximum_absolute_differences'][key] == max(abs(value) for row in audit['comparison_points'] for value in row[key])
    assert not audit['gates']['complete'] and not final['time_convergence_gate']
    assert not audit['gates']['temperature_to_old_fine'] and not audit['gates']['temperature_to_independent_reference']
    after = {str(path): digest(path) for path in PATHS}
    assert before == after
    report = dict(scope='saved_prefix_only_no_host_calls_no_integration', original_run_passed=False,
        independent_saved_prefix_audit_passed=True, original_status=result['status'], original_reason=result['reason'],
        accepted_states=len(states), accepted_steps=len(steps), rhs_calls=result['evaluations'], rejected_trials=result['rejected_trials'],
        final_accepted_time_s=times[-1], final_accepted_time_hex=times[-1].hex(), next_reference_time_s=reference_times[3],
        next_reference_time_hex=reference_times[3].hex(), matching_reference_points=len(matches),
        matched_accepted_reference_indices=matches, maximum_local_energy_residual_j=float(local_max),
        maximum_global_heat_residual_j=float(global_max), maximum_constraint_work_residual_j=float(constraint_max),
        worst_local_accepted_index=worst_local, worst_global_accepted_index=worst_global, absolute_conservation_threshold_j=float(threshold),
        complete_saved_inverse_records_checked=len(certificates), initial_returned_temperatures_k=initial_certificate['state']['temperatures_k'],
        initial_temperature_error_bound_k=initial_certificate['temperature_error_bound_k'],
        recorded_rhs_maximum_native_power_reconstruction_difference_w=raw['rhs_summary']['maximum_native_power_reconstruction_difference_w'],
        native_power_scope='recorded_online_maximum; all_per_RHS_fields_were_not_archived_for_independent_replay',
        saved_artifact_sha256_before=before, saved_artifact_sha256_after=after,
        full_trajectory_gates_passed=False, fine_path_started=False)
    output = OWN / 'SAVED_PREFIX_AUDIT.json'
    with output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in report.items() if 'sha256' not in key}, indent=2))


if __name__ == '__main__':
    main()
