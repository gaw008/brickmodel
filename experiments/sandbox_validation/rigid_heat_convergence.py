"""Manufactured rigid-gas heat convergence; actual shared model and integrator.

Write the preregistration before running. Every run writes a new report; an
existing output is never overwritten. This is not a wet-brick validation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import traceback
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / 'docs/sandbox/research/RIGID_HEAT_CONVERGENCE.md'
SOURCE_PATHS = (
    'src/sludge_sandbox/__init__.py',
    'src/sludge_sandbox/materials.py',
    'src/sludge_sandbox/thermochemistry.py',
    'src/sludge_sandbox/gas_transport.py',
    'src/sludge_sandbox/exchanges.py',
    'src/sludge_sandbox/reactions.py',
    'src/sludge_sandbox/integration.py',
    'src/sludge_sandbox/gas_heat_model.py',
    'experiments/sandbox_validation/rigid_heat_convergence.py',
)
SOURCE_IDS = ('manufactured:rigid-heat-convergence-v1',)
CP, GAS_R, CV, T_REFERENCE = 30., 8., 22., 298.15
LENGTH, AREA, MOLAR_DENSITY, CONDUCTIVITY = 1., 1., 1., 1.
MEAN_T, AMPLITUDE = 600., 10.
ENERGY_TOLERANCE_J, AMOUNT_TOLERANCE_MOL = 1e-8, 1e-12
ORDER_MIN, ORDER_MAX = 1.8, 2.2
PEAK_RSS_LIMIT_MIB, TOTAL_WALL_LIMIT_S = 512., 360.


def source_hashes() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCE_PATHS}


def peak_rss_mib() -> float:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == 'darwin':
        return raw/(1024*1024)
    if sys.platform.startswith('linux'):
        return raw/1024
    raise RuntimeError('RSS units not registered for this platform')


def git_context() -> dict[str, Any]:
    def git(*args: str) -> str:
        result = subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True, check=True)
        return result.stdout.strip()
    return {'head': git('rev-parse', 'HEAD'),
            'relevant_working_tree_status': git('status', '--short', '--', *SOURCE_PATHS),
            'head_is_source_binding': False,
            'binding_note': 'Actual file SHA-256 values bind this run; HEAD alone does not bind uncommitted files.'}


def initial_cell_averages(cells: int) -> tuple[float, ...]:
    z = math.pi/(2*cells)
    sinc = math.sin(z)/z
    return tuple(MEAN_T+AMPLITUDE*sinc*math.cos(math.pi*(i+.5)/cells) for i in range(cells))


def exact_cell_averages(cells: int, at_s: float, *, discrete: bool) -> tuple[float, ...]:
    dx = LENGTH/cells
    decay_rate = (4*math.sin(math.pi/(2*cells))**2/(CV*MOLAR_DENSITY*dx*dx)
                  if discrete else math.pi**2/(CV*MOLAR_DENSITY*LENGTH*LENGTH))
    decay = math.exp(-CONDUCTIVITY*decay_rate*at_s)
    return tuple(MEAN_T+(value-MEAN_T)*decay for value in initial_cell_averages(cells))


def run_case(cells: int, step_s: float, end_s: float, *, reference: str) -> dict[str, Any]:
    # Imports remain inside the measured/error-recorded path: dependency or core
    # import failures also produce an explicit failed artifact via main().
    import numpy as np
    from sludge_sandbox.gas_heat_model import GasHeatModel
    from sludge_sandbox.integration import IntegrationPolicy, integrate
    from sludge_sandbox.thermochemistry import ShomateGas, ShomateSegment, Thermochemistry

    begin = time.perf_counter()
    dx = LENGTH/cells
    stability_number = 2*CONDUCTIVITY*step_s/(CV*MOLAR_DENSITY*dx*dx)
    if stability_number > 1:
        raise ValueError('preregistered explicit diffusion stability condition failed')
    segment = ShomateSegment((300., 1800.), (CP, 0, 0, 0, 0, -CP*T_REFERENCE/1000, 0, 0),
                             0., GAS_R, SOURCE_IDS)
    gas = ShomateGas('manufactured-gas', (segment,), 'manufactured_test_fixture', SOURCE_IDS)
    thermo = Thermochemistry('manufactured-rigid-heat-caloric-v1', {'manufactured-gas': gas}, GAS_R,
                             SOURCE_IDS, allow_manufactured=True)
    zeros, ones = (0.,)*cells, (1.,)*cells
    operator = GasHeatModel(
        thermochemistry=thermo, species_order=('manufactured-gas',),
        molar_masses_kg_mol={'manufactured-gas': .012}, face_area_m2=AREA,
        cell_widths_m=(dx,)*cells, gas_volumes_m3=(AREA*dx,)*cells,
        conductivities_w_m_k=(CONDUCTIVITY,)*cells,
        effective_diffusivities_m2_s={'manufactured-gas': zeros},
        permeability_m2=zeros, relative_permeability=ones, viscosity_pa_s=ones,
        coefficient_source_ids=SOURCE_IDS, coefficient_set_id='manufactured-rigid-heat-convergence',
        coefficient_version='1', coefficient_classification='manufactured', allow_manufactured=True,
    )
    initial = operator.state_from_temperatures([[MOLAR_DENSITY*AREA*dx]]*cells, initial_cell_averages(cells))
    policy = IntegrationPolicy(
        initial_step_s=step_s, maximum_step_s=step_s, minimum_step_s=1e-12,
        relative_tolerance=.01, amount_absolute_tolerance_mol=AMOUNT_TOLERANCE_MOL,
        energy_absolute_tolerance_j=ENERGY_TOLERANCE_J, amount_scale_mol=1.,
        energy_scale_j=CV*MOLAR_DENSITY*AREA*LENGTH*AMPLITUDE,
        maximum_steps=1000, maximum_rejections=10, maximum_wall_seconds=120.,
    )
    result = integrate(initial, operator, start_s=0., end_s=end_s, policy=policy)
    final = result.states[-1]
    # Algebraically independent decoder for this one explicitly manufactured gas.
    observed = tuple((float(u)/float(n[0])+CP*T_REFERENCE)/CV
                     for n, u in zip(final.amounts_mol, final.internal_energy_j))
    expected = exact_cell_averages(cells, end_s, discrete=reference == 'discrete')
    differences = tuple(a-b for a, b in zip(observed, expected))
    maximum_error = max(abs(value) for value in differences)
    l2_error = math.sqrt(math.fsum(value*value for value in differences)/cells)
    initial_energy = math.fsum(float(value) for value in initial.internal_energy_j)
    initial_amount = math.fsum(float(value) for value in initial.amounts_mol.flat)
    total_energy_residual = max(abs(math.fsum(float(value) for value in state.internal_energy_j)-initial_energy)
                                for state in result.states)
    total_amount_residual = max(abs(math.fsum(float(value) for value in state.amounts_mol.flat)-initial_amount)
                                for state in result.states)
    cell_ledger_residuals = []
    for cell in range(cells):
        # Sum actual accepted ledger face values independently from the core's
        # Fraction accumulator and evaluate the entire experiment's balance.
        inputs = [float(final.internal_energy_j[cell]), -float(initial.internal_energy_j[cell])]
        for ledger in result.steps:
            inputs.extend((-float(ledger.face_energy_j[cell]), float(ledger.face_energy_j[cell+1])))
        cell_ledger_residuals.append(math.fsum(inputs))
    accepted_lengths = tuple(b-a for a, b in zip(result.times_s, result.times_s[1:]))
    expected_steps = round(end_s/step_s)
    time_roundoff_tolerance = 64*max(math.ulp(end_s), math.ulp(step_s))
    checks = {
        'core_completed': result.status == 'completed',
        'requested_end_reached': result.times_s[-1] == end_s,
        'no_rejected_trials': result.rejected_trials == 0,
        'expected_accepted_step_count': len(result.steps) == expected_steps,
        'fixed_full_step_lengths': all(abs(value-step_s) <= time_roundoff_tolerance for value in accepted_lengths),
        'explicit_stage_stability': stability_number <= 1,
        'total_energy_conserved': total_energy_residual <= ENERGY_TOLERANCE_J,
        'per_cell_accepted_ledger_closes': max(map(abs, cell_ledger_residuals)) <= ENERGY_TOLERANCE_J,
        'global_amount_conserved': total_amount_residual <= AMOUNT_TOLERANCE_MOL,
        'each_inventory_unchanged': all(np.array_equal(state.amounts_mol, initial.amounts_mol) for state in result.states),
        'closed_boundary_energy': all(ledger.face_energy_j[0] == ledger.face_energy_j[-1] == 0 for ledger in result.steps),
        'no_species_exchange_or_reaction_or_work': all(
            np.count_nonzero(ledger.face_species_mol) == 0
            and np.count_nonzero(ledger.reaction_species_mol) == 0
            and np.count_nonzero(ledger.cell_work_j) == 0 for ledger in result.steps),
        'peak_rss_within_limit': peak_rss_mib() <= PEAK_RSS_LIMIT_MIB,
        'case_wall_within_limit': time.perf_counter()-begin <= 120.,
    }
    return {
        'cells': cells, 'requested_full_step_s': step_s, 'requested_end_s': end_s,
        'reference': reference, 'explicit_diffusion_stability_number': stability_number,
        'core_status': result.status, 'core_reason': result.reason,
        'accepted_steps': len(result.steps), 'evaluations': result.evaluations,
        'rejected_trials': result.rejected_trials, 'actual_times_s': result.times_s,
        'initial_cell_average_temperature_k': initial_cell_averages(cells),
        'observed_final_temperature_k': observed, 'reference_at_requested_end_k': expected,
        'maximum_temperature_error_k': maximum_error, 'l2_temperature_error_k': l2_error,
        'maximum_error_over_10k': maximum_error/AMPLITUDE,
        'total_energy_maximum_residual_j': total_energy_residual,
        'total_amount_maximum_residual_mol': total_amount_residual,
        'per_cell_ledger_residual_j': cell_ledger_residuals,
        'maximum_cell_ledger_residual_j': max(map(abs, cell_ledger_residuals)),
        'policy': asdict(policy), 'elapsed_seconds': time.perf_counter()-begin,
        'integrator_elapsed_seconds': result.elapsed_seconds, 'peak_rss_mib': peak_rss_mib(),
        'checks': checks, 'passed': all(checks.values()),
        'trajectory_internal_energy_j': [state.internal_energy_j.tolist() for state in result.states],
        'trajectory_amounts_mol': [state.amounts_mol.tolist() for state in result.states],
        'accepted_face_energy_j': [ledger.face_energy_j.tolist() for ledger in result.steps],
        'failure_trace_limitation': 'Only accepted states and ledgers are exposed by integrate; rejected trial states are not fabricated.',
    }


def observed_orders(cases: list[dict[str, Any]]) -> list[float | None]:
    errors = [case['maximum_temperature_error_k'] for case in cases]
    return [math.log2(left/right) if left > 0 and right > 0 else None
            for left, right in zip(errors, errors[1:])]


def run_benchmark(*, smoke: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    initial_hashes = source_hashes()
    report: dict[str, Any] = {
        'schema_version': 1, 'benchmark_id': 'rigid-heat-convergence-v1',
        'mode': 'smoke' if smoke else 'full_convergence', 'scientific_status': 'manufactured_rigid_gas_limit',
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'running',
        'python': sys.version, 'platform': platform.platform(), 'git_context': git_context(),
        'registration_path': str(REGISTRATION.relative_to(ROOT)),
        'registration_sha256': hashlib.sha256(REGISTRATION.read_bytes()).hexdigest(),
        'source_hashes_before': initial_hashes, 'cases': [],
        'constants': {'cp_j_mol_k': CP, 'R_j_mol_k': GAS_R, 'cv_j_mol_k': CV,
                      'length_m': LENGTH, 'area_m2': AREA, 'molar_density_mol_m3': MOLAR_DENSITY,
                      'conductivity_w_m_k': CONDUCTIVITY, 'mean_temperature_k': MEAN_T,
                      'initial_mode_amplitude_k': AMPLITUDE, 'manufactured_molar_mass_kg_mol': .012},
        'preregistered_thresholds': {'order_range': [ORDER_MIN, ORDER_MAX],
            'finest_space_normalized_maximum_error': 1e-3, 'space_time_contamination_fraction': .01,
            'energy_absolute_tolerance_j': ENERGY_TOLERANCE_J,
            'amount_absolute_tolerance_mol': AMOUNT_TOLERANCE_MOL,
            'total_wall_limit_s': TOTAL_WALL_LIMIT_S, 'rss_limit_mib': PEAK_RSS_LIMIT_MIB},
    }
    try:
        report['numpy_version'] = importlib.metadata.version('numpy')
        definitions = [(4, .002, .004, 'continuum', 'smoke')] if smoke else [
            (8, .002, .2, 'continuum', 'space'), (16, .002, .2, 'continuum', 'space'),
            (32, .002, .2, 'continuum', 'space'), (32, .001, .2, 'continuum', 'time_contamination'),
            (8, .1, .4, 'discrete', 'time'), (8, .05, .4, 'discrete', 'time'),
            (8, .025, .4, 'discrete', 'time'),
        ]
        for cells, step, end, reference, study in definitions:
            if time.perf_counter()-started >= TOTAL_WALL_LIMIT_S:
                raise TimeoutError('total_benchmark_wall_limit')
            record = run_case(cells, step, end, reference=reference)
            record['study'] = study
            report['cases'].append(record)
            print(f'{study} N={cells} h={step}: {record["core_status"]}, '
                  f'error={record["maximum_temperature_error_k"]:.9g} K, '
                  f'wall={record["elapsed_seconds"]:.3f} s', flush=True)
        checks = {'all_actual_cases_passed': all(case['passed'] for case in report['cases'])}
        if not smoke:
            spatial = [case for case in report['cases'] if case['study'] == 'space']
            temporal = [case for case in report['cases'] if case['study'] == 'time']
            fine_time = next(case for case in report['cases'] if case['study'] == 'time_contamination')
            p_space, p_time = observed_orders(spatial), observed_orders(temporal)
            contamination = max(abs(a-b) for a, b in zip(spatial[-1]['observed_final_temperature_k'],
                                                       fine_time['observed_final_temperature_k']))
            ratio = contamination/spatial[-1]['maximum_temperature_error_k'] if spatial[-1]['maximum_temperature_error_k'] else None
            report['convergence'] = {'space_orders': p_space, 'time_orders': p_time,
                                     'finest_space_step_halving_difference_k': contamination,
                                     'space_time_contamination_ratio': ratio}
            checks.update({
                'space_orders_in_range': all(p is not None and ORDER_MIN <= p <= ORDER_MAX for p in p_space),
                'time_orders_in_range': all(p is not None and ORDER_MIN <= p <= ORDER_MAX for p in p_time),
                'finest_space_error_below_threshold': spatial[-1]['maximum_error_over_10k'] <= 1e-3,
                'spatial_time_contamination_below_one_percent': ratio is not None and ratio <= .01,
            })
        final_hashes = source_hashes()
        report['source_hashes_after'] = final_hashes
        checks.update({'source_files_unchanged_during_run': initial_hashes == final_hashes,
                       'total_wall_within_limit': time.perf_counter()-started <= TOTAL_WALL_LIMIT_S,
                       'rss_within_limit': peak_rss_mib() <= PEAK_RSS_LIMIT_MIB})
        report['checks'] = checks
        report['status'] = 'passed' if all(checks.values()) else 'failed'
    except Exception as exc:
        report['status'] = 'failed'
        report['exception_type'] = type(exc).__name__
        report['exception_message'] = str(exc)
        report['traceback'] = traceback.format_exc()
    report['elapsed_seconds'] = time.perf_counter()-started
    report['peak_rss_mib'] = peak_rss_mib()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true', help='Exercise the actual model quickly; does not claim convergence')
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('Output already exists; preserve it and choose a new path')
    try:
        report = run_benchmark(smoke=args.smoke)
    except Exception as exc:
        report = {'schema_version': 1, 'benchmark_id': 'rigid-heat-convergence-v1', 'status': 'failed',
                  'exception_type': type(exc).__name__, 'exception_message': str(exc),
                  'traceback': traceback.format_exc()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also closes the overwrite race between the precheck
    # and writing a possibly long-running benchmark's final result.
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write('\n')
    print(f'{report["status"]}: {args.output}', flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())

