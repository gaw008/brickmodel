"""Closed data admission and process isolation; no native physics in these tests."""
import json
from copy import deepcopy

import pytest

from sludge_sandbox.source_managed_worker import _load_request, _require_isolated_entry


def request():
    return dict(schema='source_rhs_request_v1', execution_mode='managed_single_rhs_v1',
        case_path='/tmp/case.json', assets_root='/tmp/assets', output='/tmp/result',
        amounts_mol=[[.25, .1, .2, .001], [0., .1, .2, .001], [.25, .1, .2, .001]],
        internal_energy_j=[10., 20., 30.], time={'numerator': 1, 'denominator': 64},
        interface_modes=['existing_liquid', 'depleted_no_nucleation', 'existing_liquid'],
        origin={'kind': 'saved_numerical_query_not_resume', 'sha256': 'a' * 64},
        timeout_seconds=120., material_qualified=False)


def test_query_preserves_exact_numbers_and_declares_scope():
    raw = request()
    decoded = _load_request(json.dumps(raw).encode())
    assert decoded == raw
    assert type(decoded['amounts_mol'][1][0]) is float
    assert decoded['material_qualified'] is False
    assert decoded['origin']['kind'] == 'saved_numerical_query_not_resume'


@pytest.mark.parametrize('path,value', [
    (('amounts_mol', 1, 0), 1e-20), (('amounts_mol', 0, 0), True),
    (('amounts_mol', 0, 1), -1.), (('internal_energy_j', 0), float('nan')),
    (('time', 'denominator'), 0), (('time', 'numerator'), True),
    (('time', 'numerator'), -1), (('time', 'denominator'), 10**101),
    (('interface_modes', 1), 'invented'), (('material_qualified',), True),
    (('execution_mode',), 'arbitrary_python'), (('timeout_seconds',), 121.),
    (('case_path',), 'relative.json'), (('origin', 'sha256'), 'x' * 64),
])
def test_invalid_query_is_rejected_before_construction(path, value):
    raw = deepcopy(request())
    target = raw
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        _load_request(json.dumps(raw).encode())


@pytest.mark.parametrize('raw', [b'{}', b' ' * 65537,
    b'{"schema":"a","schema":"b"}', b'{"callable":"os.system"}'])
def test_closed_bounded_json(raw):
    with pytest.raises(ValueError):
        _load_request(raw)


def test_imported_in_process_call_cannot_claim_isolation():
    with pytest.raises(RuntimeError, match='isolated_module_process_required'):
        _require_isolated_entry()
