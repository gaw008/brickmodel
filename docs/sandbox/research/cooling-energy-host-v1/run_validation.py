"""Frozen native-energy cooling experiment; no integration occurs on import.

Run only after independent review, installation and a root-produced freeze.
Pure/fake tests explicitly cannot qualify a real native trajectory.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from fractions import Fraction as F
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[3]
OLD = ROOT.parent / 'cooling-stress-v1/execution/cooling01/worker'
FINE_SHA256 = '87765e841b2faec698c36ff90af7cfb698c4874b87192d287d0ac86c0111586d'
MODULES = ('integration', 'geometry', 'exchanges', 'cooling_thermoelastic_plate',
           'thermoelastic_energy_storage', 'thermoelastic_energy_host')
QUALIFICATIONS = dict(material_qualified=False, chemical_mass_qualified=False,
    full_cycle_qualified=False, source_material_qualified=False,
    deployment='offline_research', classification='manufactured_test_fixture')
PARAMETERS = dict(biaxial_modulus_pa=1e9, linear_expansion_per_k=1e-4,
    stress_free_heat_capacity_j_m3_k=1e5, reference_temperature_k=300.,
    conductivity_w_m_k=1., temperature_bounds_k=(290., 310.),
    strain_bounds=(-.01, .01), outer_temperature_k=300.,
    outer_boundary='fixed_temperature', coefficient_classification='manufactured',
    mechanical_regime='symmetric_free_plane_stress')
INVERSE_POLICY = dict(energy_tolerance_j=1e-10, temperature_tolerance_k=1e-9,
                      maximum_iterations=200, square_root_bits=160)


def jsonable(value):
    """Serialize immutable native records without deepcopy of MappingProxyType."""
    if isinstance(value, F):
        return dict(numerator=str(value.numerator), denominator=str(value.denominator))
    if is_dataclass(value):
        return {field.name: jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if hasattr(value, 'tolist'):
        return value.tolist()
    return value


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(jsonable(value), stream, allow_nan=False, separators=(',', ':'))
        stream.write('\n')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_freeze(path):
    """A fixed experiment binding, not an arbitrary source discovery service."""
    freeze = json.loads(Path(path).read_text())
    if freeze.get('schema') != 'cooling_energy_host_freeze_v1':
        raise ValueError('unsupported_freeze_schema')
    required = {str(p.resolve()) for p in (ROOT/'run_validation.py', ROOT/'supervise.py',
                ROOT/'PREREGISTRATION.md', OLD/'fine.json', OLD/'reference.json')}
    if not required <= set(freeze['files']):
        raise ValueError('required_driver_protocol_reference_hashes_missing')
    if freeze['files'][str((OLD/'fine.json').resolve())] != FINE_SHA256:
        raise ValueError('prior_fine_reference_identity_mismatch')
    if set(freeze['modules']) != set(MODULES):
        raise ValueError('required_native_module_bindings_missing')
    prefix = Path(freeze['python_prefix'])
    executable = Path(freeze['python_executable'])
    if not prefix.is_absolute() or not executable.is_absolute():
        raise ValueError('absolute_installed_python_identity_required')
    if not executable.is_relative_to(prefix):
        raise ValueError('python_executable_outside_registered_environment')
    for name, binding in freeze['modules'].items():
        expected = REPOSITORY/'src/sludge_sandbox'/f'{name}.py'
        if Path(binding['source']).resolve() != expected.resolve():
            raise ValueError('module_source_outside_expected_repository')
        installed = Path(binding['installed'])
        if not installed.is_absolute() or not installed.resolve().is_relative_to(prefix.resolve()):
            raise ValueError('module_not_bound_to_installed_environment')
        if 'site-packages' not in installed.parts:
            raise ValueError('noneditable_installed_modules_required')
    # Access required interpreter/dependency identity fields before launch.
    if not all(isinstance(freeze[k], str) and freeze[k] for k in
               ('python_version', 'python_binary_sha256', 'numpy_version')):
        raise ValueError('explicit_interpreter_dependency_identity_required')
    return freeze


def verify_freeze(freeze, freeze_path):
    observed = {str(Path(freeze_path).resolve()): sha256(freeze_path)}
    for path, expected in freeze['files'].items():
        actual = sha256(path)
        observed[path] = actual
        if actual != expected:
            raise ValueError(f'frozen_input_changed:{path}')
    for name, binding in freeze['modules'].items():
        for kind in ('source', 'installed'):
            actual = sha256(binding[kind])
            observed[binding[kind]] = actual
            if actual != binding['sha256']:
                raise ValueError(f'frozen_{kind}_module_changed:{name}')
    binary = str(Path(freeze['python_executable']).resolve())
    observed[binary] = sha256(binary)
    if observed[binary] != freeze['python_binary_sha256']:
        raise ValueError('installed_python_binary_changed')
    return observed


def import_runtime(freeze):
    if not sys.flags.isolated or str(Path(sys.executable).absolute()) != freeze['python_executable']:
        raise ValueError('frozen_python_with_isolated_flag_required')
    if str(Path(sys.prefix).resolve()) != str(Path(freeze['python_prefix']).resolve()):
        raise ValueError('installed_prefix_mismatch')
    if sys.version != freeze['python_version']:
        raise ValueError('python_version_mismatch')
    modules = {name: importlib.import_module('sludge_sandbox.'+name) for name in MODULES}
    for name, module in modules.items():
        if Path(module.__file__).resolve() != Path(freeze['modules'][name]['installed']).resolve():
            raise ValueError(f'import_did_not_use_frozen_installed_module:{name}')
    numpy = importlib.import_module('numpy')
    if numpy.__version__ != freeze['numpy_version']:
        raise ValueError('numpy_version_mismatch')
    return modules, numpy


def read_references():
    fine = json.loads((OLD/'fine.json').read_text())
    reference = json.loads((OLD/'reference.json').read_text())
    times = tuple(fine['times_s'])
    other = tuple(reference['times_s'])
    if len(times) != 101 or tuple(map(float.hex, times)) != tuple(map(float.hex, other)):
        raise ValueError('exact_original_comparison_times_required')
    if times[0] != 0. or times[-1] != 10. or any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError('invalid_original_times')
    old_temperatures = [row[:2] for row in fine['samples']]
    old_stress = [[point['stress_pa'] for point in row['points']] for row in fine['observations']]
    dense = reference['temperatures_k']
    for rows in (old_temperatures, old_stress, dense):
        if len(rows) != 101 or any(len(row) != 2 or not all(math.isfinite(x) for x in row) for row in rows):
            raise ValueError('invalid_existing_reference_arrays')
    if fine['status'] != 'completed':
        raise ValueError('prior_fine_not_completed')
    return dict(times_s=times, fine_temperatures_k=old_temperatures,
                reference_temperatures_k=dense, fine_stress_pa=old_stress,
                reference_method=reference['method'],
                provenance='existing_B_temperature_path_and_independently_assembled_dense_matrix')


def policy_parameters(step):
    return dict(initial_step_s=step, maximum_step_s=step, minimum_step_s=1e-8,
        relative_tolerance=1e-9, amount_absolute_tolerance_mol=1e-12,
        energy_absolute_tolerance_j=1e-11, amount_scale_mol=1., energy_scale_j=80.,
        maximum_steps=12000, maximum_rejections=1000, maximum_wall_seconds=60.)


def state_record(state):
    record = jsonable(state)
    record['amounts_binary64_bytes_hex'] = state.amounts_mol.tobytes().hex()
    record['amounts_dtype'] = state.amounts_mol.dtype.str
    record['internal_energy_binary64_hex'] = [float(x).hex() for x in state.internal_energy_j]
    return record


def result_record(result):
    record = {field.name: jsonable(getattr(result, field.name)) for field in fields(result)
              if field.name != 'states'}
    record['states'] = [state_record(state) for state in result.states]
    record['accepted_prefix_provenance'] = 'IntegrationResult.states_times_s_steps_returned_together'
    return record


def independent_stage(plate):
    """Reconstruct u_dot, Q, P and stress from declared constants and returned Tdot."""
    temperatures, td = tuple(plate.temperatures_k), tuple(plate.temperature_rates_k_s)
    mean, mean_rate = math.fsum(temperatures)/2., math.fsum(td)/2.
    strain, edot = 1e-4*(mean-300.), 1e-4*mean_rate
    stress = tuple(1e9*1e-4*(mean-t) for t in temperatures)
    heat = (temperatures[1]-temperatures[0],
            temperatures[0]-temperatures[1]+2.*(300.-temperatures[1]))
    power = tuple(2.*1e-4*s*edot for s in stress)
    derivative = tuple(1e-4*((1e5-2.*t*1e9*1e-4**2)*rate
                      + 2.*1e9*(strain+1e-4*300.)*edot)
                       for t, rate in zip(temperatures, td))
    return dict(stress_pa=stress, cell_power_w=power,
        energy_equation_residual_w=tuple(math.fsum((u, -q, -p)) for u, q, p in zip(derivative, heat, power)),
        reported_stress_difference_pa=tuple(point.stress_pa-s for point, s in zip(plate.points, stress)),
        reported_power_difference_w=tuple(actual-p for actual, p in zip(plate.cell_mechanical_power_w, power)))


def inventory_and_rates_valid(state, rates, fixed):
    return (state.amounts_mol.shape == fixed.shape and state.amounts_mol.tobytes() == fixed.tobytes()
        and state.mechanical_stretches is None and rates.mechanical_rates_per_s is None
        and all(float(x) == 0. for x in rates.face_species_mol_s.flat)
        and all(float(x) == 0. for x in rates.reaction_species_mol_s.flat)
        and rates.cell_power_components_w is not None
        and set(rates.cell_power_components_w) == {'mechanical_constraint'}
        and rates.cell_power_components_w['mechanical_constraint'].tobytes() == rates.cell_power_w.tobytes())


class EvaluationSummary:
    """Online summary of actual calls; never a source of accepted states."""
    def __init__(self, host):
        self.host = host
        self.data = dict(calls_started=0, calls_succeeded=0, calls_failed=0,
            failed_exception_counts={}, inventory_and_rate_contract=True, all_decodes_certified=True,
            min_temperature_k=None, max_temperature_k=None,
            maximum_energy_residual_bound_j=0., maximum_temperature_error_bound_k=0.,
            maximum_iterations=0, decoder_elapsed_s=0., maximum_decoder_elapsed_s=0.,
            maximum_independent_stage_energy_residual_w=0.,
            maximum_independent_stress_difference_pa=0., maximum_independent_power_difference_w=0.,
            maximum_native_power_reconstruction_difference_w=0.,
            maximum_actual_total_constraint_power_abs_w=0., worst_energy_certificate=None,
            worst_temperature_certificate=None)

    def evaluate(self, state, at):
        d = self.data
        d['calls_started'] += 1
        try:
            result = self.host.evaluate(state, at)
        except Exception as exc:
            d['calls_failed'] += 1
            name = type(exc).__name__
            d['failed_exception_counts'][name] = d['failed_exception_counts'].get(name, 0)+1
            raise
        inverse, rates = result.inverse, result.rates
        decoded, plate = inverse.state, inverse.state.plate_evaluation
        d['calls_succeeded'] += 1
        d['inventory_and_rate_contract'] &= inventory_and_rates_valid(state, rates, self.host.fixed_amounts_mol)
        bound = max(inverse.combined_energy_residual_bound_j)
        temperature_bound = inverse.temperature_error_bound_k
        certified = (math.isfinite(bound) and math.isfinite(temperature_bound)
            and 0. <= bound <= INVERSE_POLICY['energy_tolerance_j']
            and 0. <= temperature_bound <= INVERSE_POLICY['temperature_tolerance_k']
            and inverse.minimum_energy_jacobian_eigenvalue_j_k > 0.
            and 0 <= inverse.iterations <= INVERSE_POLICY['maximum_iterations']
            and inverse.target_interval_admissible
            and all(float(x) == 0. for x in inverse.target.absolute_error_j)
            and tuple(inverse.target.cell_energy_j) == tuple(state.internal_energy_j)
            and all(290. <= t <= 310. for t in decoded.temperatures_k))
        d['all_decodes_certified'] &= certified
        certificate = None
        for key, value, witness in (
            ('maximum_energy_residual_bound_j', bound, 'worst_energy_certificate'),
            ('maximum_temperature_error_bound_k', temperature_bound, 'worst_temperature_certificate')):
            if value > d[key] or d[witness] is None:
                if certificate is None:
                    certificate = dict(time_s=float(at), state_energy_j=jsonable(state.internal_energy_j),
                                       inverse=jsonable(inverse))
                d[key], d[witness] = value, certificate
        low, high = min(decoded.temperatures_k), max(decoded.temperatures_k)
        d['min_temperature_k'] = low if d['min_temperature_k'] is None else min(low, d['min_temperature_k'])
        d['max_temperature_k'] = high if d['max_temperature_k'] is None else max(high, d['max_temperature_k'])
        d['maximum_iterations'] = max(d['maximum_iterations'], inverse.iterations)
        d['decoder_elapsed_s'] += inverse.elapsed_s
        d['maximum_decoder_elapsed_s'] = max(d['maximum_decoder_elapsed_s'], inverse.elapsed_s)
        independent = independent_stage(plate)
        for key, values in (
            ('maximum_independent_stage_energy_residual_w', independent['energy_equation_residual_w']),
            ('maximum_independent_stress_difference_pa', independent['reported_stress_difference_pa']),
            ('maximum_independent_power_difference_w', independent['reported_power_difference_w'])):
            d[key] = max(d[key], *(abs(value) for value in values))
        d['maximum_native_power_reconstruction_difference_w'] = max(
            d['maximum_native_power_reconstruction_difference_w'],
            *(abs(float(native)-reconstructed) for native, reconstructed in
              zip(rates.cell_power_w, independent['cell_power_w'], strict=True)))
        d['maximum_actual_total_constraint_power_abs_w'] = max(
            d['maximum_actual_total_constraint_power_abs_w'], abs(math.fsum(rates.cell_power_w)))
        return result


def save_run(host, initial, integrate, policy, times, output, name, *, real_native_integration):
    summary = EvaluationSummary(host)
    started = time.monotonic()
    with (output/f'{name}-rhs-trials.jsonl').open('x') as stream:
        def operator(state, at):
            evaluation = summary.evaluate(state, at)
            if summary.data['calls_started'] % 512 == 0:
                witness = dict(kind='RHS_trial_not_accepted_state', real_native_integration=real_native_integration,
                    time_s=float(at), state=state_record(state), summary=summary.data,
                    accepted_prefix_status='unknown_until_integrate_returns')
                stream.write(json.dumps(jsonable(witness), allow_nan=False, separators=(',', ':'))+'\n')
                stream.flush()
            return evaluation.rates
        result = integrate(initial, operator, start_s=0., end_s=10., policy=policy,
                           breakpoints_s=tuple(times[1:-1]))
    # Save the complete returned prefix before any accepted-state reconstruction.
    write_new(output/f'{name}.json', dict(real_native_integration=real_native_integration,
        qualifications=QUALIFICATIONS, policy=policy, result=result_record(result),
        rhs_summary=summary.data, driver_elapsed_to_return_s=time.monotonic()-started))
    return result, summary.data


def audit_prefix(result, fixed):
    """Exact accumulation of represented ledger exchanges at EVERY accepted prefix."""
    if len(result.states) != len(result.times_s) or len(result.steps)+1 != len(result.states):
        raise ValueError('native_state_time_ledger_count_mismatch')
    if not result.times_s or result.times_s[0] != 0.:
        raise ValueError('native_initial_time_missing')
    initial = result.states[0]
    energy0 = [F(float(x)) for x in initial.internal_energy_j]
    heat, work, boundary = [F(), F()], [F(), F()], F()
    records = []
    valid = True
    max_local, max_global, max_constraint = F(), F(), F()
    for index, (at, state) in enumerate(zip(result.times_s, result.states)):
        valid &= (state.amounts_mol.shape == fixed.shape and state.amounts_mol.tobytes() == fixed.tobytes()
                  and state.mechanical_stretches is None
                  and state.energy_model_identity == initial.energy_model_identity)
        if index:
            step = result.steps[index-1]
            if step.start_s != result.times_s[index-1] or step.end_s != at or step.start_s >= at:
                raise ValueError('native_ledger_endpoints_mismatch')
            valid &= (all(float(x) == 0. for x in step.face_species_mol.flat)
                and all(float(x) == 0. for x in step.reaction_species_mol.flat)
                and step.stretch_increment is None and step.stretch_quadrature_roundoff is None
                and step.cell_work_components_j is not None
                and set(step.cell_work_components_j) == {'mechanical_constraint'}
                and step.cell_work_components_j['mechanical_constraint'].tobytes() == step.cell_work_j.tobytes()
                and step.component_quadrature_roundoff_j is not None
                and set(step.component_quadrature_roundoff_j) == {'mechanical_constraint'})
            faces = [F(float(x)) for x in step.face_energy_j]
            for cell in range(2):
                heat[cell] += faces[cell]-faces[cell+1]
                work[cell] += F(float(step.cell_work_j[cell]))
            boundary += faces[0]-faces[-1]
        delta = [F(float(x))-e0 for x, e0 in zip(state.internal_energy_j, energy0)]
        local = [de-q-p for de, q, p in zip(delta, heat, work)]
        global_residual, total_work = sum(delta, F())-boundary, sum(work, F())
        max_local = max(max_local, *map(abs, local))
        max_global, max_constraint = max(max_global, abs(global_residual)), max(max_constraint, abs(total_work))
        records.append(dict(time_s=at, local_energy_residual_j=local,
            global_heat_residual_j=global_residual, cumulative_boundary_heat_j=boundary,
            cumulative_cell_heat_j=list(heat), cumulative_cell_work_j=list(work),
            total_constraint_work_residual_j=total_work))
    threshold = F(80)*F(1e-8)
    return dict(all_prefixes=records, exact_accumulation='Fraction_of_represented_StepLedger_binary64',
        inventory_stretch_and_work_contract=bool(valid), maximum_local_energy_residual_j=max_local,
        maximum_global_heat_residual_j=max_global, maximum_total_constraint_work_residual_j=max_constraint,
        local_energy_gate=max_local <= threshold, global_heat_gate=max_global <= threshold)


def analyze_run(host, result, rhs_summary, references):
    ledger = audit_prefix(result, host.fixed_amounts_mol)
    decoded = EvaluationSummary(host)
    desired = {float(t).hex(): index for index, t in enumerate(references['times_s'])}
    comparisons = []
    for index, (at, state) in enumerate(zip(result.times_s, result.states)):
        evaluated = decoded.evaluate(state, at)
        key = float(at).hex()
        if key in desired:
            old_index = desired[key]
            temperatures = tuple(evaluated.inverse.state.temperatures_k)
            plate = evaluated.inverse.state.plate_evaluation
            stress = [point.stress_pa for point in plate.points]
            comparisons.append(dict(time_s=at, accepted_index=index, reference_index=old_index,
                temperatures_k=temperatures, in_plane_strain=evaluated.inverse.state.in_plane_strain,
                stress_pa=stress, inverse=evaluated.inverse, ledger=ledger['all_prefixes'][index],
                fine_temperature_difference_k=[t-r for t, r in zip(temperatures, references['fine_temperatures_k'][old_index])],
                reference_temperature_difference_k=[t-r for t, r in zip(temperatures, references['reference_temperatures_k'][old_index])],
                fine_stress_difference_pa=[s-r for s, r in zip(stress, references['fine_stress_pa'][old_index])],
                independent_stress_difference_pa=independent_stage(plate)['reported_stress_difference_pa']))
    complete_points = [row['reference_index'] for row in comparisons] == list(range(101))
    errors = {name: max((abs(value) for row in comparisons for value in row[name]), default=None)
              for name in ('fine_temperature_difference_k', 'reference_temperature_difference_k',
                           'fine_stress_difference_pa', 'independent_stress_difference_pa')}
    complete = result.status == 'completed' and result.times_s[-1] == 10. and complete_points
    gates = dict(complete=complete, local_energy=ledger['local_energy_gate'], global_heat=ledger['global_heat_gate'],
        inventory_stretch_work=ledger['inventory_stretch_and_work_contract']
            and decoded.data['inventory_and_rate_contract'] and rhs_summary['inventory_and_rate_contract'],
        storage_decode=decoded.data['all_decodes_certified'] and rhs_summary['all_decodes_certified'],
        native_rhs_count_matches=result.evaluations == rhs_summary['calls_started'],
        temperature_to_old_fine=complete_points and errors['fine_temperature_difference_k']/4. <= 1e-6,
        temperature_to_independent_reference=complete_points and errors['reference_temperature_difference_k']/4. <= 1e-6)
    return dict(gates=gates, comparison_points=comparisons, maximum_absolute_differences=errors,
        accepted_state_decode_summary=decoded.data, native_rhs_summary=rhs_summary, ledger=ledger,
        domain_claim='actual_guarded_RHS_and_returned_accepted_points_only_no_continuous_solution_certificate',
        stress_acceptance='descriptive_no_new_stress_threshold')


def run_experiment(host, initial, integrate, policy_factory, references, output, *, real_native_integration=False):
    """Only main can supply the checked installed native callable in a real run."""
    raw, reports = {}, {}
    for name, step in (('coarse', .005), ('fine', .0025)):
        result, summary = save_run(host, initial, integrate, policy_factory(**policy_parameters(step)),
            references['times_s'], output, name, real_native_integration=real_native_integration)
        raw[name] = (result, summary)
        if result.status != 'completed':
            break
    for name, (result, summary) in raw.items():
        reports[name] = analyze_run(host, result, summary, references)
        write_new(output/f'{name}-audit.json', dict(real_native_integration=real_native_integration,
                                                   qualifications=QUALIFICATIONS, **reports[name]))
    time_difference = None
    if set(reports) == {'coarse', 'fine'} and all(r['gates']['complete'] for r in reports.values()):
        time_difference = max(abs(t-u) for coarse, fine in zip(reports['coarse']['comparison_points'],
            reports['fine']['comparison_points'], strict=True)
            for t, u in zip(coarse['temperatures_k'], fine['temperatures_k'], strict=True))
    time_gate = time_difference is not None and time_difference/4. <= 1e-7
    gates = {name: report['gates'] for name, report in reports.items()}
    passed = (real_native_integration and len(reports) == 2 and time_gate
              and all(all(report['gates'].values()) for report in reports.values()))
    return dict(real_native_integration=real_native_integration, passed=bool(passed), qualifications=QUALIFICATIONS,
        gates=gates, maximum_coarse_fine_temperature_difference_k=time_difference, time_convergence_gate=time_gate,
        run_status={name: (raw[name][0].status if name in raw else 'not_started') for name in ('coarse', 'fine')})


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    started = time.monotonic()
    args.output.mkdir(parents=True, exist_ok=False)
    final = dict(passed=False, real_native_integration=False, qualifications=QUALIFICATIONS)
    before = None
    try:
        freeze = read_freeze(args.freeze)
        before = verify_freeze(freeze, args.freeze)
        modules, np = import_runtime(freeze)
        references = read_references()
        plate = modules['cooling_thermoelastic_plate'].CoolingThermoelasticPlate(
            reference=modules['geometry'].ReferenceSlab(.02, .01, 2), **PARAMETERS)
        host = modules['thermoelastic_energy_host'].ThermoelasticEnergyHost(
            storage=modules['thermoelastic_energy_storage'].ThermoelasticEnergyStorage(plate),
            fixed_amounts_mol=np.array([[2.], [3.]], dtype=np.float64),
            inverse_policy=modules['thermoelastic_energy_storage'].EnergyInversePolicy(**INVERSE_POLICY))
        initial, forward = host.state_from_temperatures((304., 304.))
        write_new(args.output/'INPUTS.json', dict(freeze=freeze, input_sha256_before=before,
            initial_state=state_record(initial), initialization_forward_certificate=forward,
            parameters=PARAMETERS, inverse_policy=INVERSE_POLICY, references=references,
            qualifications=QUALIFICATIONS, inventory_role='explicit_fixed_bookkeeping_outside_caloric_law',
            target_input_uncertainty_j=[0., 0.], initialization_roundoff_kept_separate=True))
        final['real_native_integration'] = True
        final.update(run_experiment(host, initial, modules['integration'].integrate,
            modules['integration'].IntegrationPolicy, references, args.output, real_native_integration=True))
    except Exception as exc:
        final.update(passed=False, error_type=type(exc).__name__, error=str(exc))
    try:
        after = verify_freeze(freeze, args.freeze) if before is not None else None
        unchanged = before is not None and before == after
        final.update(input_sha256_before=before, input_sha256_after=after, inputs_unchanged=unchanged)
        final['passed'] &= unchanged
    except Exception as exc:
        final.update(passed=False, inputs_unchanged=False, post_verification_error=f'{type(exc).__name__}:{exc}')
    final['elapsed_s'] = time.monotonic()-started
    write_new(args.output/'RESULT.json', final)
    return 0 if final['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
