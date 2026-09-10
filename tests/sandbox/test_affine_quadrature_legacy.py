"""Pre-extraction full terminal state/ledger and failure regression."""
from dataclasses import replace
from fractions import Fraction as F
import json
from pathlib import Path
import numpy as np

from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_terminal_panel import build_exact_affine_panel
from sludge_sandbox.exact_root_order import _data
from sludge_sandbox.integration import ConservedState, Rates, IntegrationError
from test_exact_terminal_panel import data, policy


GOLDEN = Path(__file__).parent/'fixtures/affine-quadrature-legacy-v1.json'


def legacy_records():
    records = {}

    def capture(name, s, a, b, **changes):
        kwargs = dict(start=T(F()), midpoint=T(F(1, 4)), end=T(F(1, 2)),
                      policy=policy(), liquid_index=0, selected_cell=0,
                      wet_cells=(0, 1), source_binding=('legacy-quadrature-fixture',))
        kwargs.update(changes)
        try:
            records[name] = {'result': _data(build_exact_affine_panel(s, a, b, **kwargs))}
        except IntegrationError as exc:
            records[name] = {'error_type': type(exc).__name__, 'error': str(exc)}

    s, a, b = data()
    capture('all_fields', s, a, b)
    origin = F(2**80)+F(1, 3)
    capture('large_origin', s, a, b, start=T(origin), midpoint=T(origin+F(1, 4)), end=T(origin+F(1, 2)))
    capture('nonhalf_sample', s, a, b, midpoint=T(F(1, 3)), end=T(F(2, 3)))
    capture('schema_failure', s, a, replace(b, cell_power_components_w=None))
    capture('time_failure', s, a, b, midpoint=T(F(1)))
    capture('mechanical_roundoff_budget', s, a, b,
            policy=replace(policy(), stretch_absolute_tolerance=1e-30))
    capture('mechanical_interior_negative', replace(s, mechanical_stretches=[.1, 2., 3.]),
            replace(a, mechanical_rates_per_s=[-2., 0., 0.]),
            replace(b, mechanical_rates_per_s=[0., 0., 0.]))
    capture('gas_interior_negative', replace(s, amounts_mol=[[10., .1], [8., 3.]]),
            replace(a, reaction_species_mol_s=[[-1., -2.], [-.5, .5]]),
            replace(b, reaction_species_mol_s=[[-2., 0.], [-1., 1.]]))
    plain = ConservedState([[1.], [1.]], [0., 0.])
    rate = Rates(np.zeros((3, 1)), np.zeros(3), [[-2.], [-1.]], np.zeros(2))
    capture('selected_endpoint_zero', plain, rate, rate)
    rate2 = replace(rate, reaction_species_mol_s=[[-2.], [-2.]])
    capture('competing_endpoint_zero', plain, rate2, rate2)
    small = replace(rate, reaction_species_mol_s=[[.1], [.1]])
    capture('state_roundoff_budget', plain, small, small,
            policy=replace(policy(), amount_absolute_tolerance_mol=1e-30))
    tiny = replace(rate, reaction_species_mol_s=[[1e-320], [1e-320]])
    capture('integral_underflow', plain, tiny, tiny, midpoint=T(F(1, 10**50)), end=T(F(2, 10**50)))
    large = replace(rate, face_energy_w=[1e308, 1e308, 1e308])
    capture('integral_overflow', plain, large, large, midpoint=T(F(1)), end=T(F(2)))
    return records


def test_old_terminal_outputs_and_failures_are_unchanged():
    expected = json.loads(GOLDEN.read_text())
    assert expected['baseline_commit'] == '1fd9e87'
    assert legacy_records() == expected['records']
