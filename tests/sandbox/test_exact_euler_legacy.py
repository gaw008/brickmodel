"""Full pre-extraction SSPRK2 captures/outputs; wall timing is not deterministic."""
from dataclasses import fields, replace
from fractions import Fraction as F
import json
from pathlib import Path
import numpy as np

from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_integration import integrate_exact
from sludge_sandbox.exact_root_order import _data
from sludge_sandbox.integration import ConservedState, DomainExit
from test_exact_integration import initial, policy, rates


GOLDEN = Path(__file__).parent/'fixtures/exact-euler-legacy-v1.json'


def legacy_records():
    output = {}
    h = F(1, 64)
    base = replace(policy(), initial_step_s=float(h), maximum_step_s=float(h),
                   minimum_step_s=float(h/16), maximum_steps=4, maximum_rejections=2)

    def run(name, *, state=None, config=base, origin=F(), duration=h, variant='constant', cancel_after=None):
        calls = []
        def op(s, at):
            entry = {'input': _data(s), 'time': _data(at)}
            calls.append(entry)
            try:
                if variant == 'endpoint_domain' and at.seconds > origin:
                    raise DomainExit('frozen_endpoint_domain')
                r = rates(s)
                if s.mechanical_stretches is None:
                    r = replace(r, mechanical_rates_per_s=None, cell_power_components_w=None)
                if variant == 'nonlinear':
                    r = replace(r, reaction_species_mol_s=np.array([[s.amounts_mol[0, 0], 0.], [0., 0.]]))
                if variant == 'negative_stretch':
                    r = replace(r, mechanical_rates_per_s=np.array([-1000., 0., 0.]))
                if variant == 'schema' and len(calls) > 2:
                    r = replace(r, cell_power_components_w=None)
                entry['rates'] = _data(r)
                return r
            except DomainExit as exc:
                entry['failure'] = [type(exc).__name__, str(exc)]
                raise
        result = integrate_exact(initial() if state is None else state, op,
            start_s=T(origin), end_s=T(origin+duration), policy=config,
            cancel=(lambda: len(calls) >= cancel_after) if cancel_after else None)
        output[name] = {'calls': calls, 'result': {f.name: _data(getattr(result, f.name))
                         for f in fields(result) if f.name != 'elapsed_seconds'}}

    run('mechanical_shared_faces')
    run('large_exact_origin', origin=F(2**80)+F(1, 3))
    run('no_mechanics', state=ConservedState([[1., 0.], [2., 0.]], [10., -20.]))
    run('nonlinear_trial_rejection', variant='nonlinear')
    run('negative_stretch', variant='negative_stretch')
    run('amount_roundoff', config=replace(base, amount_absolute_tolerance_mol=1e-30))
    run('energy_roundoff', config=replace(base, energy_absolute_tolerance_j=1e-30))
    run('schema_change', variant='schema')
    run('domain_trial', variant='endpoint_domain')
    run('accepted_step_cap', duration=2*h, config=replace(base, maximum_steps=1))
    run('cancel_after_prefix', duration=2*h, cancel_after=9)
    run('zero_outflow', state=ConservedState([[0., 0.], [2., 0.]], [10., 20.]))
    return output


def test_all_pre_extraction_captures_and_results_are_unchanged():
    saved = json.loads(GOLDEN.read_text())
    assert saved['baseline_commit'] == 'cc94ecb'
    assert legacy_records() == saved['records']
