"""Actual loopback presentation boundary; all physical operations forbidden."""
import json
import threading

import pytest

from test_source_run_view import source_bundle, forbid_physics
from test_local_app import request, CASE
from sludge_sandbox import local_app as app


@pytest.fixture
def view_server(source_bundle, tmp_path):
    server = app.make_server(view_source_run=source_bundle, storage_directory=tmp_path/'storage')
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield server
    server.close(); thread.join(timeout=3)
    assert not thread.is_alive()


def test_view_only_startup_needs_no_case_or_water(view_server):
    code, config = request(view_server, '/api/config')
    assert code == 200 and config['case'] is None and not config['launch_enabled']
    assert config['source_run_mounted']
    assert 'source-view' in request(view_server, '/')[1]
    code, view = request(view_server, '/api/source-run')
    assert code == 200 and view['result']['status'] == 'cancelled'
    assert view['study']['capture_count'] == 3
    code, selected = request(view_server, '/api/source-run/study?capture_index=0&cell=1')
    assert code == 200
    assert selected['study']['selected_capture']['observation']['time']['numerator'] == str(2**80+19)
    assert selected['study']['selected_capture']['observation']['cells'][0]['cell_index'] == 1
    assert request(view_server, '/api/source-run/study?capture_index=1')[1]['study']['selected_capture']['capture_status'] == 'failed'
    assert request(view_server, '/api/source-run/study?capture_index=2')[1]['study']['selected_capture']['return_identity'] == 'no_saved_return'


def test_http_export_and_asset_retain_source_bytes(view_server, source_bundle):
    assets = request(view_server, '/api/source-run')[1]['assets']
    code, value = request(view_server, '/api/source-run/asset?id='+assets[0]['asset_id'])
    assert code == 200 and value['text'].encode() == (source_bundle/assets[0]['path']).read_bytes()
    code, exported = request(view_server, '/api/source-run/export')
    assert code == 200 and exported['canonical_source_record']['text'].encode() == (source_bundle/'source-study-record.json').read_bytes()


@pytest.mark.parametrize('path', ['/api/source-run?path=/etc/passwd', '/api/source-run/asset?path=../../case.json',
    '/api/source-run/asset?id=../case.json', '/api/source-run/study?capture_index=0&capture_index=1',
    '/api/source-run/study?limit=51', '/api/source-run/study?cell=0',
    '/api/source-run/study?path=../../case.json', '/api/source-run/study?capture_index=-1'])
def test_browser_cannot_supply_paths_or_unbounded_selectors(view_server, path):
    assert request(view_server, path)[0] == 400


def test_browser_mutations_stay_unavailable_for_view_only_startup(view_server):
    assert request(view_server, '/api/validate', {'case': {}})[0] == 409
    assert request(view_server, '/api/jobs', {'case': {}, 'wall_seconds': 1, 'grace_seconds': 1})[0] == 409
    assert request(view_server, '/api/source-run', {})[0] == 404
    assert request(view_server, '/api/source-run', headers={'X-Sandbox-Token':'wrong'})[0] == 403
    assert request(view_server, '/api/source-run', headers={'Origin':'https://evil.example'})[0] == 403


def test_asset_tamper_is_visible_on_next_request(view_server, source_bundle):
    (source_bundle/'assets/fixture-source.txt').write_text('tampered')
    code, view = request(view_server, '/api/source-run')
    assert code == 400 and 'artifact_hash_mismatch' in view['reason']
    assert request(view_server, '/api/source-run/export')[0] == 400


def test_existing_case_gui_can_coexist_with_source_mount(source_bundle, tmp_path):
    manager = app.JobManager(case_path=CASE, water_directory=tmp_path/'unused-water', evidence_directory=None,
                            storage_directory=tmp_path/'both', maximum_jobs=2, view_source_run=source_bundle)
    config = manager.config()
    assert config['case']['grid']['cells'] == 2 and config['launch_enabled'] and config['source_run_mounted']
    assert manager.validate(config['case'])['status'] == 'schema_valid'
    assert manager.source_view('summary', {})['result']['status'] == 'cancelled'
    manager.close()


def test_cli_view_only_startup_passes_trusted_mount_without_fake_inputs(source_bundle, tmp_path, monkeypatch):
    from sludge_sandbox.cli import main
    captured = {}
    monkeypatch.setattr(app, 'serve_local', lambda **kwargs: captured.update(kwargs))
    assert main(['ui', '--view-source-run', str(source_bundle), '--storage', str(tmp_path/'storage')]) == 0
    assert captured['case_path'] is None and captured['water_directory'] is None
    assert captured['view_source_run'] == source_bundle


def test_view_only_cannot_cancel_preexisting_job_or_write_any_file(view_server):
    import uuid
    identifier = str(uuid.uuid4())
    job = view_server.manager.jobs_directory/identifier
    job.mkdir()
    (job/'job.json').write_text(json.dumps({'schema':'sandbox_job_v1','job_id':identifier,'operation':'source-run'}))
    before = {p.relative_to(job): p.read_bytes() for p in job.rglob('*') if p.is_file()}
    code, response = request(view_server, f'/api/jobs/{identifier}/cancel', {})
    after = {p.relative_to(job): p.read_bytes() for p in job.rglob('*') if p.is_file()}
    assert code == 409 and response['reason'] == 'saved_source_view_is_read_only'
    assert after == before
