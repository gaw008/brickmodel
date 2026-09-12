"""Argument routing only; no source admission or physical construction here."""
import json
import sys
from types import SimpleNamespace

import pytest

from sludge_sandbox.cli import main


@pytest.mark.parametrize('inverse', [False, True])
def test_wet_cli_uses_shared_model_and_reports_approximation(monkeypatch, capsys, inverse):
    calls = []
    result = SimpleNamespace(to_record=lambda: {'material_qualified': False, 'model_error': None})

    class Model:
        def __init__(self, root, water):
            calls.append(('construct', str(root), str(water)))

        def evaluate(self, temperature, moisture):
            calls.append(('evaluate', temperature, moisture))
            return result

        def inverse_enthalpy(self, target, *, dry_mass_kg, moisture):
            calls.append(('inverse', target, dry_mass_kg, moisture))
            return result

        def definition(self):
            return {'qualification': 'conditional_exploration_not_validated_wet_material'}

    monkeypatch.setitem(sys.modules, 'sludge_sandbox.arlabosse_wet_thermo',
                        SimpleNamespace(ArlabosseWetThermodynamics=Model))
    args = ['arlabosse-wet', '--assets-root', '/sources', '--water-data', '/water',
            '--moisture', '.3', '--trace']
    args += ['--enthalpy-j', '-10', '--dry-mass-kg', '.1'] if inverse else ['--temperature-k', '350']
    assert main(args) == 0
    actual = json.loads(capsys.readouterr().out)
    assert actual['result'] == result.to_record()
    assert actual['trace']['qualification'].startswith('conditional_exploration')
    assert calls == [('construct', '/sources', '/water'),
                     ('inverse', -10., .1, .3) if inverse else ('evaluate', 350., .3)]


@pytest.mark.parametrize('mode,reason', [
    (['--enthalpy-j', '0'], 'dry_mass_required_for_enthalpy_inverse'),
    (['--temperature-k', '350', '--dry-mass-kg', '1'], 'dry_mass_only_for_enthalpy_inverse'),
])
def test_wet_cli_rejects_ambiguous_energy_basis_before_model(capsys, mode, reason):
    assert main(['arlabosse-wet', '--assets-root', '/missing', '--water-data', '/missing',
                 '--moisture', '.3', *mode]) == 1
    assert json.loads(capsys.readouterr().out)['reason'] == reason
