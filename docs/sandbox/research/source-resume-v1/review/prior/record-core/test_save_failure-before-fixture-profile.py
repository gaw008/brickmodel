"""Actual save failure path, explicit live-session shell; zero physics."""
from pathlib import Path
from types import SimpleNamespace
import pytest
from sludge_sandbox import source_trajectory_record as module


def test_manifest_cleanup_cannot_mask_primary_save_error(monkeypatch,tmp_path):
    session=object.__new__(module.SourceTrajectorySession)
    session._check=lambda:None
    cp=object()
    execution=SimpleNamespace(checkpoint=cp,failure=None)
    session.last_result=SimpleNamespace(status='paused',execution=execution,counts=())
    session.checkpoint=cp;session.last_execution=execution;session.closed=False
    session.parent_directory=tmp_path/'parent'
    session.begin=module.time.monotonic()
    session.last_counts=()
    session.recorder=SimpleNamespace(stop_status=None,undurable_returns=[],notification_failures=[],
        counts={},journal=SimpleNamespace(directory=tmp_path/'original/events'))
    primary=OSError('primary save publication error')
    secondary=OSError('secondary manifest cleanup error')
    def publish(path,value):
        if path.name==module.FINALIZING:raise primary
    original_unlink=Path.unlink
    def unlink(path,*a,**kw):
        if path.name=='manifest.json':raise secondary
        return original_unlink(path,*a,**kw)
    monkeypatch.setattr(module,'_json',publish)
    monkeypatch.setattr(Path,'unlink',unlink)
    actual=None
    try:module.save_source_trajectory(session,tmp_path/'packet')
    except Exception as exc:actual=exc
    (tmp_path/'RESULT.txt').write_text('primary='+repr(primary)+'\nactual='+repr(actual)+'\n')
    assert session.closed and session.checkpoint is None
    assert actual is primary
