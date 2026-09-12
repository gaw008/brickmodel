"""Passive boundary regressions: temporary fake jobs and bounded JSON only."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import uuid

import pytest
from sludge_sandbox import local_app as app
from sludge_sandbox import source_run_view as view
from test_source_run_view import source_bundle, forbid_physics


def test_read_only_manager_cannot_cancel_an_existing_persisted_job(tmp_path):
    manager=app.JobManager(case_path=None,water_directory=None,evidence_directory=None,
        storage_directory=tmp_path/'storage',maximum_jobs=2,view_source_run=tmp_path/'unused-mount')
    identifier=str(uuid.uuid4())
    directory=manager.jobs_directory/identifier
    directory.mkdir()
    (directory/'job.json').write_text(json.dumps({'schema':'sandbox_job_v1','job_id':identifier,'operation':'source-run'}))
    try:
        with pytest.raises(app.LocalAppError):
            manager.cancel_job(identifier)
        assert not (directory/'cancel.json').exists()
    finally:
        manager.close()


def test_response_budget_stops_before_serializing_repeated_large_text():
    graph={'schema':'source_run_raw_projection_v1','root':{'ref':'root'},'nodes':{
        'root':{'values':[{'ref':'shared'} for _ in range(256)]},
        'shared':{'fields':{'text':'x'*65536}}}}
    real=json.dumps
    def bounded_dumps(value,*args,**kwargs):
        # Fixture list is 16 MiB if encoded whole; leaf serialization is fine.
        if type(value) is list and len(value)==256:
            pytest.fail('whole amplified DAG reached JSON serialization before response budget')
        return real(value,*args,**kwargs)
    with patch.object(view.json,'dumps',bounded_dumps):
        with pytest.raises(ValueError):
            view.project_builder_path(graph,())


def test_malformed_builder_cell_is_a_controlled_data_error():
    graph={'schema':'source_run_raw_projection_v1','root':{'ref':'r'},'nodes':{'r':{'fields':[]}}}
    with pytest.raises(ValueError):
        view.project_builder_path(graph,())


def test_replaced_asset_bytes_after_complete_verification_are_not_returned(source_bundle, monkeypatch):
    # Alter only a disposable fixture between admission and the final asset read.
    original=view._open
    expected=(source_bundle/'assets/fixture-source.txt').read_bytes()
    asset_id=hashlib.sha256(b'assets/fixture-source.txt').hexdigest()
    def replace_after_admission(directory):
        accepted=original(directory)
        (source_bundle/'assets/fixture-source.txt').write_bytes(expected+b'changed')
        return accepted
    monkeypatch.setattr(view,'_open',replace_after_admission)
    with pytest.raises(ValueError,match='changed_after_validation'):
        view.read_source_run_asset(source_bundle,asset_id)


def test_discrete_cli_kelvin_fraction_keeps_unknown_heat_and_exact_clock(capsys):
    from sludge_sandbox.cli import main
    root=Path('/Users/wanggaoying/Desktop/brickmodel-github')
    code=main(['arlabosse95','--source',str(root/'data/sandbox/research/arlabosse95/source.json'),
        '--assets-root',str(root),'--moisture','1/10','--temperature','7363/20','--unit','K'])
    result=json.loads(capsys.readouterr().out)
    assert code==0
    point=result['point']
    assert point['temperature_K']=={'numerator':'7363','denominator':'20'}
    assert point['total_desorption_heat']['value'] is None
    assert point['total_desorption_heat']['digitization_bounds'] is None
    assert point['total_desorption_heat']['unknown_reasons']
    assert point['material_qualified'] is point['full_firing_cycle'] is False


@pytest.mark.parametrize('event', [[], {'event': 'builder_returned'}])
def test_malformed_saved_event_is_a_controlled_error(source_bundle, event):
    from sludge_sandbox.run_service import _seal
    path=next((source_bundle/'events').glob('*.json'))
    path.write_text(json.dumps(event))
    _seal(source_bundle)
    with pytest.raises(ValueError):
        view.inspect_source_run(source_bundle, capture_index=0, cell_index=0)
