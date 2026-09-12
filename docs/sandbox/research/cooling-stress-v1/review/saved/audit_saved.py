"""Read saved validation evidence only; no model, integrator, RHS or root solve.

Exact manufactured decimal constants and the binary64 values encoded by JSON
are evaluated with 80-digit Decimal arithmetic. Small differences from the
driver's float arithmetic are reported, not used to invent acceptance gates.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
import traceback
from decimal import Decimal as D, getcontext

getcontext().prec = 80
BASE = Path('/private/tmp/brick-cooling-thermoelastic-v1')
REPO = Path('/Users/wanggaoying/Desktop/brickmodel-github')
OUT = Path(__file__).resolve().parent
STUDY = REPO / 'docs/sandbox/research/cooling-stress-v1'
C, B, A, M, V, TR = map(D, ('100000', '10', '.0001', '1e9', '.0001', '300'))
Z = D(0)
EXPECTED_HASHES = {
    'PREREGISTRATION.md': '12bd994b77f7dc264b3994181696f31140031ccbca8c786ab902ecf632237b35',
    'run_validation.py': '7a4d3ed9ea733934645420b29673b6d3c4869f07575cd1b58e743931be6f714a',
    'supervise.py': 'ab07f1eb856b768b82b0db1524f9f8e8e3be3b92f4b24324e10fbf69c472b0cd',
}
COLUMNS = ['T0_K', 'T1_K', 'heat0_J', 'heat1_J', 'work0_J', 'work1_J',
           'external_heat_J', 'reservoir_entropy_J_per_K', 'production_J_per_K']
INPUT_HASHES = {}


def dec(value):
    return D.from_float(value) if isinstance(value, float) else D(value)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, label):
    if not condition:
        raise ValueError(label)


def finite(value):
    if isinstance(value, dict):
        for entry in value.values():
            finite(entry)
    elif isinstance(value, list):
        for entry in value:
            finite(entry)
    elif isinstance(value, float):
        require(math.isfinite(value), 'nonfinite saved JSON value')


def read(path):
    INPUT_HASHES[str(path)] = digest(path)
    result = json.loads(path.read_text())
    finite(result)
    return result


def emit(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False,
                  default=lambda v: str(v) if isinstance(v, D) else str(v))
        stream.write('\n')


def peak(stats, key, value):
    stats[key] = max(stats.get(key, Z), abs(value))


def difference(stats, key, reported, reconstructed):
    peak(stats, key, dec(reported) - reconstructed)


def fields(temperature):
    """Differentiate the declared potential; do not use candidate helper code."""
    t = list(map(dec, temperature))
    require(len(t) == 2 and all(D(290) <= x <= D(310) for x in t), 'T domain')
    mean = sum(t) / 2
    strain = A * (mean - TR)
    mismatch = [A * (mean - x) for x in t]
    eigen = [A * (x - TR) for x in t]
    require(max(map(abs, [strain, *mismatch, *eigen])) <= D('.01'), 'strain domain')
    ce = [C - 2 * B * x for x in t]
    require(min(ce) > 0, 'Ce positive')
    stress = [M * x for x in mismatch]
    logs = [(x / TR).ln() for x in t]
    # Factored squares reduce cancellation independently of the driver's form.
    u = [C * (x - TR) + B * (mean - x) * (mean + x) for x in t]
    s = [C * log + 2 * B * (mean - x) for x, log in zip(t, logs, strict=True)]
    psi = [C * ((x - TR) - x * log) + B * (mean - x) ** 2
           for x, log in zip(t, logs, strict=True)]
    return dict(t=t, mean=mean, strain=strain, mismatch=mismatch, ce=ce,
                stress=stress, u=u, s=s, psi=psi)


def inspect_evaluation(evaluation, external, stats):
    finite(evaluation)
    f = fields(evaluation['temperatures_k'])
    t, mean = f['t'], f['mean']
    td = list(map(dec, evaluation['temperature_rates_k_s']))
    require(len(td) == 2 and len(evaluation['points']) == 2, 'evaluation dimensions')
    require(evaluation['reference_cell_volumes_m3'] == [.0001, .0001], 'cell volumes')
    require(evaluation['ledger_scope'] == 'reference_half_slab'
            and evaluation['full_slab_mirror_factor'] == 2
            and evaluation['material_qualified'] is False, 'evaluation scope')
    mdot = sum(td) / 2
    flux = t[0] - t[1]
    qb = 2 * (TR - t[1]) if external else Z
    q = [-flux, flux + qb]
    power = [2 * V * stress * A * mdot for stress in f['stress']]
    udot = [ce * rate + 2 * B * mean * mdot
            for ce, rate in zip(f['ce'], td, strict=True)]
    sdot = [(C / x - 2 * B) * rate + 2 * B * mdot
            for x, rate in zip(t, td, strict=True)]
    prod = [Z, flux ** 2 / (t[0] * t[1]),
            2 * (TR - t[1]) ** 2 / (TR * t[1]) if external else Z]
    for i, point in enumerate(evaluation['points']):
        require(point['temperature_k'] == evaluation['temperatures_k'][i], 'point T identity')
        for key, value in [('in_plane_strain', f['strain']),
                           ('elastic_strain', f['mismatch'][i]),
                           ('stress_pa', f['stress'][i]),
                           ('internal_energy_j_m3', f['u'][i]),
                           ('entropy_j_m3_k', f['s'][i]),
                           ('helmholtz_j_m3', f['psi'][i]),
                           ('fixed_strain_heat_capacity_j_m3_k', f['ce'][i])]:
            difference(stats, 'reported_point_' + key, point[key], value)
        peak(stats, 'constitutive_u_minus_psi_minus_Ts_j_m3',
             f['u'][i] - f['psi'][i] - t[i] * f['s'][i])
        peak(stats, 'matrix_equation_residual_w',
             V * (f['ce'][i] * td[i] + 2 * B * t[i] * mdot) - q[i])
        peak(stats, 'local_first_law_rate_residual_w', V * udot[i] - q[i] - power[i])
        peak(stats, 'local_entropy_heat_rate_residual_w', V * t[i] * sdot[i] - q[i])
    for key, values in [('face_heat_outward_w', [Z, flux, -qb]), ('cell_heat_in_w', q),
                        ('cell_mechanical_power_w', power), ('cell_u_rates_j_m3_s', udot),
                        ('cell_s_rates_j_m3_k_s', sdot), ('face_entropy_production_w_k', prod)]:
        require(len(evaluation[key]) == len(values), 'field shape: ' + key)
        for reported, value in zip(evaluation[key], values, strict=True):
            difference(stats, 'reported_' + key, reported, value)
    totals = {
        'in_plane_strain': f['strain'], 'in_plane_strain_rate_per_s': A * mdot,
        'external_heat_in_w': qb, 'reservoir_entropy_rate_w_k': -qb / TR,
        'total_internal_energy_j': V * sum(f['u']),
        'total_helmholtz_energy_j': V * sum(f['psi']), 'total_entropy_j_k': V * sum(f['s']),
        'total_internal_energy_rate_w': V * sum(udot), 'total_entropy_rate_w_k': V * sum(sdot),
        'total_mechanical_power_w': sum(power), 'total_entropy_production_w_k': sum(prod),
    }
    for key, value in totals.items():
        difference(stats, 'reported_' + key, evaluation[key], value)
    peak(stats, 'membrane_resultant_pa_m', D('.01') * sum(map(dec, (p['stress_pa'] for p in evaluation['points']))))
    peak(stats, 'reported_total_mechanical_power_w_absolute', dec(evaluation['total_mechanical_power_w']))
    peak(stats, 'entropy_rate_identity_w_k', V * sum(sdot) - qb / TR - sum(prod))
    require(all(dec(x) >= 0 for x in evaluation['face_entropy_production_w_k']), 'negative saved production')
    # The following signs are specific to these two paths, not a general solver gate.
    require(qb <= 0, 'external cooling heat sign')
    for key, value, op in [('minimum_temperature_k', min(t), min), ('maximum_temperature_k', max(t), max),
                         ('minimum_fixed_strain_heat_capacity_j_m3_k', min(f['ce']), min),
                         ('minimum_external_heat_in_w', qb, min), ('maximum_external_heat_in_w', qb, max)]:
        stats[key] = value if key not in stats else op(stats[key], value)
    return f


def ledger(row, initial, stats):
    require(len(row) == 9, 'state dimension')
    values = list(map(dec, row))
    f = fields(row[:2])
    local = [V * (f['u'][i] - initial['u'][i]) - values[2 + i] - values[4 + i] for i in range(2)]
    global_error = V * sum(f['u'][i] - initial['u'][i] for i in range(2)) - values[6]
    entropy = V * sum(f['s'][i] - initial['s'][i] for i in range(2)) + values[7] - values[8]
    for value in local:
        peak(stats, 'local_energy_error_j', value)
    peak(stats, 'global_energy_error_j', global_error)
    peak(stats, 'entropy_identity_error_j_k_descriptive', entropy)
    peak(stats, 'cell_heat_sum_minus_external_heat_j', sum(values[2:4]) - values[6])
    peak(stats, 'cell_work_sum_j', sum(values[4:6]))
    peak(stats, 'reservoir_entropy_plus_external_heat_over_300_j_k', values[7] + values[6] / TR)
    peak(stats, 'U_fluctuation_identity_j', V * sum(f['u']) -
         (V * C * sum(t - TR for t in f['t']) - B * V * sum((t - f['mean']) ** 2 for t in f['t'])))
    require(values[8] >= 0 and values[7] >= 0 and values[6] <= 0, 'cumulative sign')
    return dict(U_j=V * sum(f['u']), S_j_k=V * sum(f['s']),
                cell_u_j=[V * x for x in f['u']], cell_s_j_k=[V * x for x in f['s']],
                local_energy_residual_j=local, global_energy_residual_j=global_error,
                entropy_identity_residual_j_k=entropy,
                cell_heat_integrals_j=values[2:4], cell_work_integrals_j=values[4:6],
                external_heat_integral_j=values[6], reservoir_entropy_integral_j_k=values[7],
                production_integral_j_k=values[8])


def analytic_saved(reference, times):
    require(reference['method'] == 'independent_60_digit_bisection', 'analytic method')
    require(len(reference['roots']) == 101, 'root count')
    stats, output = {}, []
    k0 = C - 2 * B * D(302) + 2 * B * B * D(4) / C
    for saved, time in zip(reference['roots'], times, strict=True):
        require(saved['time_s'] == time, 'root time grid')
        # The frozen oracle converts time with str(float), deliberately retained here.
        t = D(str(time))
        lo, hi = D(saved['delta_lower']), D(saved['delta_upper'])
        require(0 < lo <= hi <= 2 and hi - lo <= D('1e-12'), 'saved root bracket')
        def residual(delta):
            return k0 * (delta / 2).ln() - B * B / C * (delta * delta - 4) + D(20000) * t
        rlo, rhi = residual(lo), residual(hi)
        require((t == 0 and lo == hi == 2 and rlo == rhi == 0)
                or (t > 0 and rlo < 0 < rhi), 'original equation bracket signs')
        # Positive derivative over this whole bracket proves root uniqueness.
        require(k0 / hi - 2 * B * B / C * hi > 0, 'root monotonicity')
        delta = (lo + hi) / 2
        mean = D(302) + B / C * (delta * delta - 4)
        rebuilt = [mean + delta, mean - delta]
        bound = (hi - lo) * (1 + 2 * B * D(2) / C) / 2 + D('1e-12')
        require(bound <= D('2e-7') and D(saved['temperature_error_bound_k']) == bound, 'saved root error bound')
        for actual, target in zip(saved['temperatures_k'], rebuilt, strict=True):
            require(actual == float(target), 'root midpoint to binary64 conversion')
            peak(stats, 'temperature_binary64_conversion_error_k', dec(actual) - target)
        peak(stats, 'bracket_width_delta_k', hi - lo)
        peak(stats, 'midpoint_original_equation_residual', residual(delta))
        peak(stats, 'stored_endpoint_residual_discrepancy', rlo - D(saved['residual_lower']))
        peak(stats, 'stored_endpoint_residual_discrepancy', rhi - D(saved['residual_upper']))
        peak(stats, 'temperature_error_bound_k', bound)
        output.append(dict(time_s=time, residual_lower=rlo, residual_upper=rhi,
                           midpoint_residual=residual(delta), temperature_error_bound_k=bound))
    return stats, output


def reference_bounds(row):
    bounds = row['rhs_domain_bounds']
    require(row['nfev'] == bounds['rhs_calls'] and row['nfev'] > 0, 'reference nfev')
    require(290 <= bounds['min_temperature_k'] <= bounds['max_temperature_k'] <= 310, 'reference recorded domain')
    require(bounds['min_fixed_strain_heat_capacity_j_m3_k'] > 0, 'reference recorded Ce')
    expected_ce = C - 2 * B * dec(bounds['max_temperature_k'])
    require(all(bounds['min_temperature_k'] <= x <= bounds['max_temperature_k']
                for ts in row['temperatures_k'] for x in ts), 'saved reference bounds enclose observations')
    for ts in row['temperatures_k']:
        fields(ts)
    return dict(recorded_bounds=bounds,
                min_Ce_arithmetic_discrepancy=dec(bounds['min_fixed_strain_heat_capacity_j_m3_k']) - expected_ce,
                limitation='Only aggregate RHS bounds saved for this reference; no claim of independent per-stage reference audit.')


def source_identity():
    freeze, installed = read(BASE / 'SOURCE_FREEZE.json'), read(BASE / 'INSTALLED_MATCH.json')
    require(installed['noneditable'] is True and installed['direct_url']['dir_info'] == {}, 'noneditable record')
    count = 0
    for name, record in freeze['files'].items():
        for root in [Path(freeze['root']), Path(installed['installed_root'])]:
            path = root / name
            require(path.stat().st_size == record['bytes'] and digest(path) == record['sha256'], 'source/installed mismatch: ' + name)
        count += 1
    require(count == installed['package_files'] == 163, 'source file count')
    require(freeze['files']['cooling_thermoelastic_plate.py']['sha256'] ==
            '33851857946f16b560529ad8a9d3ab1bc4fec6c1a18ae63bb9897d77a03746d7', 'candidate source identity')
    for name, expected in EXPECTED_HASHES.items():
        require(digest(STUDY / name) == expected, 'frozen driver/prereg/supervisor SHA: ' + name)
    return dict(files_hashed_against_both_source_and_installed=count,
                candidate=freeze['files']['cooling_thermoelastic_plate.py'], driver_hashes=EXPECTED_HASHES)


def audit_case(case, reconstruction):
    directory = BASE / (case + '01')
    work = directory / 'worker'
    start, execution = read(directory / 'START.json'), read(directory / 'EXECUTION.json')
    inputs, result = read(work / 'INPUTS.json'), read(work / 'RESULT.json')
    expected_before = {str(STUDY / name): sha for name, sha in EXPECTED_HASHES.items()}
    expected_command = [str(BASE / 'installed-venv/bin/python'), '-I', str(STUDY / 'run_validation.py'),
                        '--case', case, '--output', str(work), '--preregistration', str(STUDY / 'PREREGISTRATION.md')]
    for row in [start, execution]:
        require(row['command'] == expected_command and row['cwd'] == '/private/tmp'
                and row['timeout_s'] == 10 and row['input_sha256_before'] == expected_before, 'supervisor start identity')
    require(execution['input_sha256_after'] == expected_before and execution['inputs_unchanged'] is True, 'supervisor after identity')
    require(execution['returncode'] == 0 and execution['child_reaped'] is True
            and execution['timed_out'] is False and 0 < execution['elapsed_s'] < 10, 'supervisor terminal')
    require(result['status'] == 'completed' and result['elapsed_s'] < execution['elapsed_s'], 'inner terminal')
    require(all(result[key] is False for key in ['material_qualified', 'spatial_convergence_demonstrated', 'full_firing_cycle']), 'result qualification')
    external = case == 'cooling'
    initial_t = [304., 304.] if external else [304., 300.]
    require(inputs['initial_temperatures_k'] == initial_t and inputs['case'] == case
            and inputs['material_qualified'] is False and inputs['preregistration_sha256'] == EXPECTED_HASHES['PREREGISTRATION.md'], 'worker input identity')
    expected_parameters = dict(biaxial_modulus_pa=1e9, linear_expansion_per_k=1e-4,
        stress_free_heat_capacity_j_m3_k=1e5, reference_temperature_k=300., conductivity_w_m_k=1.,
        temperature_bounds_k=[290.,310.], strain_bounds=[-.01,.01], outer_temperature_k=300.,
        coefficient_classification='manufactured', mechanical_regime='symmetric_free_plane_stress',
        outer_boundary='fixed_temperature' if external else 'adiabatic')
    require(inputs['parameters'] == expected_parameters and inputs['reference'] ==
            dict(half_thickness_m=.02, reference_area_m2=.01, cells=2), 'manufactured inputs')
    initial = fields(initial_t)
    reference, negative = read(work / 'reference.json'), read(work / 'negative_control.json')
    reports = {name: read(work / (name + '.json')) for name in ['coarse', 'fine']}
    times = reports['coarse']['times_s']
    require(len(times) == 101 and times[0] == 0 and times[-1] == 10
            and all(abs(dec(t) - D(i) / 10) <= D('2e-15') for i, t in enumerate(times)), '101-point grid')
    if external:
        require(reference['method'] == 'independent_dense_rhs' and reference['times_s'] == times, 'dense reference grid')
        ref_t, ref_audit = reference['temperatures_k'], reference_bounds(reference)
    else:
        ref_t = [row['temperatures_k'] for row in reference['roots']]
        ref_audit, roots = analytic_saved(reference, times)
        emit(OUT / 'ANALYTIC_ROOTS01.json', roots)
    require(len(ref_t) == 101 and ref_t[0] == initial_t, 'reference shape/initial')
    audited, gates = {}, {}
    for name, report in reports.items():
        expected_policy = dict(rtol=1e-9, atol=1e-11, max_step=.05) if name == 'coarse' else dict(rtol=1e-11, atol=1e-13, max_step=.025)
        require(report['status'] == 'completed' and report['policy'] == expected_policy
                and report['state_columns'] == COLUMNS and report['times_s'] == times, 'candidate policy/grid')
        require(len(report['samples']) == len(report['observations']) == 101, 'candidate sample shape')
        accepted_times, accepted_states = report['accepted_times_s'], report['accepted_states']
        require(len(accepted_times) == len(accepted_states) and accepted_times[0] == 0 and accepted_times[-1] == 10, 'accepted extent')
        require(all(0 < b - a <= expected_policy['max_step'] + 2e-15
                    for a, b in zip(accepted_times, accepted_times[1:])), 'accepted monotonic/max-step')
        require(accepted_states[0] == report['samples'][0] == initial_t + [0.] * 7
                and accepted_states[-1] == report['samples'][-1], 'state endpoints')
        sample_stats, accepted_stats, evaluation_stats = {}, {}, {}
        for kind, ts, rows, stats in [('sample', times, report['samples'], sample_stats),
                                      ('accepted_prefix', accepted_times, accepted_states, accepted_stats)]:
            previous = None
            for time, row in zip(ts, rows, strict=True):
                entry = ledger(row, initial, stats)
                if previous is not None:
                    require(row[8] >= previous[8] and row[7] >= previous[7], 'cumulative entropy monotonicity')
                previous = row
                reconstruction.write(json.dumps(dict(case=case, resolution=name, kind=kind, time_s=time,
                    temperatures_k=row[:2], **entry), default=str, allow_nan=False) + '\n')
        terr, stress_error = Z, Z
        pointwise_difference = {}
        saved_metrics = result['metrics'][name]
        require(len(saved_metrics['pointwise']) == 101, 'pointwise count')
        for row, observation, reference_t, saved_point in zip(report['samples'], report['observations'], ref_t, saved_metrics['pointwise'], strict=True):
            require(observation['temperatures_k'] == row[:2] == saved_point['temperatures_k'], 'observation state identity')
            f = inspect_evaluation(observation, external, evaluation_stats)
            ref_fields = fields(reference_t)
            current = ledger(row, initial, {})
            for i in range(2):
                terr = max(terr, abs(dec(row[i]) - dec(reference_t[i])))
                stress_error = max(stress_error, abs(dec(observation['points'][i]['stress_pa']) - ref_fields['stress'][i]))
                require(saved_point['reported_stress_pa'][i] == observation['points'][i]['stress_pa'], 'pointwise reported stress identity')
                difference(pointwise_difference, 'reconstructed_stress_pa', saved_point['reconstructed_stress_pa'][i], f['stress'][i])
                difference(pointwise_difference, 'local_energy_residual_j', saved_point['local_energy_residual_j'][i], current['local_energy_residual_j'][i])
        sample_stats['temperature_error_k'] = terr
        sample_stats['reported_stress_error_vs_decimal_reference_pa'] = stress_error
        stage_path = work / (name + '-stages.jsonl')
        INPUT_HASHES[str(stage_path)] = digest(stage_path)
        stage_stats, count, previous_time, decreases, exact_accepted_times = {}, 0, None, 0, 0
        accepted_set = set(accepted_times)
        with stage_path.open() as stream:
            for line in stream:
                row = json.loads(line)
                require(0 <= row['time_s'] <= 10, 'RHS stage time')
                inspect_evaluation(row['evaluation'], external, stage_stats)
                decreases += previous_time is not None and row['time_s'] < previous_time
                exact_accepted_times += row['time_s'] in accepted_set
                previous_time = row['time_s']
                count += 1
        require(count == report['nfev'] == report['logged_rhs'], 'RHS log nfev identity')
        original_gates = dict(temperature=terr / 4 <= D('1e-6'),
            local_energy=sample_stats['local_energy_error_j'] / 80 <= D('1e-8'),
            global_energy=sample_stats['global_energy_error_j'] / 80 <= D('1e-8'))
        require(original_gates == saved_metrics['gates'], 'original sample gates disagree')
        for gate, passed in original_gates.items():
            gates[name + '_' + gate] = passed
        # Decimal identities differ from cancellation-prone float expressions by
        # a few final bits. These differences are descriptive, not new tolerances.
        metric_differences = {key: dec(saved_metrics[key]) - sample_stats[key]
                              for key in ['temperature_error_k', 'local_energy_error_j', 'global_energy_error_j']}
        metric_differences['entropy_identity_error_j_k'] = dec(saved_metrics['entropy_identity_error_j_k']) - sample_stats['entropy_identity_error_j_k_descriptive']
        audited[name] = dict(samples=101, accepted_states=len(accepted_states), accepted_steps=len(accepted_states) - 1,
            nfev=count, RHS_log_time_decreases=decreases, RHS_calls_at_an_accepted_time=exact_accepted_times,
            stage_classification='RHS calls include trial/possibly rejected stages and dense-output construction, not accepted states.',
            sample_decimal=sample_stats, accepted_prefix_decimal=accepted_stats,
            sample_reported_field_discrepancy=evaluation_stats, all_RHS_reported_field_discrepancy=stage_stats,
            saved_metric_minus_decimal=metric_differences, saved_pointwise_minus_decimal=pointwise_difference,
            original_sample_gates=original_gates)
    refinement = max(abs(dec(a[i]) - dec(b[i])) for a, b in zip(reports['coarse']['samples'], reports['fine']['samples'], strict=True) for i in range(2))
    require(dec(result['refinement_difference_k']) == refinement, 'refinement metric')
    require(negative['method'] == 'omit_rank_one_thermal_coupling' and negative['times_s'] == times
            and len(negative['temperatures_k']) == 101 and negative['temperatures_k'][0] == initial_t, 'negative control grid/identity')
    neg_error = max(abs(dec(a[i]) - dec(b[i])) for a, b in zip(negative['temperatures_k'], ref_t, strict=True) for i in range(2))
    require(dec(negative['reference_error_k']) == neg_error, 'negative metric')
    detected = neg_error / 4 > D('1e-6')
    require(negative['detected_by_temperature_gate'] == detected, 'negative gate')
    gates.update(time_refinement=refinement / 4 <= D('1e-7'), negative_control_detected=detected)
    require(result['gates'] == gates and result['numerical_policy_pass'] == all(gates.values()), 'combined gates')
    return dict(supervised_elapsed_s=execution['elapsed_s'], supervisor_exit_code=0, timeout_s=10,
        initial_U_j=V * sum(initial['u']), initial_S_j_k=V * sum(initial['s']),
        trajectories=audited, reference_audit=ref_audit, refinement_difference_k=refinement,
        negative_audit=dict(reference_error_k=neg_error, detected_by_original_temperature_gate=detected,
                            **reference_bounds(negative)), original_gates=gates)


def main():
    require(not (OUT / 'AUDIT01.json').exists(), 'audit output exists; use a distinct attempt')
    identity = source_identity()
    with (OUT / 'RECONSTRUCTION01.jsonl').open('x') as reconstruction:
        cases = {case: audit_case(case, reconstruction) for case in ['relaxation', 'cooling']}
    after = {name: digest(Path(name)) for name in INPUT_HASHES}
    require(after == INPUT_HASHES, 'original evidence changed during audit')
    emit(OUT / 'AUDIT01.json', dict(status='completed_saved_arithmetic_audit',
        python=sys.version, decimal_precision=getcontext().prec,
        no_application_or_scipy_import=True, no_RHS_or_ODE_or_new_trajectory_root_solve=True,
        arithmetic='Exact declared decimal constants; Decimal.from_float for saved binary64 JSON values.',
        source_identity=identity, cases=cases, original_artifact_sha256=INPUT_HASHES,
        original_artifacts_unchanged=True, entropy_gate_added=False,
        material_qualified=False, spatial_convergence_demonstrated=False, full_firing_cycle=False))
    print(json.dumps({'status': 'completed_saved_arithmetic_audit', 'cases': list(cases),
                      'result': str(OUT / 'AUDIT01.json')}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        error = traceback.format_exc()
        candidate = OUT / 'ATTEMPT01_FAILURE.json'
        if not candidate.exists():
            emit(candidate, dict(status='audit_script_failed', traceback=error,
                 note='Only saved arithmetic audit; no formal trajectory was run or modified.'))
        raise
