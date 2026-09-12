"""Bounded independent API/control probes; no native backend is imported."""
from decimal import Decimal, Inexact, ROUND_UP, localcontext
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from sludge_sandbox.calcite_thermochemistry import calculate_calcite_thermochemistry

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
DATA = ROOT/'data/sandbox/research/calcite-thermochemistry-v1'


def test_nonregular_source_file_fails_without_blocking(tmp_path):
    source = tmp_path/'source'
    source.mkdir()
    os.mkfifo(source/'facts.json')
    code = ('from sludge_sandbox.calcite_thermochemistry import calculate_calcite_thermochemistry;'
            'import sys; calculate_calcite_thermochemistry(sys.argv[1], temperature_k="800")')
    environment = dict(os.environ, PYTHONPATH=str(ROOT/'src'), PYTHONDONTWRITEBYTECODE='1')
    blocked = False
    try:
        result = subprocess.run([sys.executable, '-B', '-c', code, str(source)],
                                capture_output=True, timeout=1., env=environment)
    except subprocess.TimeoutExpired:
        blocked = True
    (tmp_path/'RESULT.json').write_text(json.dumps({'blocked_past_one_second': blocked})+'\n')
    assert not blocked, 'FIFO source blocks plain open before bounded byte read'
    assert result.returncode != 0


def test_extreme_accepted_extent_keeps_exact_mass_balance():
    result = calculate_calcite_thermochemistry(DATA, temperature_k='298.15',
        extent_mol='12345678901234567890123456789012345678901234567890E1000')
    mass = {name: Fraction(Decimal(value)) for name, value in result['reaction']['mass_changes_kg'].items()}
    assert sum(mass.values()) == 0
    assert mass['carbon_dioxide'] == Fraction(Decimal(result['extent_mol']))*Fraction('0.044010')


def test_outer_traps_and_rounding_do_not_change_result():
    expected = calculate_calcite_thermochemistry(DATA, temperature_k='800', extent_mol='0.3333333333333333333333333333333333333')
    with localcontext() as context:
        context.prec = 3
        context.rounding = ROUND_UP
        context.traps[Inexact] = True
        actual = calculate_calcite_thermochemistry(DATA, temperature_k='800', extent_mol='0.3333333333333333333333333333333333333')
    assert actual == expected


def test_reaction_enthalpy_derivative_matches_delta_cp():
    with localcontext() as context:
        context.prec = 60
        epsilon = Decimal('0.00001')
        lower = calculate_calcite_thermochemistry(DATA, temperature_k=str(Decimal(800)-epsilon))
        upper = calculate_calcite_thermochemistry(DATA, temperature_k=str(Decimal(800)+epsilon))
        center = calculate_calcite_thermochemistry(DATA, temperature_k='800')
        difference = (Decimal(upper['reaction']['enthalpy_j_mol_extent'])-
                      Decimal(lower['reaction']['enthalpy_j_mol_extent']))/(2*epsilon)
        assert abs(difference-Decimal(center['reaction']['heat_capacity_change_j_mol_extent_k'])) < Decimal('1e-12')


def test_reaction_mass_trace_names_existing_species_quantities(tmp_path):
    result = calculate_calcite_thermochemistry(DATA, temperature_k='800')
    dependency = result['trace']['reaction.mass_changes_kg']['dependencies']
    actual_mass_paths = {f'species.{name}.molar_mass_g_mol' for name in result['species']}
    dangling = [path for path in dependency if path.startswith('species.') and path not in actual_mass_paths]
    (tmp_path/'TRACE.json').write_text(json.dumps({'declared_dependencies': dependency,
        'actual_result_mass_paths': sorted(actual_mass_paths), 'dangling_species_paths': dangling}, indent=2)+'\n')
    assert not dangling, 'mass trace contains no concrete per-species molar-mass path'


def test_cli_reports_invalid_input_and_uses_same_success_value(capsys):
    from sludge_sandbox.cli import main
    args = ['calcite-thermochemistry', '--source-data', str(DATA), '--temperature-k']
    assert main([*args, 'NaN']) == 1
    failure = json.loads(capsys.readouterr().out)
    assert failure['status'] == 'failed' and failure['error_type'] == 'MineralThermochemistryError'
    assert main([*args, '800', '--extent-mol', '0']) == 0
    actual = json.loads(capsys.readouterr().out)
    assert actual == calculate_calcite_thermochemistry(DATA, temperature_k='800', extent_mol='0')
    assert not any(name == 'CoolProp' or name.startswith('CoolProp.') for name in sys.modules)
