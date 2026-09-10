"""Nonstationary source heat transfer and an explicitly artificial liquid seam."""
from dataclasses import replace
from fractions import Fraction as F
import json
import time

import numpy as np
import pytest

from test_source_run_service import CASE, liquid_seam
from test_mass_storage_bridge import REPOSITORY
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_integration_checkpoint import _same
from sludge_sandbox.integration import IntegrationError
from sludge_sandbox.run_service import read_run_with_source_record
from sludge_sandbox.source_run_config import load_source_run_config
from sludge_sandbox.source_run_service import run_source_case
from sludge_sandbox.source_study_schema import reify
from sludge_sandbox.source_trajectory import SourceOrdinaryStepSizes, open_source_trajectory

DYNAMIC_CASE = REPOSITORY/'data/sandbox/cases/source-nonstationary-heos-v1.json'
RATIONALE = 'Explicit new post-event conduction segment; 1/64 s steps, original error and resource limits.'


def test_new_case_changes_only_declared_test_temperatures_and_conductivity():
    original = json.loads(CASE.read_bytes())
    dynamic = json.loads(DYNAMIC_CASE.read_bytes())
    assert load_source_run_config(DYNAMIC_CASE.read_bytes()).values['classification'] == 'manufactured_test_fixture'
    original['grid']['conductivities_w_m_k'] = [[.5,.7],[.5,.7]]
    original['initial']['temperature_k'] = [325.,327.,329.]
    assert dynamic == original


def test_nonstationary_continuous_and_paused_source_trajectories_agree(tmp_path, monkeypatch):
    # Same pressure-root precision derived for the old artificial-liquid seam;
    # the real HEOS case and all acceptance/error envelopes remain unchanged.
    values = json.loads(DYNAMIC_CASE.read_bytes())
    values['pressure_policy']['pressure_tolerance_pa'] = 1e-7
    case = tmp_path/'manufactured-seam-case.json'
    case.write_text(json.dumps(values))
    liquid_seam(monkeypatch)
    parent, sessions = None, []
    began = time.monotonic()
    def cancel():
        if time.monotonic()-began >= values['resources']['outer_seconds']:
            return True
        if parent is None:
            return False
        return any(parent['counts'][key]+sum(s.recorder.counts[key]-parent['counts'][key]
                   for s in sessions) >= values['resources'][limit]
                   for key,limit in (('rhs_started','total_callback_cap'), ('wet_started','wet_pressure_request_cap')))
    parent = run_source_case(case, REPOSITORY, tmp_path/'parent', cancel=cancel)
    assert parent['status'] == 'completed' and parent['numerical_event_accepted'], parent
    _, _, record = read_run_with_source_record(tmp_path/'parent')
    start = record.roots['transition'].candidates[1].end
    end = T(start.seconds+F(3,64))
    sizes = SourceOrdinaryStepSizes(1/64, 1/64, RATIONALE)
    continuous = open_source_trajectory(tmp_path/'parent', tmp_path/'continuous', end=end, step_sizes=sizes, cancel=cancel)
    sessions.append(continuous)
    baseline = continuous.advance()
    assert baseline.status == 'completed', (baseline.status, baseline.reason)
    paused = open_source_trajectory(tmp_path/'parent', tmp_path/'paused', end=end, step_sizes=sizes, cancel=cancel)
    sessions.append(paused)
    assert paused.step_sizes is not sizes  # Caller-owned input was snapshotted.
    first = paused.advance(pause_after_steps=1)
    assert first.status == 'paused' and len(first.execution.result.steps) == 1
    original_sizes = paused.step_sizes
    original_count = paused.recorder.counts['rhs_started']
    paused.step_sizes = replace(original_sizes, maximum_step_s=1/32)
    with pytest.raises(IntegrationError, match='definition_changed'):
        paused.advance()
    assert paused.recorder.counts['rhs_started'] == original_count
    paused.step_sizes = original_sizes
    finished = paused.advance()
    assert finished.status == 'completed', (finished.status, finished.reason)
    assert _same(replace(baseline.execution.result, elapsed_seconds=0.),
                 replace(finished.execution.result, elapsed_seconds=0.))
    assert _same(baseline.execution.observations, finished.execution.observations)
    assert _same(first.execution.result.steps, finished.execution.result.steps[:1])
    assert baseline.balances == finished.balances
    numerical = finished.execution.result
    assert len(numerical.steps) == 3 and numerical.evaluations == 22
    assert numerical.times_s[0] == start and numerical.times_s[-1] == end
    assert any(np.any(step.face_energy_j[1:-1]) for step in numerical.steps)
    assert np.any(numerical.states[-1].internal_energy_j != numerical.states[0].internal_energy_j)
    assert all(np.array_equal(s.amounts_mol, numerical.states[0].amounts_mol) for s in numerical.states)
    before = paused.recorder.captures[0]['evaluation'].source_evaluation.cells
    after = paused.recorder.captures[-1]['evaluation'].source_evaluation.cells
    assert paused.recorder.captures[-1]['time'] == end
    assert _same(reify(paused.recorder.captures[-1]['packed_input']), numerical.states[-1])
    assert any(abs(F(b.inverse.point.temperature_k)-F(a.inverse.point.temperature_k)) >
               F(a.inverse.temperature_error_bound_k)+F(b.inverse.temperature_error_bound_k)
               for a,b in zip(before,after))
    for old,new,step in zip(numerical.states,numerical.states[1:],numerical.steps):
        assert step.face_energy_j[0] == step.face_energy_j[-1] == 0
        assert abs(sum(F(float(x)) for x in new.internal_energy_j)-
                   sum(F(float(x)) for x in old.internal_energy_j)) <= F(paused.reference_policy.energy_absolute_tolerance_j)
    assert dict(finished.counts)['rhs_started'] == parent['counts']['rhs_started']+22
    assert finished.cumulative_outer_seconds >= parent['elapsed_wall_seconds']+numerical.elapsed_seconds
    assert len(finished.balances) == len(record.roots['transition'].balance_paths[1])+3
    assert not finished.material_qualified and not finished.full_firing_cycle and not finished.archived_resume_authorized
