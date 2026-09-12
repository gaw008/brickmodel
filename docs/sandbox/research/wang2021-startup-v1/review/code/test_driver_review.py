"""Manufactured orchestration failures; no fitting, CSV loading or subprocess."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
REPRODUCE = HERE.parents[1]/'reproduce'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if name == 'review_probe':
        # Relocate only __file__ for archived source so its original imports
        # resolve exactly as when it occupied the production directory.
        module.__file__ = str(REPRODUCE/'probe.py')
    spec.loader.exec_module(module)
    return module


def test_failed_numerical_check_cannot_publish_qualified_readout(monkeypatch, tmp_path):
    target = Path(os.environ.get('PROBE_REVIEW_TARGET', str(REPRODUCE/'probe.py')))
    module = load('review_probe', target)
    old_support = os.environ.get('DRIVER_SUPPORT_REVIEW_TARGET')
    if old_support:
        module.metrics = load('review_old_support', Path(old_support)).metrics
    curves = {(40, 30): [dict(observed=.5, readout_bound=.01, time_s=60.)]}
    x = module.D1_SEED.copy()
    fit = SimpleNamespace(x=x, fun=np.array([.1]), success=True, nfev=1, njev=1,
        message='manufactured', optimality=0., active_mask=np.zeros(3, dtype=int))
    monkeypatch.setattr(module, 'least_squares', lambda *args, **kwargs: fit)
    monkeypatch.setattr(module, 'refinement', lambda *args, **kwargs:
        (dict(accepted=False, fine_delta=.01), np.array([.6])))
    study = module.Study(curves, tmp_path, time.monotonic())
    study.cells = 64
    with pytest.raises(ValueError, match='numerical comparison failed'):
        study.fit(x, 600., 'manufactured')
    record = json.loads((tmp_path/'study.json').read_text())
    assert record['profiles'][0]['status'] == 'failed'
    path = tmp_path/'manufactured-training.json'
    if path.exists():
        report = json.loads(path.read_text())
        assert report['numerical_check_passed'] is False
        assert report.get('numerical_allowance') is None
        assert report['overall'].get('outside_count') is None
        for point in report['points']:
            assert point.get('exceeds_readout_plus_numeric') is None


def test_missing_input_after_child_exit_preserves_terminal_record(monkeypatch, tmp_path):
    target = Path(os.environ.get('SUPERVISE_REVIEW_TARGET', str(REPRODUCE/'supervise.py')))
    module = load('review_supervise', target)
    # Keep production path resolution but replace child execution completely.
    module.__file__ = str(REPRODUCE/'supervise.py')
    csv = tmp_path/'manufactured.csv'
    csv.write_text('not read by any data loader\n')
    output = tmp_path/'supervised'

    def fake_child(*args, **kwargs):
        csv.unlink()
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(module.subprocess, 'run', fake_child)
    monkeypatch.setattr(sys, 'argv', ['supervise', '--csv', str(csv), '--output', str(output)])
    try:
        result = module.main()
    except FileNotFoundError:
        result = None
    path = output/'supervisor-end.json'
    assert path.exists(), 'actual child terminal status must survive a post-run input binding failure'
    record = json.loads(path.read_text())
    assert result == 1
    assert record['returncode'] == 7
    assert record['child_reaped'] is True
    assert record['inputs_unchanged'] is False
