"""Expand only the frozen manifest, preserving full numeric JSON identities."""
from copy import deepcopy
import json
from model import ROOT, Scenario


def matrix():
    return json.loads((ROOT / 'B2_ACCEPTANCE_MATRIX.json').read_text(encoding='utf-8'))


def expand_frozen_manifest(document=None):
    m = (document or matrix())['scenario_manifest']
    result = []
    for run in m['runs']:
        d = deepcopy(m['defaults']); bundle = m['bundles'][run['bundle_id']]
        d['scenario_id'] = run['scenario_id']
        d['temperature']['knots'] = deepcopy(m['programs'][run['program_id']])
        for k in ('K_ref','theta'): d['reaction'][k] = bundle[k]
        for k in ('d_ref','m'): d['transport'][k] = bundle[k]
        d['reaction']['Gamma'] = run['Gamma']
        d['geometry']['length_ratio'] = run['length_ratio']
        d['boundary'] = {'mode':run['boundary_mode'],'reservoir_ratio':run['reservoir_ratio']}
        if run['K_ref_override'] is not None: d['reaction']['K_ref'] = run['K_ref_override']
        if run['Bi_ref_override'] is not None: d['transport']['Bi_ref'] = run['Bi_ref_override']
        result.append(Scenario.from_dict(d))
    return result
