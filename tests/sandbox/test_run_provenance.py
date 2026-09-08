"""Declared provenance links must resolve; they do not certify material science."""
import json

import pytest

from sludge_sandbox.run_provenance import ProvenanceError, build_graph, query_graph


def fixture(tmp_path):
    (tmp_path/'implementation').mkdir()
    (tmp_path/'implementation/model.py').write_text('def balance(x):\n    return x\n')
    (tmp_path/'case.json').write_text(json.dumps({'case_id': 'test', 'model_id': 'test',
                                                'solid': {'A': {'value': 2}}}))
    return {'schema': 'sludge_sandbox_equation_catalog_v1', 'model_id': 'test',
        'catalog_id': 'test', 'scope': 'test only', 'graph_semantics': 'declaration',
        'parameter_metadata': {'/solid/A/value': {'symbol': 'N', 'unit': 'mol', 'basis': 'cell inventory',
                                               'classification': 'manufactured_test_fixture'}},
        'result_roots': {'amounts_mol': ['balance']}, 'equations': [{
            'id': 'balance', 'title': 'balance', 'kind': 'balance', 'expression': 'N_new=N_old',
            'symbols': {'N': {'meaning': 'inventory', 'unit': 'mol'}},
            'implemented_at': [{'path': 'implementation/model.py', 'symbol': 'balance'}],
            'case_parameter_pointers': ['/solid/A/value'], 'upstream_equation_ids': [],
            'classification': 'manufactured_test_fixture', 'domain': 'test only', 'omissions': [],
            'sources': [{'kind': 'manufactured_test_fixture', 'artifact': 'case.json',
                         'locator': '/solid/A/value', 'binding': 'active_case_sha256'}]}]}


def test_actual_parameter_and_symbol_are_bound(tmp_path):
    graph = build_graph(tmp_path, fixture(tmp_path))
    trace = query_graph(graph, 'amounts_mol')
    assert any(n.get('value') == 2 for n in trace['nodes'])
    eq = next(n for n in trace['nodes'] if n['id'] == 'equation:balance')
    assert eq['implemented_at'][0]['start_line'] == 1
    assert trace['missing_source_assets'] == []
    assert trace['scientific_validation'] == 'not_established_by_graph'


@pytest.mark.parametrize('defect', ['missing_parameter', 'missing_symbol', 'unknown_dependency', 'cycle', 'escape'])
def test_invalid_declared_dependency_fails(tmp_path, defect):
    catalog = fixture(tmp_path)
    eq = catalog['equations'][0]
    if defect == 'missing_parameter':
        eq['case_parameter_pointers'] = ['/solid/missing']
    elif defect == 'missing_symbol':
        eq['implemented_at'][0]['symbol'] = 'not_present'
    elif defect == 'unknown_dependency':
        eq['upstream_equation_ids'] = ['absent']
    elif defect == 'cycle':
        eq['upstream_equation_ids'] = ['balance']
    else:
        eq['sources'][0]['artifact'] = '../outside'
    with pytest.raises(ProvenanceError):
        build_graph(tmp_path, catalog)


def test_missing_source_is_explicit_not_zero_or_verified(tmp_path):
    catalog = fixture(tmp_path)
    catalog['equations'][0]['sources'] = [{'kind': 'literature_constitutive_model',
        'artifact': 'evidence/unavailable.pdf', 'locator': 'equation 1'}]
    trace = query_graph(build_graph(tmp_path, catalog), 'amounts_mol')
    assert trace['missing_source_assets'] == ['evidence/unavailable.pdf']
    assert trace['source_asset_coverage'] == 0


def test_unknown_result_is_refused(tmp_path):
    graph = build_graph(tmp_path, fixture(tmp_path))
    with pytest.raises(ProvenanceError, match='unsupported_quantity'):
        query_graph(graph, 'strength')


@pytest.mark.parametrize('graph', [[], {}, {'schema': 'sandbox_run_provenance_v1', 'nodes': []}])
def test_malformed_saved_graph_is_structured_error(graph):
    with pytest.raises(ProvenanceError):
        query_graph(graph, 'amounts_mol')


def test_copied_graph_cannot_bind_to_other_implementation(tmp_path):
    import hashlib
    catalog = fixture(tmp_path)
    (tmp_path/'equation_catalog.json').write_text(json.dumps(catalog))
    graph = build_graph(tmp_path, catalog)
    artifacts = {p.relative_to(tmp_path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in tmp_path.rglob('*') if p.is_file()}
    query_graph(graph, 'amounts_mol', artifacts=artifacts)
    artifacts['implementation/model.py'] = 'a'*64
    with pytest.raises(ProvenanceError, match='implementation_artifact_binding_mismatch'):
        query_graph(graph, 'amounts_mol', artifacts=artifacts)


def test_unknown_source_classification_is_rejected(tmp_path):
    catalog = fixture(tmp_path)
    catalog['equations'][0]['sources'][0]['kind'] = 'looks_scientific'
    with pytest.raises(ProvenanceError, match='invalid_source_classification'):
        build_graph(tmp_path, catalog)


def test_evidence_declarations_do_not_depend_on_cwd_symlinks(tmp_path, monkeypatch):
    from sludge_sandbox.run_provenance import evidence_paths
    (tmp_path/'evidence').symlink_to('/private/tmp')
    monkeypatch.chdir(tmp_path)
    catalog = {'supporting_assets': ['evidence/license.txt'], 'equations': []}
    assert evidence_paths(catalog) == ['license.txt']


def test_parameter_units_cannot_silently_default(tmp_path):
    catalog = fixture(tmp_path)
    del catalog['parameter_metadata']['/solid/A/value']['unit']
    with pytest.raises(ProvenanceError):
        build_graph(tmp_path, catalog)
