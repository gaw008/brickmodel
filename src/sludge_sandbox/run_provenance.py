"""Instantiate equation declarations against frozen run inputs and source code.

Edges describe the calculation at a given stage and the subsequent update, not
a claim that physical feedback is acyclic. Equations are documentation strings;
this module never evaluates an expression or imports saved implementation code.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from .evidence import KINDS


class ProvenanceError(ValueError):
    """A declared provenance link cannot be interpreted or resolved."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProvenanceError(message)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _lexical(name: str) -> None:
    _require(isinstance(name, str) and bool(name), 'invalid_artifact_path')
    relative = PurePosixPath(name)
    _require(not relative.is_absolute() and '..' not in relative.parts and
             '\\' not in name and str(relative) == name, 'invalid_artifact_path')


def _path(directory: Path, name: str) -> Path:
    _lexical(name)
    path = directory/name
    _require(not path.is_symlink() and path.resolve().is_relative_to(directory.resolve()),
             'invalid_artifact_path')
    return path


def _pointer(payload: Any, pointer: str) -> Any:
    _require(isinstance(pointer, str) and pointer.startswith('/'), 'invalid_parameter_pointer')
    value = payload
    try:
        for token in pointer[1:].split('/'):
            key = token.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                _require(key.isdecimal() and str(int(key)) == key, 'invalid_array_pointer')
                value = value[int(key)]
            else:
                value = value[key]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProvenanceError('unresolved_parameter:'+pointer) from exc
    return deepcopy(value)


def _anchor(directory: Path, entry: dict[str, str]) -> dict[str, Any]:
    _require(isinstance(entry, dict) and isinstance(entry.get('symbol'), str)
             and bool(entry['symbol']), 'invalid_implementation_symbol')
    path = _path(directory, entry['path'])
    _require(entry['path'].startswith('implementation/'), 'invalid_implementation_artifact')
    raw = path.read_bytes()
    tree = ast.parse(raw)
    body = tree.body
    found = None
    for component in entry['symbol'].split('.'):
        matches = [node for node in body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                   and node.name == component]
        _require(len(matches) == 1, 'unresolved_implementation_symbol:'+entry['symbol'])
        found = matches[0]
        body = found.body
    _require(found is not None, 'empty_implementation_symbol')
    return {**entry, 'sha256': _sha(raw), 'start_line': found.lineno, 'end_line': found.end_lineno}


LEGACY_MODEL_ID = 'manufactured_reacting_wet_prescribed_slab_v1'


def catalog_filename(model_id: str = LEGACY_MODEL_ID, *, case_schema: str | None = None) -> str:
    """Resolve only explicitly supported models to fixed packaged filenames."""
    if case_schema == 'sludge_sandbox_free_event_case_v1':
        _require(model_id == 'manufactured_reacting_wet_free_slab_v1', 'unsupported_catalog_model')
        return 'free-wet-event-slab-equations-v1.json'
    _require(case_schema in (None, 'sludge_sandbox_verification_case_v1'), 'unsupported_catalog_case_schema')
    names = {
        LEGACY_MODEL_ID: 'wet-slab-equations-v1.json',
        'manufactured_reacting_wet_free_slab_v1': 'free-wet-slab-equations-v1.json',
    }
    _require(isinstance(model_id, str) and model_id in names, 'unsupported_catalog_model')
    return names[model_id]


def load_catalog(model_id: str = LEGACY_MODEL_ID, *, case_schema: str | None = None) -> dict[str, Any]:
    """Installed package resource, kept independent of the working directory."""
    return json.loads(catalog_bytes(model_id, case_schema=case_schema))


def catalog_bytes(model_id: str = LEGACY_MODEL_ID, *, case_schema: str | None = None) -> bytes:
    raw = (Path(__file__).parent/'catalogs'/catalog_filename(model_id, case_schema=case_schema)).read_bytes()
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ProvenanceError('invalid_catalog_json') from exc
    _require(isinstance(payload, dict) and payload.get('model_id') == model_id,
             'catalog_model_mismatch')
    expected_schema = case_schema or 'sludge_sandbox_verification_case_v1'
    _require(payload.get('case_schema', 'sludge_sandbox_verification_case_v1') == expected_schema,
             'catalog_case_schema_mismatch')
    return raw


def evidence_paths(catalog: dict[str, Any]) -> list[str]:
    paths = set(catalog.get('supporting_assets', []))
    for equation in catalog['equations']:
        for source in equation['sources']:
            name = source['artifact']
            paths.add(name)
    for name in paths:
        _lexical(name)
    return sorted(name[len('evidence/'):] for name in paths if name.startswith('evidence/'))


def build_graph(directory: str | Path, catalog: dict[str, Any]) -> dict[str, Any]:
    """Check a declared DAG and bind its parameters, code and source positions.

    Missing source assets remain explicit leaf nodes. This is useful for a
    manufactured verification run; it does not permit real-material admission.
    Source locators are declarations except JSON pointers, which are resolved.
    """
    directory = Path(directory)
    try:
        _require(catalog['schema'] == 'sludge_sandbox_equation_catalog_v1', 'unsupported_catalog')
        case_raw = (directory/'case.json').read_bytes()
        case = json.loads(case_raw)
        _require(case['model_id'] == catalog['model_id'], 'catalog_model_mismatch')
        # Old ad-hoc graphs can omit schema; event cases require explicit binding.
        expected_schema = catalog.get('case_schema', 'sludge_sandbox_verification_case_v1')
        _require(case.get('schema', 'sludge_sandbox_verification_case_v1') == expected_schema,
                 'catalog_case_schema_mismatch')
        case_sha = _sha(case_raw)
        nodes: dict[str, dict[str, Any]] = {}
        for equation in catalog['equations']:
            identifier = 'equation:'+equation['id']
            _require(identifier not in nodes, 'duplicate_equation_id')
            _require(equation['classification'] in KINDS, 'invalid_equation_classification')
            for name in ('expression', 'title'):
                _require(isinstance(equation[name], str) and bool(equation[name].strip()), 'invalid_'+name)
            _require(bool(equation['implemented_at']) and bool(equation['sources']), 'missing_equation_evidence')
            dependencies = ['equation:'+dep for dep in equation['upstream_equation_ids']]
            for pointer in equation['case_parameter_pointers']:
                parameter_id = 'parameter:'+pointer
                metadata = catalog.get('parameter_metadata', {}).get(pointer)
                _require(isinstance(metadata, dict), 'missing_parameter_metadata:'+pointer)
                _require(metadata['classification'] in KINDS, 'invalid_parameter_classification')
                for field in ('symbol', 'unit', 'basis'):
                    _require(isinstance(metadata[field], str) and bool(metadata[field].strip()),
                             'missing_parameter_'+field)
                nodes[parameter_id] = {'id': parameter_id, 'node_type': 'parameter',
                    'classification': metadata['classification'],
                    'metadata': deepcopy(metadata), 'metadata_status': 'declared',
                    'value': _pointer(case, pointer),
                    'artifact': 'case.json', 'pointer': pointer, 'sha256': case_sha, 'depends_on': [],
                    'qualification': 'Input and unit/basis declaration; source applicability is not certified by this case value.'}
                dependencies.append(parameter_id)
            for index, declaration in enumerate(equation['sources']):
                source = deepcopy(declaration)
                _require(source['kind'] in KINDS, 'invalid_source_classification')
                artifact = source['artifact']
                path = _path(directory, artifact)
                _require(isinstance(source['locator'], str) and bool(source['locator']), 'missing_source_locator')
                source_id = 'source:'+equation['id']+':'+str(index)
                available = path.is_file()
                source.update(id=source_id, node_type='source', depends_on=[],
                              availability='present' if available else 'missing',
                              scientific_validation='not_established_by_graph')
                if available:
                    raw = path.read_bytes()
                    source['sha256'] = _sha(raw)
                    if source['locator'].startswith('/') and path.suffix == '.json':
                        source['located_value'] = _pointer(json.loads(raw), source['locator'])
                        source['locator_check'] = 'json_pointer_resolved'
                    else:
                        source['locator_check'] = 'declared_position_not_machine_verified'
                else:
                    source.update(sha256=None, locator_check='source_asset_missing')
                if source.get('binding') == 'active_case_sha256':
                    _require(artifact == 'case.json', 'invalid_case_source_binding')
                    source['bound_case_sha256'] = case_sha
                nodes[source_id] = source
                dependencies.append(source_id)
            nodes[identifier] = {**deepcopy(equation), 'id': identifier, 'node_type': 'equation',
                'implemented_at': [_anchor(directory, entry) for entry in equation['implemented_at']],
                'depends_on': dependencies}
        roots = {}
        for quantity, equations in catalog['result_roots'].items():
            root = 'result:'+quantity
            nodes[root] = {'id': root, 'node_type': 'output', 'quantity': quantity,
                           'depends_on': ['equation:'+item for item in equations]}
            roots[quantity] = root
        graph = {'schema': 'sandbox_run_provenance_v1', 'model_id': catalog['model_id'],
                 'catalog_id': catalog['catalog_id'], 'case_sha256': case_sha,
                 'scope': catalog['scope'], 'graph_semantics': catalog['graph_semantics'],
                 'nodes': list(nodes.values()), 'result_roots': roots,
                 'scientific_validation': 'not_established_by_graph', 'material_qualified': False}
        catalog_path = directory/'equation_catalog.json'
        if catalog_path.is_file():
            raw = catalog_path.read_bytes()
            _require(json.loads(raw) == catalog, 'catalog_payload_mismatch')
            graph['catalog_sha256'] = _sha(raw)
        else:
            graph['catalog_sha256'] = None
        # Validate disconnected declarations too; omissions cannot hide a cycle.
        _ordered({node['id']: node for node in graph['nodes']}, list(nodes))
        return graph
    except ProvenanceError:
        raise
    except (OSError, KeyError, TypeError, ValueError, SyntaxError) as exc:
        raise ProvenanceError('invalid_provenance_declaration:'+str(exc)) from exc


def _ordered(nodes: dict[str, dict[str, Any]], roots: list[str]) -> list[str]:
    ordered, visiting, done = [], set(), set()

    def visit(identifier: str) -> None:
        _require(identifier in nodes, 'unresolved_dependency:'+identifier)
        _require(identifier not in visiting, 'cyclic_provenance')
        if identifier in done:
            return
        visiting.add(identifier)
        for upstream in nodes[identifier]['depends_on']:
            visit(upstream)
        visiting.remove(identifier)
        done.add(identifier)
        ordered.append(identifier)

    for root in roots:
        visit(root)
    return ordered


def query_graph(graph: dict[str, Any], quantity: str, *,
                artifacts: dict[str, str] | None = None) -> dict[str, Any]:
    """Return only declared ancestors of a saved output, in dependency order."""
    try:
        _require(isinstance(graph, dict) and graph.get('schema') == 'sandbox_run_provenance_v1', 'invalid_graph_schema')
        _require(isinstance(graph['result_roots'], dict) and isinstance(graph['nodes'], list), 'invalid_graph_containers')
        _require(quantity in graph['result_roots'], 'unsupported_quantity')
        nodes = {node['id']: node for node in graph['nodes']}
        _require(len(nodes) == len(graph['nodes']), 'duplicate_graph_node')
        for node in nodes.values():
            _require(isinstance(node['id'], str) and isinstance(node['depends_on'], list)
                     and all(isinstance(dep, str) for dep in node['depends_on']), 'invalid_graph_node')
            _require(node['node_type'] in ('equation', 'source', 'parameter', 'output'), 'invalid_graph_node_type')
            if node['node_type'] == 'source':
                _require(node['availability'] in ('present', 'missing') and node['kind'] in KINDS,
                         'invalid_graph_source')
                _lexical(node['artifact'])
        _require('scope' in graph and 'graph_semantics' in graph, 'missing_graph_scope')
        _require(isinstance(graph['case_sha256'], str) and len(graph['case_sha256']) == 64,
                 'invalid_graph_case_binding')
        _ordered(nodes, list(nodes))
        ancestors = [nodes[key] for key in _ordered(nodes, [graph['result_roots'][quantity]])]
        if artifacts is not None:
            _require(graph['catalog_sha256'] == artifacts.get('equation_catalog.json')
                     and graph['catalog_sha256'] is not None, 'catalog_artifact_binding_mismatch')
            for node in ancestors:
                if node['node_type'] == 'equation':
                    for anchor in node['implemented_at']:
                        _require(anchor['sha256'] == artifacts.get(anchor['path']), 'implementation_artifact_binding_mismatch')
                elif node['node_type'] in ('parameter', 'source'):
                    if node.get('availability') == 'missing':
                        _require(node['artifact'] not in artifacts, 'source_availability_binding_mismatch')
                    else:
                        _require(node['sha256'] == artifacts.get(node['artifact'])
                                 and node['sha256'] is not None, 'source_artifact_binding_mismatch')
    except ProvenanceError:
        raise
    except (KeyError, TypeError, AttributeError, ValueError, RecursionError) as exc:
        raise ProvenanceError('invalid_saved_graph:'+str(exc)) from exc
    sources = [node for node in ancestors if node['node_type'] == 'source']
    missing = sorted({node['artifact'] for node in sources if node['availability'] != 'present'})
    return {'quantity': quantity, 'case_sha256': graph['case_sha256'], 'nodes': deepcopy(ancestors),
            'missing_source_assets': missing,
            'source_asset_coverage': sum(node['availability'] == 'present' for node in sources)/len(sources) if sources else None,
            'coverage_meaning': 'Fraction of declared source-position nodes with readable local assets; not evidence applicability, physical-parameter coverage or external validation.',
            'scientific_validation': 'not_established_by_graph', 'material_qualified': False,
            'scope': graph['scope'], 'graph_semantics': graph['graph_semantics']}
