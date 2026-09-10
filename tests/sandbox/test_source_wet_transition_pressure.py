"""Wet-neighbour pressure evidence in the actual N3 wet-to-dry comparison."""
from dataclasses import replace

import pytest

from test_source_multicell_transition import completed_multicell
from sludge_sandbox.source_dry_transition import (
    SourceDryTransitionError, compare_source_dry_candidates, evaluate_source_dry_transition,
)
from sludge_sandbox.source_net_prefix import _same


def test_empty_wet_strategy_preserves_original_pressure_result(completed_multicell):
    original = completed_multicell
    result = compare_source_dry_candidates(original.refinement, original.candidates,
        shared_volume=original.shared_volume, wet_pressure_pairs=())
    assert _same(result, original)
    assert result.wet_pressure_pairs == ()
    assert not result.numerical_event_accepted
    assert result.cell_selected_pressure_gates == ((False, True, False),) * 2


@pytest.fixture(scope='module')
def wet_strategy(completed_multicell):
    from sludge_sandbox.source_wet_shared_pressure import (
        declare_source_shared_wet_volume, collect_source_wet_pressure_pair,
    )
    old = completed_multicell
    column = old.refinement.approach.proposal.original_trial.adapter.column
    declarations = tuple(None if i == old.selected_cell_index else declare_source_shared_wet_volume(storage)
                         for i, storage in enumerate(column.storages))
    pairs = tuple(tuple(None if declaration is None else collect_source_wet_pressure_pair(
        old.candidates[0].cell_pressure_endpoints[phase][i],
        old.candidates[1].cell_pressure_endpoints[phase][i], shared_volume=declaration)
        for i, declaration in enumerate(declarations)) for phase in range(2))
    current = compare_source_dry_candidates(old.refinement, old.candidates,
        shared_volume=old.shared_volume, wet_pressure_pairs=pairs)
    return old, current, declarations


def test_actual_wet_pairs_complete_all_cell_gates_and_keep_old_failures(wet_strategy):
    old, current, _ = wet_strategy
    assert current.cell_selected_pressure_gates == ((True, True, True),) * 2
    assert current.numerical_event_accepted and not current.material_qualified
    assert current.clock_gate == old.clock_gate
    assert current.endpoint_gates == old.endpoint_gates
    assert current.cell_conditional_pressure_bounds_pa == old.cell_conditional_pressure_bounds_pa
    assert current.cell_conditional_pressure_gates == old.cell_conditional_pressure_gates
    assert all(row[0] is False and row[2] is False for row in current.cell_conditional_pressure_gates)
    assert current.pressure_strategy == 'explicit_shared_source_wet_and_dry_volume'
    assert current.candidates is old.candidates
    assert _same(current.balance_paths, old.balance_paths)
    assert current.shared_pressure_pairs == old.shared_pressure_pairs


def test_comparison_and_record_check_do_not_collect_new_water_states(wet_strategy, monkeypatch):
    from sludge_sandbox.water_properties import WaterProperties
    from sludge_sandbox.water_heos import HEOSWaterProperties
    import sludge_sandbox.source_wet_shared_pressure as wet

    def forbidden(*args, **kwargs):
        pytest.fail('passive transition check called water or collector')

    for cls in (WaterProperties, HEOSWaterProperties):
        monkeypatch.setattr(cls, 'state_tp', forbidden)
    monkeypatch.setattr(wet, 'collect_source_wet_pressure_pair', forbidden)
    wet_strategy[1].check()


def test_research_json_retains_wet_evidence_and_omits_live_storage(wet_strategy, monkeypatch):
    import importlib.util
    import json
    from pathlib import Path
    from sludge_sandbox.water_properties import WaterProperties

    def forbidden(*args, **kwargs):
        pytest.fail('research serialization called water')

    monkeypatch.setattr(WaterProperties, 'state_tp', forbidden)
    root = Path(__file__).resolve().parents[2]

    def load(relative):
        path = root / 'docs/sandbox/research' / relative
        spec = importlib.util.spec_from_file_location('wet_pressure_serialization_probe', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    base = load('exact-source-column-v1/run_native.py').serialize
    save = load('source-multicell-transition-v1/run_native.py').saved_record
    current = wet_strategy[1]
    encoded = json.loads(json.dumps(save(current.wet_pressure_pairs, base), allow_nan=False))
    for phase, row in enumerate(encoded):
        assert row[1] is None
        for cell in (0, 2):
            pair = current.wet_pressure_pairs[phase][cell]
            body = row[cell]['fields']
            assert body['status'] == pair.status
            assert body['material_qualified'] is False
            assert 'storage' not in body['shared_volume']['fields']
            assert len(body['endpoints']) == len(body['error_parts']) == 2
            attempts = body['evidence']['fields']['attempts']
            assert len(attempts) == len(pair.evidence.attempts)
            for recorded, actual in zip(attempts, pair.evidence.attempts):
                fields = recorded['fields']
                assert fields['state'] == save(actual.state, base)
                assert fields['pressure_pa'] == actual.pressure_pa
                assert fields['temperature_k'] == actual.temperature_k
                assert fields['failure_type'] is None


@pytest.mark.parametrize('mutation', ['cell', 'time', 'missing_row', 'empty_grid'])
def test_wet_pair_binding_rejects_different_cell_or_phase(wet_strategy, mutation):
    old, current, _ = wet_strategy
    grid = current.wet_pressure_pairs
    if mutation == 'cell':
        grid = ((grid[0][2], None, grid[0][0]), grid[1])
    elif mutation == 'time':
        grid = (grid[1], grid[0])
    elif mutation == 'missing_row':
        grid = grid[:1]
    else:
        grid = ((None, None, None),) * 2
    with pytest.raises(ValueError):
        compare_source_dry_candidates(old.refinement, old.candidates,
            shared_volume=old.shared_volume, wet_pressure_pairs=grid)


def test_one_original_wet_failure_still_prevents_event_acceptance(wet_strategy):
    old, current, _ = wet_strategy
    partial = tuple((None, *row[1:]) for row in current.wet_pressure_pairs)
    out = compare_source_dry_candidates(old.refinement, old.candidates,
        shared_volume=old.shared_volume, wet_pressure_pairs=partial)
    assert not out.numerical_event_accepted
    assert out.cell_selected_pressure_gates == ((False, True, True),) * 2


def test_new_runtime_collects_from_actual_candidates(wet_strategy):
    old, _, declarations = wet_strategy
    out = evaluate_source_dry_transition(old.refinement, end=old.candidates[0].end,
        maximum_callbacks_per_path=24, shared_volume=old.shared_volume,
        shared_wet_volumes=declarations)
    assert out.numerical_event_accepted and out.wet_pressure_pairs
    assert all(candidate.reference.status == 'completed' for candidate in out.candidates)
    for phase, row in enumerate(out.wet_pressure_pairs):
        for i, pair in enumerate(row):
            if pair is not None:
                assert pair.endpoints[0] is out.candidates[0].cell_pressure_endpoints[phase][i]
                assert pair.endpoints[1] is out.candidates[1].cell_pressure_endpoints[phase][i]


def test_equal_content_foreign_volume_rejected_before_dry_execution(wet_strategy, monkeypatch):
    import sludge_sandbox.source_dry_transition as module
    from sludge_sandbox.source_wet_shared_pressure import declare_source_shared_wet_volume

    old, _, declarations = wet_strategy
    changed = (declare_source_shared_wet_volume(replace(declarations[0].storage)), *declarations[1:])
    monkeypatch.setattr(module, 'execute_source_dry_candidate',
                        lambda *a, **k: pytest.fail('foreign declaration reached execution'))
    with pytest.raises(ValueError, match='original_cell'):
        evaluate_source_dry_transition(old.refinement, end=old.candidates[0].end,
            maximum_callbacks_per_path=24, shared_volume=old.shared_volume,
            shared_wet_volumes=changed)


def test_collector_failure_retains_completed_pair_and_partial_attempts(wet_strategy, monkeypatch):
    import sludge_sandbox.source_dry_transition as module
    import sludge_sandbox.source_wet_shared_pressure as wet

    old, current, declarations = wet_strategy
    returned = iter(old.candidates)
    monkeypatch.setattr(module, 'execute_source_dry_candidate', lambda *a, **k: next(returned))
    error = RuntimeError('observed collector failure')
    error.attempts = ('already returned observation', 'failed next request')
    collected = []

    def collector(*args, **kwargs):
        collected.append(args)
        if len(collected) == 1:
            return current.wet_pressure_pairs[0][0]
        raise error

    monkeypatch.setattr(wet, 'collect_source_wet_pressure_pair', collector)
    with pytest.raises(SourceDryTransitionError) as caught:
        evaluate_source_dry_transition(old.refinement, end=old.candidates[0].end,
            maximum_callbacks_per_path=24, shared_volume=old.shared_volume,
            shared_wet_volumes=declarations)
    failure = caught.value
    assert failure.__cause__ is error and failure.stage == 'wet_shared_pressure:0:2'
    assert failure.candidates == old.candidates and len(failure.records) == 2
    assert failure.records[0]['pair'] is current.wet_pressure_pairs[0][0]
    assert failure.records[1]['attempts'] is error.attempts
    assert failure.records[1]['cell_index'] == 2
