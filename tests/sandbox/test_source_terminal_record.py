"""Passive terminal checks on original published data, never new physics."""
import copy
import json
from pathlib import Path

import pytest

from sludge_sandbox.source_terminal_record import _Graph, _read_events, inspect_source_terminal

ARCHIVE = Path(__file__).resolve().parents[2]/'docs/sandbox/research/source-resume-v1/native01'


def test_unknown_raw_type_refused():
    graph = {'schema': 'source_run_raw_projection_v1', 'root': {'ref':'0'},
             'nodes': {'0': {'type': 'subprocess.Popen', 'fields': {}, 'uninitialized_fields': []}},
             'numeric_validation_performed':False, 'resume_authorized':False}
    with pytest.raises(ValueError, match='unsupported'):
        _Graph(graph)


def test_original_terminal_graph_is_readable_without_checkpoint_admission():
    events = _read_events(ARCHIVE/'continuous/trajectory')
    assert len(events) == 60
    terminal = events[-1][1].root
    assert terminal.values['status'] == 'completed'
    assert terminal.values['execution'].values['checkpoint'] is None


def test_cycle_refused():
    graph = {'schema': 'source_run_raw_projection_v1', 'root': {'ref':'0'},
             'nodes': {'0': {'type': 'builtins.tuple', 'values': [{'ref':'0'}]}},
             'numeric_validation_performed':False, 'resume_authorized':False}
    with pytest.raises(ValueError, match='cycle'):
        _Graph(graph)


def _original_numerical_inputs():
    import sludge_sandbox.source_terminal_record as terminal
    wire = json.loads((ARCHIVE/'continuous/trajectory/events/000060.json').read_bytes())['payload']
    body = _Graph(wire).root.values['execution'].values
    result = terminal._materialize(body['result'])
    policy = terminal._materialize(body['committed_checkpoint'].values['problem']).policy
    return wire, (result.states[0], result.times_s[0], result.times_s[-1], policy)


def test_repeated_committed_observations_rejected_before_digest(monkeypatch):
    """Regression from the independent Python review's compact wire fixture."""
    import sludge_sandbox.source_terminal_record as terminal
    wire, inputs = _original_numerical_inputs()
    nodes = wire['nodes']
    checkpoint = next(node for node in nodes.values() if node['type'] ==
                      'sludge_sandbox.exact_integration_checkpoint.ExactIntegrationCheckpoint')
    values = nodes[checkpoint['fields']['observations']['ref']]['values']
    values.extend([values[0]] * (terminal.MAX_OBSERVATIONS + 1-len(values)))
    execution = _Graph(json.loads(json.dumps(wire))).root.values['execution']
    monkeypatch.setattr(terminal, '_digest', lambda *_: pytest.fail('invalid history reached digest'))
    with pytest.raises(ValueError, match='limit|observations|history'):
        terminal._numerical(execution, *inputs)


def test_compact_shared_identity_rejected_before_materialization(monkeypatch):
    import sludge_sandbox.source_terminal_record as terminal
    wire, inputs = _original_numerical_inputs()
    nodes = wire['nodes']
    state = next(node for node in nodes.values()
                 if node['type'] == 'sludge_sandbox.integration.ConservedState')
    child = state['fields']['energy_model_identity']
    for _ in range(24):
        key = str(len(nodes))
        nodes[key] = {'type': 'builtins.tuple', 'values': [child, child]}
        child = {'ref': key}
    state['fields']['energy_model_identity'] = child
    # The original graph remains well-formed and small, yet naive constructor
    # comparisons could unfold millions of repetitions of the saved identity.
    graph = _Graph(json.loads(json.dumps(wire)))
    assert graph.visits < terminal.MAX_VALUES
    monkeypatch.setattr(terminal, '_materialize', lambda *_: pytest.fail('expanded before budget admission'))
    with pytest.raises(ValueError, match='expansion_size_limit'):
        terminal._numerical(graph.root.values['execution'], *inputs)


def test_callback_shared_states_rejected_before_source_reification(monkeypatch):
    import sludge_sandbox.source_terminal_record as terminal
    for path in sorted((ARCHIVE/'continuous/trajectory/events').glob('*.json')):
        event = json.loads(path.read_bytes())
        if event['event'] == 'rhs_returned':
            break
    else:
        pytest.fail('missing original callback fixture')
    wire = event['payload']
    nodes = wire['nodes']
    evaluation = next(node for node in nodes.values() if node['type'] ==
                      'sludge_sandbox.exact_source_column.SourceExactEvaluation')
    states = nodes[evaluation['fields']['source_states']['ref']]['values']
    states.extend([states[0]] * 50000)
    raw = json.dumps(wire).encode()
    graph = _Graph(json.loads(raw))
    assert len(raw) < 2 * 1024 * 1024 and graph.visits < terminal.MAX_VALUES
    monkeypatch.setattr(terminal, 'reify', lambda *_: pytest.fail('callback expanded before admission'))
    with pytest.raises(ValueError, match='expansion_size_limit'):
        terminal._materialize(graph.root['evaluation'])


@pytest.fixture(scope='module')
def saved_parent():
    from sludge_sandbox.source_study_record import decode_source_study
    directory = ARCHIVE/'parent/run'
    return (json.loads((directory/'result.json').read_bytes()),
            decode_source_study((directory/'source-study-record.json').read_bytes()))


@pytest.fixture
def admitted_archive(monkeypatch, saved_parent):
    """Software seam only: public archive omits assets and is NOT an admitted run."""
    import sludge_sandbox.source_terminal_record as terminal
    summary, record = saved_parent
    monkeypatch.setattr(terminal, 'read_run_with_source_record', lambda path: (summary, {}, record))
    from test_source_study_cli import _forbid_physics
    _forbid_physics(monkeypatch)
    def forbidden(*args, **kwargs):
        pytest.fail('terminal reader attempted new physical integration')
    import sludge_sandbox.source_trajectory as trajectory
    import sludge_sandbox.exact_integration as integration
    import sludge_sandbox.source_run_builder as builder
    monkeypatch.setattr(trajectory, 'open_source_trajectory', forbidden)
    monkeypatch.setattr(builder, 'build_source_run', forbidden)
    monkeypatch.setattr(integration, 'integrate_exact_checkpointed', forbidden)
    return summary, record


def _call(directory):
    request = json.loads((ARCHIVE/'continuous/request.json').read_bytes())
    outcome = json.loads((ARCHIVE/'continuous/OUTCOME.json').read_bytes())
    return inspect_source_terminal(directory, parent_directory=ARCHIVE/'parent/run', request=request, outcome=outcome)


def test_original_published_numeric_events_observations_and_balances(admitted_archive):
    report = _call(ARCHIVE/'continuous/trajectory')
    assert report['accepted_steps'] == 3 and report['observations'] == 22
    assert report['lineage_counts']['rhs_started'] == 54
    assert report['new_eos_calls'] == 0 and report['controller_arithmetic_replay'] is False
    assert sum(row['role'] == 'accepted' for row in report['controller_observation_roles']) == 3


def test_public_archive_missing_private_assets_is_not_admitted():
    with pytest.raises(ValueError):
        _call(ARCHIVE/'continuous/trajectory')


@pytest.fixture
def copied_trajectory(tmp_path):
    import shutil
    directory = tmp_path/'trajectory'
    shutil.copytree(ARCHIVE/'continuous/trajectory', directory)
    return directory


def _mutate_event(directory, number, mutator):
    path = directory/'events'/f'{number:06d}.json'
    event = json.loads(path.read_bytes())
    mutator(event)
    path.write_text(json.dumps(event))


def _first_node(event, kind):
    return next(node for node in event['payload']['nodes'].values() if node['type'].endswith('.'+kind))


@pytest.mark.parametrize('case', ['ordinal', 'extra_field', 'huge_integer', 'nonfinite', 'array_size',
    'terminal_failure', 'count', 'clock', 'balance', 'role', 'lease_error', 'accepted_state', 'checkpoint_debit'])
def test_saved_semantic_tampering_is_refused(admitted_archive, copied_trajectory, case):
    def change(event):
        if case == 'ordinal': event['ordinal'] = True
        elif case == 'extra_field': _first_node(event, 'ExactIntegrationResult')['fields']['invented'] = 1
        elif case == 'huge_integer': _first_node(event, 'ExactIntegrationResult')['fields']['evaluations'] = 1 << 4097
        elif case == 'nonfinite': _first_node(event, 'ExactIntegrationResult')['fields']['elapsed_seconds'] = {'binary64':'inf'}
        elif case == 'array_size': _first_node(event, 'ndarray')['shape'] = [250001]
        elif case == 'terminal_failure': event['event'] = 'ordinary_segment_failed'
        elif case == 'count': _first_node(event, 'ExactIntegrationResult')['fields']['evaluations'] = 21
        elif case == 'clock': _first_node(event, 'ExactEventTime')['fields']['seconds'] = {'fraction':[0,1]}
        elif case == 'balance': _first_node(event, 'SourceTransitionBalance')['fields']['energy_residual_j'] = {'fraction':[1,1]}
        elif case == 'role': _first_node(event, 'ExactCallbackObservation')['fields']['role'] = 'invented'
        elif case == 'lease_error':
            root = event['payload']['nodes'][event['payload']['root']['ref']]
            root['fields']['primary_error'] = 'saved_error'
        elif case == 'accepted_state':
            node = _first_node(event, 'ConservedState')
            ref = node['fields']['internal_energy_j']['ref']
            event['payload']['nodes'][ref]['values'][0] = {'binary64': '0x1.0000000000000p+0'}
        elif case == 'checkpoint_debit': _first_node(event, 'ExactIntegrationCheckpoint')['fields']['cumulative_u'] = {'ref':'0'}
    _mutate_event(copied_trajectory, 59 if case == 'lease_error' else 60, change)
    with pytest.raises(ValueError):
        _call(copied_trajectory)


def test_missing_or_extra_event_and_symlink_refused(admitted_archive, copied_trajectory):
    path = copied_trajectory/'events'/'000002.json'
    old = path.read_bytes()
    path.unlink()
    with pytest.raises(ValueError, match='event_order'):
        _call(copied_trajectory)
    path.symlink_to(copied_trajectory/'events'/'000001.json')
    with pytest.raises(ValueError, match='regular_file'):
        _call(copied_trajectory)


def test_duplicate_json_keys_are_refused(admitted_archive, copied_trajectory):
    path = copied_trajectory/'events'/'000001.json'
    raw = path.read_bytes().replace(b'{', b'{"ordinal":1,', 1)
    path.write_bytes(raw)
    with pytest.raises(ValueError, match='duplicate_json_key'):
        _call(copied_trajectory)


@pytest.fixture
def copied_resume(tmp_path, monkeypatch, admitted_archive):
    """Original numeric packet + synthetic admission and relocated claim fixture.

    Private source admission is intentionally a seam, never a claim that this
    public export is itself restorable. No original bytes or runtime IDs change.
    """
    import hashlib
    import shutil
    from types import SimpleNamespace
    from sludge_sandbox.exact_integration_checkpoint_codec import decode_exact_checkpoint
    from sludge_sandbox.source_terminal_record import _Graph
    import sludge_sandbox.source_terminal_record as terminal
    packet_path = tmp_path/'packet'
    packet_path.mkdir()
    shutil.copytree(ARCHIVE/'paused/resume-point/events', packet_path/'events')
    trajectory = tmp_path/'resumed-trajectory'
    shutil.copytree(ARCHIVE/'resumed/trajectory', trajectory)
    envelope = json.loads((ARCHIVE/'paused/resume-point/packet.json').read_bytes())
    checkpoint = decode_exact_checkpoint((ARCHIVE/'paused/resume-point/ordinary-checkpoint.json').read_bytes())
    files = {'events/'+p.name:(hashlib.sha256(p.read_bytes()).hexdigest(),len(p.read_bytes()))
             for p in (packet_path/'events').iterdir()}
    packet = SimpleNamespace(parent_record=admitted_archive[1], parent_summary=admitted_archive[0],
        files=files, checkpoint=checkpoint, envelope=envelope)
    monkeypatch.setattr(terminal, 'read_source_trajectory_checkpoint', lambda path: packet)
    claim = packet_path/'.restore-attempt'; claim.mkdir()
    for name in ('started.json','restored.json'):
        value = json.loads((ARCHIVE/'paused/resume-point/.restore-attempt'/name).read_bytes())
        value['output'] = str(trajectory)
        (claim/name).write_text(json.dumps(value))
    request = json.loads((ARCHIVE/'resumed/request.json').read_bytes())
    outcome = json.loads((ARCHIVE/'resumed/OUTCOME.json').read_bytes())
    def invoke():
        return inspect_source_terminal(trajectory, parent_directory=ARCHIVE/'parent/run',
            request=request, outcome=outcome, input_checkpoint=packet_path)
    return trajectory, packet_path, invoke


def test_resumed_original_prefix_claim_counters_and_debit(copied_resume):
    _, _, invoke = copied_resume
    report = invoke()
    assert report['preserved_prefix_events'] == 32
    assert report['lineage_counts']['rhs_started'] == 54
    assert report['lineage_counts']['heos_started'] == 12
    assert report['saved_charged_segment_seconds'] > 0


@pytest.mark.parametrize('case', ['prefix_bytes', 'claim_failed', 'wrong_output', 'claimed_count_reset', 'saved_debit_reset'])
def test_resumed_lineage_changes_are_refused(copied_resume, case):
    trajectory, packet, invoke = copied_resume
    if case == 'prefix_bytes':
        path = trajectory/'events'/'000001.json'
        path.write_bytes(path.read_bytes()+b' ')
    elif case == 'claim_failed':
        (packet/'.restore-attempt/failed.json').write_text('{}')
    else:
        path = packet/'.restore-attempt/restored.json'
        data = json.loads(path.read_bytes())
        if case == 'wrong_output': data['output'] = '/private/tmp/unrelated-output'
        elif case == 'claimed_count_reset': data['counts']['rhs_started'] = 0
        else: data['charged_segment_seconds'] = 0.
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        invoke()


def test_end_accepted_energy_change_breaks_original_balance(admitted_archive, copied_trajectory):
    def change(event):
        nodes = event['payload']['nodes']
        result = _first_node(event, 'ExactIntegrationResult')['fields']
        state_ref = nodes[result['states']['ref']]['values'][-1]['ref']
        energy_ref = nodes[state_ref]['fields']['internal_energy_j']['ref']
        nodes[energy_ref]['values'][0] = {'binary64': '0x1.0000000000000p+0'}
    _mutate_event(copied_trajectory, 60, change)
    with pytest.raises(ValueError, match='local_step_balance'):
        _call(copied_trajectory)


def test_forged_terminal_counters_do_not_reset_original_parent_cost(admitted_archive, copied_trajectory):
    import sludge_sandbox.source_terminal_record as terminal
    def change(event):
        nodes = event['payload']['nodes']
        root = nodes[event['payload']['root']['ref']]['fields']
        for reference in nodes[root['counts']['ref']]['values']:
            pair = nodes[reference['ref']]['values']
            if pair[0] == 'rhs_started': pair[1] = 22
    _mutate_event(copied_trajectory, 60, change)
    request = json.loads((ARCHIVE/'continuous/request.json').read_bytes())
    outcome = json.loads((ARCHIVE/'continuous/OUTCOME.json').read_bytes())
    outcome['counts']['rhs_started'] = 22
    with pytest.raises(ValueError, match='intermediate_counts'):
        inspect_source_terminal(copied_trajectory, parent_directory=ARCHIVE/'parent/run', request=request, outcome=outcome)


def test_bound_graph_work_precedes_excessive_resolution(monkeypatch):
    import sludge_sandbox.source_terminal_record as terminal
    monkeypatch.setattr(terminal, 'MAX_VALUES', 10)
    graph = {'schema':'source_run_raw_projection_v1', 'root':{'ref':'0'},
        'nodes':{'0':{'type':'builtins.tuple','values':list(range(11))}},
        'numeric_validation_performed':False, 'resume_authorized':False}
    with pytest.raises(ValueError, match='sequence_limit'):
        _Graph(graph)


def test_qualification_upgrade_in_saved_mapping_refused():
    graph = {'schema':'source_run_raw_projection_v1', 'root':{'ref':'0'},
        'nodes':{'0':{'type':'builtins.dict','fields':{'material_qualified':True}}},
        'numeric_validation_performed':False, 'resume_authorized':False}
    with pytest.raises(ValueError, match='qualification_upgrade'):
        _Graph(graph)


def test_shared_dag_comparison_is_bounded_without_expansion():
    from sludge_sandbox.source_terminal_record import _same
    left = right = ('leaf',)
    for _ in range(90):
        left, right = (left,left), (right,right)
    assert _same(left,right)


def test_completed_advance_cannot_exceed_requested_new_step_pause(admitted_archive):
    request = json.loads((ARCHIVE/'continuous/request.json').read_bytes())
    request['pause_after_steps'] = 1
    outcome = json.loads((ARCHIVE/'continuous/OUTCOME.json').read_bytes())
    with pytest.raises(ValueError, match='requested_pause_steps'):
        inspect_source_terminal(ARCHIVE/'continuous/trajectory', parent_directory=ARCHIVE/'parent/run',
            request=request, outcome=outcome)


def test_completed_resume_counts_only_new_steps_against_pause(copied_resume):
    trajectory, packet, _ = copied_resume
    request = json.loads((ARCHIVE/'resumed/request.json').read_bytes())
    outcome = json.loads((ARCHIVE/'resumed/OUTCOME.json').read_bytes())
    request['pause_after_steps'] = 1
    with pytest.raises(ValueError, match='requested_pause_steps'):
        inspect_source_terminal(trajectory, parent_directory=ARCHIVE/'parent/run',
            request=request, outcome=outcome, input_checkpoint=packet)
    request['pause_after_steps'] = 2
    report = inspect_source_terminal(trajectory, parent_directory=ARCHIVE/'parent/run',
        request=request, outcome=outcome, input_checkpoint=packet)
    assert report['accepted_steps'] == 3 and report['new_accepted_steps'] == 2
