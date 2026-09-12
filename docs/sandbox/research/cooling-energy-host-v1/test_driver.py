"""Short fake/pure driver tests. real_native_integration=false in every fixture.

No invocation of sludge_sandbox.integration.integrate occurs here.
"""
from dataclasses import dataclass, replace
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from sludge_sandbox.integration import ConservedState, IntegrationPolicy, IntegrationResult, Rates, StepLedger

ROOT = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = load('run_validation')
supervisor = load('supervise')
REAL_NATIVE_INTEGRATION = False
FIXED = np.array([[2.], [3.]])


@dataclass
class FakePoint:
    stress_pa: float = 0.


@dataclass
class FakePlate:
    temperatures_k: tuple = (304., 304.)
    temperature_rates_k_s: tuple = (0., 0.)
    cell_mechanical_power_w: tuple = (0., 0.)
    points: tuple = (FakePoint(), FakePoint())


@dataclass
class FakeDecoded:
    temperatures_k: tuple = (304., 304.)
    in_plane_strain: float = .0004
    plate_evaluation: object = None


@dataclass
class FakeInverse:
    state: object
    target: object
    combined_energy_residual_bound_j: tuple = (0., 0.)
    temperature_error_bound_k: float = 0.
    minimum_energy_jacobian_eigenvalue_j_k: float = 9.
    iterations: int = 0
    target_interval_admissible: bool = True
    elapsed_s: float = 0.


@dataclass
class FakeTarget:
    cell_energy_j: tuple
    absolute_error_j: tuple = (0., 0.)


class FakeHost:
    fixed_amounts_mol = FIXED

    def evaluate(self, state, at):
        del at
        rates = Rates(np.zeros((3, 1)), np.zeros(3), np.zeros((2, 1)), np.zeros(2),
                      {'mechanical_constraint': np.zeros(2)})
        inverse = FakeInverse(FakeDecoded(plate_evaluation=FakePlate()),
                              FakeTarget(tuple(state.internal_energy_j)))
        return SimpleNamespace(rates=rates, inverse=inverse)


def initial():
    return ConservedState(FIXED, np.array([40., 40.]), energy_model_identity=('fake_explicit_energy',))


def step(start, end, face=None):
    return StepLedger(start, end, np.zeros((3, 1)), np.zeros(3) if face is None else np.array(face),
        np.zeros((2, 1)), np.zeros(2), {'mechanical_constraint': np.zeros(2)},
        {'mechanical_constraint': (Fraction(), Fraction())})


def fake_result(state, times, *, status='completed', evaluations=1):
    return IntegrationResult(status, None if status == 'completed' else 'fake_wall_time_limit',
        tuple(times), tuple(state for _ in times), tuple(step(a, b) for a, b in zip(times, times[1:])),
        evaluations, 0, 0.)


def fake_references():
    times = driver.read_references()['times_s']
    return dict(times_s=times, fine_temperatures_k=[[304., 304.]]*101,
                reference_temperatures_k=[[304., 304.]]*101, fine_stress_pa=[[0., 0.]]*101)


class DriverTests(unittest.TestCase):
    def test_original_times_are_reused_without_reconstruction(self):
        references = driver.read_references()
        self.assertEqual(driver.sha256(driver.OLD/'fine.json'), driver.FINE_SHA256)
        self.assertEqual(len(references['times_s']), 101)
        self.assertEqual(sum(t != k/10. for k, t in enumerate(references['times_s'])), 35)
        with (driver.OLD/'reference.json').open() as stream:
            self.assertEqual(list(references['times_s']), json.load(stream)['times_s'])

    def test_fake_two_paths_obey_exact_policies_and_cannot_scientifically_pass(self):
        calls = []
        references = fake_references()
        state = initial()
        def fake_integrate(candidate, operator, **kwargs):
            calls.append((candidate, kwargs))
            operator(candidate, 0.)
            return fake_result(candidate, references['times_s'])
        with tempfile.TemporaryDirectory() as directory:
            report = driver.run_experiment(FakeHost(), state, fake_integrate, IntegrationPolicy,
                references, Path(directory), real_native_integration=REAL_NATIVE_INTEGRATION)
            self.assertFalse(report['passed'])
            self.assertFalse(report['real_native_integration'])
            self.assertTrue(report['time_convergence_gate'])
            for name in ('coarse', 'fine'):
                saved = json.loads((Path(directory)/(name+'.json')).read_text())
                self.assertFalse(saved['real_native_integration'])
                self.assertEqual(saved['result']['states'][0]['amounts_binary64_bytes_hex'], FIXED.tobytes().hex())
                self.assertEqual(len(saved['result']['states']), 101)
                self.assertEqual(len(saved['result']['steps']), 100)
                audit = json.loads((Path(directory)/(name+'-audit.json')).read_text())
                self.assertEqual(audit['native_rhs_summary']['calls_started'], 1)
                self.assertEqual(audit['accepted_state_decode_summary']['calls_started'], 101)
                self.assertEqual(len(audit['comparison_points']), 101)
        self.assertEqual(len(calls), 2)
        for index, (candidate, kwargs) in enumerate(calls):
            self.assertIs(candidate, state)
            self.assertEqual(kwargs['breakpoints_s'], references['times_s'][1:-1])
            self.assertEqual((kwargs['start_s'], kwargs['end_s']), (0., 10.))
            self.assertEqual(driver.jsonable(kwargs['policy']), driver.jsonable(IntegrationPolicy(
                **driver.policy_parameters((.005, .0025)[index]))))

    def test_returned_prefix_saved_before_any_decode_failure(self):
        references = fake_references()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            def fake_integrate(state, operator, **kwargs):
                return fake_result(state, references['times_s'][:3], status='resource_limit', evaluations=0)
            with patch.object(driver, 'analyze_run', side_effect=ValueError('fake_decode_failure')):
                with self.assertRaisesRegex(ValueError, 'fake_decode_failure'):
                    driver.run_experiment(FakeHost(), initial(), fake_integrate, IntegrationPolicy,
                        references, path, real_native_integration=False)
            saved = json.loads((path/'coarse.json').read_text())
            self.assertEqual(saved['result']['status'], 'resource_limit')
            self.assertEqual(len(saved['result']['states']), 3)
            self.assertEqual(len(saved['result']['steps']), 2)
            self.assertFalse((path/'fine.json').exists())

    def test_partial_result_keeps_failure_and_does_not_start_second_path(self):
        references = fake_references()
        calls = []
        def fake_integrate(state, operator, **kwargs):
            calls.append(kwargs)
            operator(state, 0.)
            return fake_result(state, references['times_s'][:3], status='resource_limit')
        with tempfile.TemporaryDirectory() as directory:
            report = driver.run_experiment(FakeHost(), initial(), fake_integrate, IntegrationPolicy,
                references, Path(directory), real_native_integration=False)
        self.assertEqual(len(calls), 1)
        self.assertFalse(report['passed'])
        self.assertEqual(report['run_status'], {'coarse': 'resource_limit', 'fine': 'not_started'})

    def test_fraction_accumulation_checks_intermediate_failure_not_only_final(self):
        states = [initial(), ConservedState(FIXED, [1e16+40., 40.], energy_model_identity=('fake_explicit_energy',)),
                  ConservedState(FIXED, [1e16+40., 40.], energy_model_identity=('fake_explicit_energy',)),
                  ConservedState(FIXED, [41., 40.], energy_model_identity=('fake_explicit_energy',))]
        steps = (step(0., 1., [0., -1e16, -1e16]), step(1., 2., [0., -1., -1.]),
                 step(2., 3., [0., 1e16, 1e16]))
        result = IntegrationResult('resource_limit', 'fake', (0., 1., 2., 3.), tuple(states), steps, 0, 0, 0.)
        audit = driver.audit_prefix(result, FIXED)
        self.assertEqual(audit['all_prefixes'][-1]['cumulative_boundary_heat_j'], Fraction(1))
        self.assertEqual(audit['all_prefixes'][-1]['global_heat_residual_j'], Fraction())
        self.assertEqual(audit['maximum_global_heat_residual_j'], Fraction(1))
        self.assertFalse(audit['global_heat_gate'])
        self.assertFalse(audit['local_energy_gate'])

    def test_missing_comparison_time_is_not_interpolated(self):
        references = fake_references()
        times = list(references['times_s'])
        times[7] = 7/10.
        self.assertNotEqual(times[7], references['times_s'][7])
        result = fake_result(initial(), times)
        summary = driver.EvaluationSummary(FakeHost())
        summary.evaluate(initial(), 0.)
        audit = driver.analyze_run(FakeHost(), result, summary.data, references)
        self.assertFalse(audit['gates']['complete'])
        self.assertEqual(len(audit['comparison_points']), 100)

    def test_inventory_and_ledger_identity_failures_are_visible(self):
        state = initial()
        result = fake_result(state, (0., .1))
        changed = ConservedState([[2.], [3.000001]], state.internal_energy_j, energy_model_identity=state.energy_model_identity)
        audit = driver.audit_prefix(replace(result, states=(state, changed)), FIXED)
        self.assertFalse(audit['inventory_stretch_and_work_contract'])
        with self.assertRaisesRegex(ValueError, 'endpoints_mismatch'):
            driver.audit_prefix(replace(result, steps=(step(0., .2),)), FIXED)

    def test_trial_witness_is_explicit_and_not_an_accepted_point(self):
        references = fake_references()
        def fake_integrate(state, operator, **kwargs):
            for _ in range(512):
                operator(state, .0123)
            return fake_result(state, (0.,), status='resource_limit', evaluations=512)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            driver.save_run(FakeHost(), initial(), fake_integrate, IntegrationPolicy(**driver.policy_parameters(.005)),
                            references['times_s'], path, 'coarse', real_native_integration=False)
            witness = json.loads((path/'coarse-rhs-trials.jsonl').read_text())
            saved = json.loads((path/'coarse.json').read_text())
        self.assertEqual(witness['kind'], 'RHS_trial_not_accepted_state')
        self.assertEqual(witness['accepted_prefix_status'], 'unknown_until_integrate_returns')
        self.assertEqual(saved['result']['times_s'], [0.])
        self.assertFalse(witness['real_native_integration'])

    def test_decode_tolerance_or_identity_violation_cannot_pass(self):
        class BadHost(FakeHost):
            def evaluate(self, state, at):
                result = super().evaluate(state, at)
                result.inverse = replace(result.inverse, temperature_error_bound_k=1e-8)
                return result
        summary = driver.EvaluationSummary(BadHost())
        summary.evaluate(initial(), 0.)
        self.assertFalse(summary.data['all_decodes_certified'])

    def test_actual_point_independent_derivative_includes_local_work(self):
        # One algebraic point; no candidate or reference time solver is called.
        temperatures = np.array([303., 301.])
        heat = np.array([-2., 0.])
        ce = 1e5-2.*1e9*1e-4**2*temperatures
        matrix = np.diag(ce)+np.outer(2.*1e9*1e-4**2*temperatures, [.5, .5])
        td = np.linalg.solve(matrix, heat/1e-4)
        stress = 1e9*1e-4*(302.-temperatures)
        power = 2.*1e-4*stress*(1e-4*float(np.mean(td)))
        plate = FakePlate(tuple(temperatures), tuple(td), tuple(power), tuple(FakePoint(x) for x in stress))
        fields = driver.independent_stage(plate)
        self.assertLess(max(map(abs, fields['energy_equation_residual_w'])), 1e-12)
        self.assertGreater(max(map(abs, fields['cell_power_w'])), 1e-5)

    def test_native_local_power_mismatch_visible_even_when_total_power_is_zero(self):
        class WrongLocalPowerHost(FakeHost):
            def evaluate(self, state, at):
                result = super().evaluate(state, at)
                wrong = np.array([5., -5.])
                result.rates = Rates(np.zeros((3, 1)), np.zeros(3), np.zeros((2, 1)), wrong,
                                     {'mechanical_constraint': wrong})
                return result
        summary = driver.EvaluationSummary(WrongLocalPowerHost())
        summary.evaluate(initial(), 0.)
        self.assertEqual(summary.data['maximum_actual_total_constraint_power_abs_w'], 0.)
        self.assertEqual(summary.data['maximum_independent_power_difference_w'], 0.)
        self.assertEqual(summary.data['maximum_native_power_reconstruction_difference_w'], 5.)

    def test_installed_host_single_point_serializes_actual_inverse_and_rates(self):
        # One initial algebraic RHS point, never a call to the time integrator.
        from sludge_sandbox.cooling_thermoelastic_plate import CoolingThermoelasticPlate
        from sludge_sandbox.geometry import ReferenceSlab
        from sludge_sandbox.thermoelastic_energy_host import ThermoelasticEnergyHost
        from sludge_sandbox.thermoelastic_energy_storage import ThermoelasticEnergyStorage, EnergyInversePolicy
        plate = CoolingThermoelasticPlate(reference=ReferenceSlab(.02, .01, 2), **driver.PARAMETERS)
        host = ThermoelasticEnergyHost(storage=ThermoelasticEnergyStorage(plate), fixed_amounts_mol=FIXED,
                                      inverse_policy=EnergyInversePolicy(**driver.INVERSE_POLICY))
        state, forward = host.state_from_temperatures((304., 304.))
        summary = driver.EvaluationSummary(host)
        evaluated = summary.evaluate(state, 0.)
        self.assertTrue(summary.data['all_decodes_certified'])
        self.assertTrue(summary.data['inventory_and_rate_contract'])
        self.assertLess(summary.data['maximum_independent_stage_energy_residual_w'], 1e-11)
        self.assertLessEqual(max(abs(t-304.) for t in evaluated.inverse.state.temperatures_k),
                             driver.INVERSE_POLICY['temperature_tolerance_k'])
        self.assertLessEqual(abs(float(evaluated.rates.face_energy_w[-1])-8.),
                             2.*driver.INVERSE_POLICY['temperature_tolerance_k'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'single-point.json'
            driver.write_new(path, dict(real_native_integration=False, state=driver.state_record(state),
                forward=forward, inverse=evaluated.inverse, rates=evaluated.rates, summary=summary.data))
            self.assertFalse(json.loads(path.read_text())['real_native_integration'])

    def test_write_new_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'evidence.json'
            driver.write_new(path, {'real_native_integration': False})
            with self.assertRaises(FileExistsError):
                driver.write_new(path, {})


class FreezeTests(unittest.TestCase):
    def make_freeze(self, directory):
        directory = Path(directory)
        executable = directory/'bin/python'
        executable.parent.mkdir()
        executable.write_text('fake_binary_for_hash_unit_test_only')
        installed = directory/'lib/python3.12/site-packages/sludge_sandbox'
        installed.mkdir(parents=True)
        modules = {}
        for name in driver.MODULES:
            source = driver.REPOSITORY/'src/sludge_sandbox'/f'{name}.py'
            target = installed/f'{name}.py'
            target.write_bytes(source.read_bytes())
            modules[name] = dict(source=str(source), installed=str(target), sha256=driver.sha256(source))
        paths = (ROOT/'run_validation.py', ROOT/'supervise.py', ROOT/'PREREGISTRATION.md',
                 driver.OLD/'fine.json', driver.OLD/'reference.json')
        freeze = dict(schema='cooling_energy_host_freeze_v1', modules=modules,
            files={str(path.resolve()): driver.sha256(path) for path in paths},
            python_prefix=str(directory), python_executable=str(executable),
            python_version='fake_version', python_binary_sha256=driver.sha256(executable), numpy_version='fake_numpy')
        path = directory/'freeze.json'
        path.write_text(json.dumps(freeze))
        return path, freeze

    def test_freeze_detects_installed_module_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path, freeze = self.make_freeze(directory)
            accepted = driver.read_freeze(path)
            before = driver.verify_freeze(accepted, path)
            self.assertEqual(before[str(path.resolve())], driver.sha256(path))
            Path(freeze['modules']['integration']['installed']).write_text('changed_fake_copy')
            with self.assertRaisesRegex(ValueError, 'frozen_installed_module_changed'):
                driver.verify_freeze(accepted, path)

    def test_missing_protocol_or_module_binding_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, freeze = self.make_freeze(directory)
            removed = freeze['files'].pop(str((ROOT/'PREREGISTRATION.md').resolve()))
            path.write_text(json.dumps(freeze))
            with self.assertRaisesRegex(ValueError, 'required_driver_protocol_reference_hashes_missing'):
                driver.read_freeze(path)
            freeze['files'][str((ROOT/'PREREGISTRATION.md').resolve())] = removed
            freeze['modules'].pop('integration')
            path.write_text(json.dumps(freeze))
            with self.assertRaisesRegex(ValueError, 'required_native_module_bindings_missing'):
                driver.read_freeze(path)

    def test_read_freeze_refuses_source_in_place_of_installed_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            path, freeze = self.make_freeze(directory)
            freeze['modules']['integration']['installed'] = freeze['modules']['integration']['source']
            path.write_text(json.dumps(freeze))
            with self.assertRaisesRegex(ValueError, 'module_not_bound_to_installed_environment'):
                driver.read_freeze(path)

    def test_import_runtime_refuses_actual_source_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            _, freeze = self.make_freeze(directory)
            freeze.update(python_executable=str(Path(sys.executable).absolute()),
                          python_prefix=sys.prefix, python_version=sys.version)
            def fake_import(name):
                local = name.rsplit('.', 1)[-1]
                return SimpleNamespace(__file__=freeze['modules'][local]['source'])
            with patch.object(driver.importlib, 'import_module', side_effect=fake_import):
                with self.assertRaisesRegex(ValueError, 'import_did_not_use_frozen_installed_module'):
                    driver.import_runtime(freeze)


class SupervisorTests(unittest.TestCase):
    def fake_driver(self, verify=None):
        return SimpleNamespace(__file__=str(ROOT/'run_validation.py'), write_new=driver.write_new,
            read_freeze=lambda path: {'python_executable': '/fake/installed/python'},
            verify_freeze=(lambda *args: {'input': 'same'}) if verify is None else verify)

    def test_one_deadline_is_reduced_by_preflight_and_child_is_reaped_on_timeout(self):
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            raise subprocess.TimeoutExpired(command, kwargs['timeout'])
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(supervisor, 'load_driver', return_value=self.fake_driver()):
                report = supervisor.supervise('/fake/freeze', Path(directory)/'new', runner=runner,
                                              clock=iter((0., 2., 130.)).__next__)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]['timeout'], 128.)
        self.assertEqual(calls[0][0][1], '-I')
        self.assertTrue(report['child_reaped'])
        self.assertFalse(report['passed'])
        self.assertEqual(report['unreturned_accepted_prefix'], 'unknown')
        self.assertEqual(report['terminal_status'], 'external_deadline')

    def test_missing_result_or_zero_return_code_cannot_claim_success(self):
        def runner(command, **kwargs):
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(supervisor, 'load_driver', return_value=self.fake_driver()):
                report = supervisor.supervise('/fake/freeze', Path(directory)/'new', runner=runner)
        self.assertFalse(report['passed'])
        self.assertEqual(report['terminal_status'], 'worker_evidence_unreadable')

    def test_failed_post_hash_still_records_terminal_failure(self):
        checks = []
        def verify(*args):
            checks.append(args)
            if len(checks) == 2:
                raise OSError('fake_disappeared_input')
            return {'input': 'before'}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'new'
            with patch.object(supervisor, 'load_driver', return_value=self.fake_driver(verify)):
                report = supervisor.supervise('/fake/freeze', output,
                    runner=lambda *a, **kw: SimpleNamespace(returncode=1))
            saved = json.loads((output/'EXECUTION.json').read_text())
        self.assertFalse(report['passed'])
        self.assertFalse(saved['inputs_unchanged'])
        self.assertIn('fake_disappeared_input', saved['post_verification_error'])

    def test_launch_or_reaping_failure_is_not_success(self):
        for error in (OSError('fake_launch_failure'), RuntimeError('fake_reaping_failure')):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as directory:
                def runner(*args, **kwargs):
                    raise error
                with patch.object(supervisor, 'load_driver', return_value=self.fake_driver()):
                    report = supervisor.supervise('/fake/freeze', Path(directory)/'new', runner=runner)
                self.assertFalse(report['passed'])
                self.assertIsNone(report['child_reaped'])

    def test_fake_child_cannot_claim_real_native_success(self):
        def runner(command, **kwargs):
            output = Path(command[-1])
            output.mkdir()
            for name in ('INPUTS', 'coarse', 'fine', 'coarse-audit', 'fine-audit'):
                driver.write_new(output/(name+'.json'), {'real_native_integration': False})
            driver.write_new(output/'RESULT.json', {'passed': True, 'inputs_unchanged': True,
                                                   'real_native_integration': False})
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(supervisor, 'load_driver', return_value=self.fake_driver()):
                report = supervisor.supervise('/fake/freeze', Path(directory)/'new', runner=runner)
        self.assertFalse(report['passed'])
        self.assertFalse(report['real_native_integration'])


if __name__ == '__main__':
    print('test_scope: real_native_integration=false; pure arithmetic, single actual point and fake integrate/process only', flush=True)
    unittest.main()
