"""Frozen pre-extraction numerical records, including failed legacy budgets."""
from dataclasses import replace
from fractions import Fraction as F
import json
from pathlib import Path

import numpy as np

from sludge_sandbox.depletion_roundoff import DepletionRoundoffError
from sludge_sandbox.exact_affine_depletion import ExactAffineSamples, locate_exact_affine
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_root_order import ExactRootOrderError, _data, order_exact_affine_roots
from test_exact_affine_depletion import fixture, policy
from test_exact_root_order import inputs


GOLDEN = Path(__file__).parent / 'fixtures' / 'rational-polynomial-legacy-v1.json'


def legacy_records():
    records = {}

    def capture(name, call):
        try:
            records[name] = {'result': _data(call())}
        except (DepletionRoundoffError, ExactRootOrderError) as exc:
            records[name] = {
                'error_type': type(exc).__name__,
                'error': str(exc),
                'diagnostic': _data(getattr(exc, 'diagnostic', None)),
            }

    saved = fixture()
    p = policy()
    capture('saved_locate', lambda: locate_exact_affine(saved, time_absolute_s=1e-8, policy=p))
    capture('locate_budget_one', lambda: locate_exact_affine(
        saved, time_absolute_s=1e-8, policy=p, maximum_refinements=1))
    capture('locate_no_evaporation', lambda: locate_exact_affine(
        replace(saved, evaporation_start_mol_s=0., evaporation_mid_mol_s=0.),
        time_absolute_s=1e-8, policy=p, maximum_refinements=16))
    for name, n in (('dyadic_zero', .5), ('upper_zero', 1.)):
        s = ExactAffineSamples(T(F()), T(F(1, 4)), T(F(1)), n,
                              (0., 0., -1.), (0., 0., -1.), 1., 1., ('legacy-analytic',))
        capture(name, lambda s=s: locate_exact_affine(s, time_absolute_s=1e-8, policy=p))
    capture('locate_nonmonotone_rejected', lambda: replace(
        saved, liquid_rates_start_mol_s=(0., 0., 1.)))

    cases = (
        ('accelerated', {}),
        ('close_linear', dict(amounts=(.01, .01+1e-9), acceleration=(0., 0.))),
        ('excluded_vertex', dict(amounts=(.01, 1.), initial=(-1., -1.), acceleration=(0., 100.))),
        ('nonmonotone_candidate', dict(amounts=(.01, .001), initial=(-1., -1.), acceleration=(0., 100.))),
        ('three_equal', dict(amounts=(.01,)*3, initial=(-1.,)*3, acceleration=(0.,)*3)),
        ('later_equal', dict(amounts=(.005, .01, .01), initial=(-1.,)*3, acceleration=(0.,)*3)),
        ('none', dict(amounts=(1., 1.), acceleration=(0., 0.))),
        ('large_origin', dict(origin=F(2**80)+F(1, 3))),
    )
    for name, options in cases:
        args, kwargs = inputs(**options)
        capture(name, lambda args=args, kwargs=kwargs: order_exact_affine_roots(*args, **kwargs))
    args, kwargs = inputs()
    capture('order_budget_one', lambda: order_exact_affine_roots(
        *args, **dict(kwargs, maximum_refinements=1)))
    capture('order_no_evaporation', lambda: order_exact_affine_roots(
        *args, **dict(kwargs, evaporation_start_mol_s=(0., 0.),
                     evaporation_mid_mol_s=(0., 0.), maximum_refinements=16)))
    args, kwargs = inputs(amounts=(.5, .75), initial=(-1., -1.), acceleration=(0., -2.))
    kwargs.update(midpoint=T(F(1, 4)), upper=T(F(1)))
    second = replace(args[2], reaction_species_mol_s=np.array([[-1., 0.], [-1.5, 0.]]))
    capture('common_first_different_degree', lambda: order_exact_affine_roots(
        args[0], args[1], second, **kwargs))
    return records


def test_legacy_records_and_failed_budget_diagnostics_match_before_extraction():
    expected = json.loads(GOLDEN.read_text())
    assert expected['baseline_commit'] == '80ea73d'
    assert legacy_records() == expected['records']
