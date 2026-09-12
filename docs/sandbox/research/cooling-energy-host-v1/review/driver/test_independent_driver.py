"""Independent fake/unit probes only; no native integrate invocation."""

from dataclasses import replace
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from sludge_sandbox.integration import ConservedState, IntegrationResult, StepLedger

OWN = Path(__file__).resolve().parent
ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research/cooling-energy-host-v1')


def load(name: str):
    spec = importlib.util.spec_from_file_location('independent_' + name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


driver, supervisor = load('run_validation'), load('supervise')
FIXED = np.array([[2.0], [3.0]])


def state(energies: tuple[float, float]) -> ConservedState:
    return ConservedState(FIXED, np.array(energies), energy_model_identity=('independent_fake',))


def ledger(start: float, end: float) -> StepLedger:
    return StepLedger(start, end, np.zeros((3, 1)), np.zeros(3), np.zeros((2, 1)), np.zeros(2),
        {'mechanical_constraint': np.zeros(2)},
        {'mechanical_constraint': (Fraction(), Fraction())})


def freeze_fixture() -> dict:
    environment = json.loads(Path('/private/tmp/brick-cooling-energy-v1/INSTALLED_FREEZE.json').read_text())
    source, installed = Path(environment['source_root']), Path(environment['installed_root'])
    paths = [ROOT / name for name in ('run_validation.py', 'supervise.py', 'PREREGISTRATION.md')]
    paths.extend(driver.OLD / name for name in ('fine.json', 'reference.json'))
    return dict(schema='cooling_energy_host_freeze_v1',
        files={str(path.resolve()): driver.sha256(path) for path in paths},
        modules={name: dict(source=str(source / (name + '.py')), installed=str(installed / (name + '.py')),
                           sha256=environment['files'][name + '.py']['sha256']) for name in driver.MODULES},
        python_prefix=sys.prefix, python_executable=sys.executable, python_version=sys.version,
        python_binary_sha256=environment['python_binary_sha256'], numpy_version=np.__version__)


class IndependentDriverTests(unittest.TestCase):
    def test_opposite_local_leaks_at_intermediate_prefix_fail_absolute_gate(self) -> None:
        initial = state((40.0, 40.0))
        middle = state((40.0 + 1e-6, 40.0 - 1e-6))
        result = IntegrationResult('resource_limit', 'independent_fake', (0.0, 0.05, 0.1),
            (initial, middle, initial), (ledger(0.0, 0.05), ledger(0.05, 0.1)), 0, 0, 0.0)
        audited = driver.audit_prefix(result, FIXED)
        self.assertFalse(audited['local_energy_gate'])
        self.assertTrue(audited['global_heat_gate'])
        self.assertEqual(audited['maximum_global_heat_residual_j'], Fraction())
        self.assertGreater(audited['maximum_local_energy_residual_j'], Fraction(80) * Fraction(1e-8))
        self.assertEqual(audited['all_prefixes'][-1]['local_energy_residual_j'], [Fraction(), Fraction()])

    def test_state_time_and_ledger_cardinality_cannot_be_silently_truncated(self) -> None:
        initial = state((40.0, 40.0))
        result = IntegrationResult('resource_limit', 'independent_fake', (0.0, 0.1),
            (initial, initial), (ledger(0.0, 0.1),), 0, 0, 0.0)
        for changed in (replace(result, states=(initial,)), replace(result, steps=())):
            with self.assertRaisesRegex(ValueError, 'count_mismatch'):
                driver.audit_prefix(changed, FIXED)

    def test_actual_installed_bindings_pass_read_hash_and_import_checks(self) -> None:
        with tempfile.TemporaryDirectory(dir=OWN) as directory:
            path = Path(directory) / 'fake_freeze.json'
            path.write_text(json.dumps(freeze_fixture()))
            frozen = driver.read_freeze(path)
            hashes = driver.verify_freeze(frozen, path)
            modules, numpy = driver.import_runtime(frozen)
            self.assertEqual(set(modules), set(driver.MODULES))
            self.assertIs(numpy, np)
            self.assertIn(str(path.resolve()), hashes)
            for name, module in modules.items():
                self.assertEqual(Path(module.__file__).resolve(), Path(frozen['modules'][name]['installed']).resolve())

    def test_changed_additional_frozen_evidence_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(dir=OWN) as directory:
            path, evidence = Path(directory) / 'fake_freeze.json', Path(directory) / 'fake_evidence.txt'
            evidence.write_text('frozen independent fake input')
            frozen = freeze_fixture()
            frozen['files'][str(evidence)] = driver.sha256(evidence)
            path.write_text(json.dumps(frozen))
            registered = driver.read_freeze(path)
            driver.verify_freeze(registered, path)
            evidence.write_text('changed independent fake input')
            with self.assertRaisesRegex(ValueError, 'frozen_input_changed'):
                driver.verify_freeze(registered, path)

    def test_installed_import_identity_rejects_source_fallback(self) -> None:
        frozen = freeze_fixture()
        modules = {name: SimpleNamespace(__file__=binding['installed']) for name, binding in frozen['modules'].items()}
        modules['thermoelastic_energy_storage'].__file__ = frozen['modules']['thermoelastic_energy_storage']['source']
        def import_fake(name: str):
            return modules[name.removeprefix('sludge_sandbox.')]
        with patch.object(driver.importlib, 'import_module', side_effect=import_fake):
            with self.assertRaisesRegex(ValueError, 'import_did_not_use_frozen_installed_module'):
                driver.import_runtime(frozen)

    def test_supervisor_accounts_for_time_spent_after_worker_returns(self) -> None:
        fake_driver = SimpleNamespace(__file__=str(ROOT / 'run_validation.py'), write_new=driver.write_new,
            read_freeze=lambda unused: {'python_executable': '/fake/python'},
            verify_freeze=lambda *unused: {'frozen_fake': 'unchanged'})
        calls = []
        def runner(command: list[str], **kwargs):
            calls.append(kwargs['timeout'])
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory(dir=OWN) as directory:
            with patch.object(supervisor, 'load_driver', return_value=fake_driver):
                report = supervisor.supervise('/fake/freeze', Path(directory) / 'output', runner=runner,
                    clock=iter((0.0, 1.0, 130.001)).__next__)
        self.assertEqual(calls, [129.0])
        self.assertFalse(report['passed'])
        self.assertFalse(report['real_native_integration'])
        self.assertTrue(report['end_to_end_deadline_exceeded'])


if __name__ == '__main__':
    print('independent_scope: real_native_integration=false; unit/fake only', flush=True)
    unittest.main()
