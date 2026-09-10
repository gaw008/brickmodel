"""Source-run lifecycle with actual source classes and an explicit liquid seam."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time

import pytest

from test_mass_storage_bridge import REPOSITORY
from sludge_sandbox.run_service import read_run, _seal, replay_run, resume_run, RunError
from sludge_sandbox.source_run_journal import raw_projection, SourceRunJournal
from sludge_sandbox.source_run_service import run_source_case, _Recorder, _RunStop, RECORD
from sludge_sandbox.source_study_record import decode_source_study

CASE = REPOSITORY / 'data/sandbox/cases/source-multicell-heos-v1.json'


def test_raw_nonfinite_and_partial_constructor_are_explicit():
    @dataclass
    class HalfBuilt:
        value: float
        missing: str
    half = object.__new__(HalfBuilt)
    half.value = float('nan')
    raw = raw_projection(half)
    node = raw['nodes'][raw['root']['ref']]
    assert node['fields']['value'] == {'nonfinite_binary64': 'nan'}
    assert node['uninitialized_fields'] == ['missing']
    assert raw['numeric_validation_performed'] is False
    json.dumps(raw, allow_nan=False)


def test_journal_retains_completed_event_and_exclusive_names(tmp_path):
    journal = SourceRunJournal(tmp_path)
    reference = journal.append('started', {'time': 0.})
    raw = (tmp_path / reference['path']).read_bytes()
    assert reference['sha256'] == hashlib.sha256(raw).hexdigest()
    other = SourceRunJournal.__new__(SourceRunJournal)
    other.directory, other.count, other.total_bytes = journal.directory, 0, 0
    with pytest.raises(FileExistsError):
        other.append('overwrite', {})
    assert (tmp_path / reference['path']).read_bytes() == raw


@pytest.mark.parametrize('mode', ['cancel', 'invalid', 'missing', 'missing_assets', 'broken_cancel'])
def test_preconstruction_failure_is_sealed_and_readable(tmp_path, monkeypatch, mode):
    import sludge_sandbox.source_run_builder as builder
    monkeypatch.setattr(builder, 'build_source_run', lambda *a: pytest.fail('unexpected backend construction'))
    case, assets, cancel = CASE, REPOSITORY, None
    if mode == 'cancel':
        cancel = lambda: True
    elif mode == 'invalid':
        case = tmp_path / 'bad.json'
        case.write_text('{"schema": "unknown"}')
    elif mode == 'missing':
        case = tmp_path / 'absent.json'
    elif mode == 'missing_assets':
        assets = tmp_path
    else:
        def cancel():
            raise RuntimeError('broken caller cancellation')
    output = tmp_path / 'run'
    result = run_source_case(case, assets, output, cancel=cancel)
    assert result['status'] == ('cancelled' if mode == 'cancel' else 'failed')
    assert result['counts']['heos_started'] == result['counts']['rhs_started'] == 0
    assert result['source_record'] is not None, result.get('source_record_error')
    checked, _ = read_run(output)
    assert checked == result
    assert result['original_case_available'] is (mode != 'missing')
    with pytest.raises(FileExistsError):
        run_source_case(case, assets, output)


def liquid_seam(monkeypatch):
    """Only test backend factories and original liquid evaluator are replaced."""
    from test_source_wet_column import setup
    import sludge_sandbox.source_run_builder as module
    from sludge_sandbox.water_properties import WaterProperties
    from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    setup(monkeypatch)
    monkeypatch.setattr(module, 'load_water_properties', lambda p, **k: WaterProperties(p))
    monkeypatch.setattr(module, 'IdealWaterVapor', lambda p, **k: IdealWaterVapor(p))
    monkeypatch.setattr(module, 'WaterChemicalPotential', lambda p, **k: WaterChemicalPotential(p))


@pytest.fixture(scope='module')
def actual_run(tmp_path_factory):
    output = tmp_path_factory.mktemp('source-service') / 'run'
    with pytest.MonkeyPatch.context() as patch:
        liquid_seam(patch)
        result = run_source_case(CASE, REPOSITORY, output)
    return output, result


def test_actual_source_pipeline_publishes_full_captures(actual_run):
    output, result = actual_run
    assert result['status'] == 'completed', result
    assert result['source_record'] is not None
    record = decode_source_study((output / RECORD).read_bytes())
    assert len(record.captures) == result['counts']['rhs_started']
    assert result['counts']['initial_energy_started'] == result['counts']['initial_energy_returned'] == 3
    assert record.roots['transition'].material_qualified is False
    assert len(record.roots['transition'].candidates) == 2
    assert record.metadata['effective_inputs']['horizon'] > 0
    assert record.metadata['initial_energy_points']['nodes']
    assert read_run(output)[0] == result
    assert result['counts']['heos_started'] == 0  # Explicit test backend, never real HEOS evidence.


def test_resealed_success_claim_is_rejected(actual_run, tmp_path):
    import shutil
    output, result = actual_run
    target = tmp_path / 'altered'
    shutil.copytree(output, target)
    changed = dict(result, numerical_event_accepted=not result['numerical_event_accepted'])
    (target / 'result.json').write_text(json.dumps(changed))
    _seal(target)
    with pytest.raises(RunError, match='summary_changed'):
        read_run(target)


def test_resume_is_explicitly_unavailable_without_restarting(actual_run, tmp_path):
    with pytest.raises(RunError, match='source_study_resume_not_implemented'):
        resume_run(actual_run[0], tmp_path / 'unexpected')
    assert not (tmp_path / 'unexpected').exists()


def test_replay_uses_frozen_input_and_obeys_cancel_before_new_physics(actual_run, tmp_path):
    result = replay_run(actual_run[0], tmp_path / 'replay', cancel=lambda: True)
    assert result['status'] == 'cancelled' and result['replay_of']
    assert result['counts']['rhs_started'] == result['counts']['heos_started'] == 0
    assert result['case_sha256'] == actual_run[1]['case_sha256']
    assert read_run(tmp_path / 'replay')[0] == result


def test_failed_run_cannot_gain_event_acceptance_by_resealing(tmp_path):
    output = tmp_path / 'missing'
    result = run_source_case(tmp_path / 'absent', REPOSITORY, output)
    result.update(numerical_comparison_completed=True, numerical_event_accepted=True)
    (output / 'result.json').write_text(json.dumps(result))
    _seal(output)
    with pytest.raises(RunError, match='incomplete_summary_changed'):
        read_run(output)


def test_failed_run_cannot_gain_completed_status_by_resealing(tmp_path):
    output = tmp_path / 'missing'
    result = run_source_case(tmp_path / 'absent', REPOSITORY, output)
    result['status'] = 'completed'
    (output / 'result.json').write_text(json.dumps(result))
    _seal(output)
    with pytest.raises(RunError, match='terminal_status_changed'):
        read_run(output)


@pytest.mark.parametrize('kind', [None, 'invented_kind'])
def test_source_record_cannot_bypass_checks_by_changing_kind(tmp_path, kind):
    output = tmp_path / 'missing'
    result = run_source_case(tmp_path / 'absent', REPOSITORY, output)
    result.pop('source_record')
    result['integration_kind'] = kind
    result.update(numerical_comparison_completed=True, numerical_event_accepted=True)
    (output / 'result.json').write_text(json.dumps(result))
    _seal(output)
    with pytest.raises(RunError, match='source_run_kind_changed'):
        read_run(output)


def test_failed_energy_notification_does_not_replace_domain_exit(tmp_path, monkeypatch):
    from sludge_sandbox.integration import DomainExit
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    liquid_seam(monkeypatch)
    def failed_energy(*args):
        raise DomainExit('original energy domain failure')
    monkeypatch.setattr(SourceWetStorage, 'evaluate', failed_energy)
    original = SourceRunJournal.append
    def fail_notification(self, event, payload):
        if event == 'initial_energy_failed':
            raise OSError('secondary notification write failure')
        return original(self, event, payload)
    monkeypatch.setattr(SourceRunJournal, 'append', fail_notification)
    output = tmp_path / 'energy-failed'
    result = run_source_case(CASE, REPOSITORY, output)
    assert result['status'] == 'domain_exit' and result['reason'] == 'original energy domain failure'
    record = decode_source_study((output / RECORD).read_bytes())
    assert record.metadata['notification_failures'][0]['reason'] == 'secondary notification write failure'
    assert read_run(output)[0] == result


@pytest.mark.parametrize('event', ['initial_energy_returned', 'rhs_returned'])
def test_actual_return_survives_single_journal_write_failure(tmp_path, monkeypatch, event):
    liquid_seam(monkeypatch)
    original = SourceRunJournal.append
    failed = []
    def one_failure(self, name, payload):
        if name == event and not failed:
            failed.append(payload)
            raise OSError('injected return journal failure')
        return original(self, name, payload)
    monkeypatch.setattr(SourceRunJournal, 'append', one_failure)
    output = tmp_path / 'io-failed'
    result = run_source_case(CASE, REPOSITORY, output)
    assert result['status'] == 'failed' and len(failed) == 1
    assert result['counts'][event] == 1
    record = decode_source_study((output / RECORD).read_bytes())
    assert record.metadata['undurable_returns']['nodes']
    if event == 'rhs_returned':
        assert len(record.captures) == 1 and record.captures[0]['evaluation'] is not None
        assert record.captures[0]['failure'] == 'injected return journal failure'
        assert record.observations[0] is None
    else:
        assert record.metadata['initial_energy_points']['nodes']
    assert read_run(output)[0] == result


def test_cancel_after_first_initial_energy_preserves_actual_point(tmp_path, monkeypatch):
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    liquid_seam(monkeypatch)
    original = SourceWetStorage.evaluate
    calls = []
    def stop_after_return(self, state, temperature):
        point = original(self, state, temperature)
        calls.append(point)
        return point
    monkeypatch.setattr(SourceWetStorage, 'evaluate', stop_after_return)
    output = tmp_path / 'cancelled'
    result = run_source_case(CASE, REPOSITORY, output, cancel=lambda: bool(calls))
    assert result['status'] == 'cancelled'
    assert result['counts']['initial_energy_started'] == result['counts']['initial_energy_returned'] == 1
    assert result['counts']['rhs_started'] == 0
    assert read_run(output)[0] == result


def test_blocked_rhs_does_not_relabel_previous_success(tmp_path, monkeypatch):
    from test_source_liquid_column import setup
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.exact_event_clock import ExactEventTime
    from sludge_sandbox.source_run_observer import observer_scope
    from fractions import Fraction
    model, initial = setup(monkeypatch, count=1)
    adapter = ExactSourceColumn(model)
    state, at = adapter.pack(initial), ExactEventTime(Fraction())
    recorder = _Recorder(tmp_path, None, time.monotonic())
    recorder.limits = {'total_callback_cap': 1, 'outer_seconds': 60., 'wet_pressure_request_cap': 1}
    with observer_scope(recorder):
        adapter.evaluate(state, at)
        with pytest.raises(_RunStop):
            adapter.evaluate(state, at)
    assert len(recorder.captures) == 1
    assert 'evaluation' in recorder.captures[0] and 'failure' not in recorder.captures[0]
    assert recorder.counts['rhs_started'] == recorder.counts['rhs_returned'] == 1
