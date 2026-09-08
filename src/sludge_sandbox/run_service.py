"""Shared application boundary for explicitly manufactured verification cases.

Artifacts bind inputs, implementation and accepted ledgers by content hashes.
These are local integrity records, not signatures or scientific certification.
No deserialization executes saved code. Replay requires the same implementation.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import platform
import time
from typing import Any, Callable


class RunError(ValueError):
    """Invalid, incomplete or incompatible application artifact."""


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(path, value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n'
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(raw, encoding='utf-8')
    temporary.replace(path)


def runtime_identity() -> dict[str, Any]:
    """Fingerprint installed/source Python code without importing EOS libraries."""
    modules = {p.name: _hash(p.read_bytes()) for p in sorted(Path(__file__).parent.glob('*.py'))}
    versions = {}
    for name in ('sludge-vme', 'numpy', 'scipy', 'iapws', 'CoolProp'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    catalogs = {p.name: _hash(p.read_bytes()) for p in sorted((Path(__file__).parent/'catalogs').glob('*.json'))}
    return {'modules': modules, 'catalogs': catalogs, 'versions': versions, 'python': platform.python_version(),
            'platform': platform.platform()}


def _seal(directory):
    files = {p.relative_to(directory).as_posix(): _hash(p.read_bytes())
             for p in sorted(directory.rglob('*')) if p.is_file() and p != directory/'manifest.json'}
    _json(directory/'manifest.json', {'schema': 'sandbox_run_manifest_v1', 'files': files})


def read_run(directory: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify every recorded artifact before returning the saved result."""
    directory = Path(directory)
    try:
        manifest = json.loads((directory/'manifest.json').read_bytes())
        if (not isinstance(manifest, dict) or manifest.get('schema') != 'sandbox_run_manifest_v1'
                or not isinstance(manifest.get('files'), dict) or not manifest['files']):
            raise RunError('invalid_run_manifest')
        for name, expected in manifest['files'].items():
            relative = PurePosixPath(name)
            if (relative.is_absolute() or '..' in relative.parts or '\\' in name
                    or str(relative) != name):
                raise RunError('invalid_artifact_path')
            path = directory/name
            if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                raise RunError('invalid_artifact_path')
            if _hash(path.read_bytes()) != expected:
                raise RunError('artifact_hash_mismatch:'+name)
        actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*')
                  if p.is_file() and p != directory/'manifest.json'}
        if actual != set(manifest['files']):
            raise RunError('unrecorded_run_artifacts')
        if not {'case.json', 'result.json'} <= set(manifest['files']):
            raise RunError('invalid_run_required_artifacts')
        result = json.loads((directory/'result.json').read_bytes())
        if not isinstance(result, dict):
            raise RunError('invalid_run_result')
        if result['case_sha256'] != manifest['files']['case.json']:
            raise RunError('case_binding_mismatch')
        return result, manifest
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RunError('invalid_run') from exc


def run_case(case_path: str | Path, water_directory: str | Path, output: str | Path, *,
             cancel: Callable[[], bool] | None = None,
             replay_of: dict[str, str] | None = None,
             evidence_directory: str | Path | None = None) -> dict[str, Any]:
    """Run once in a fresh directory; retain failures and accepted prefixes.

    Wall/step budgets are explicit case policy. Cancellation is cooperative
    between solver evaluations; it cannot interrupt a native EOS call.
    """
    from .verification_case import read_case, build_case, encode, snapshot

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {'schema': 'sandbox_run_v1', 'status': 'preparing', 'case_sha256': None,
              'scientific_status': 'manufactured_verification_only',
              'material_qualified': False, 'training_eligible': False,
              'runtime_before': runtime_identity(), 'replay_of': replay_of}
    try:
        raw = Path(case_path).read_bytes()
        (output/'case.json').write_bytes(raw)
        result['case_sha256'] = _hash(raw)
        case = read_case(output/'case.json')
        result['case_id'] = case.case_id
        result['scope'] = case.payload['scope']
        (output/'water').mkdir()
        for source in sorted(Path(water_directory).iterdir()):
            if source.is_symlink() or not source.is_file():
                raise RunError('water_directory_requires_regular_files')
            (output/'water'/source.name).write_bytes(source.read_bytes())
        (output/'implementation').mkdir()
        for source in sorted(Path(__file__).parent.glob('*.py')):
            (output/'implementation'/source.name).write_bytes(source.read_bytes())
        from .run_provenance import catalog_bytes, evidence_paths, build_graph
        catalog_raw = catalog_bytes()
        (output/'equation_catalog.json').write_bytes(catalog_raw)
        catalog = json.loads(catalog_raw)
        if evidence_directory is not None:
            evidence_root = Path(evidence_directory).resolve()
            for name in evidence_paths(catalog):
                source = evidence_root/name
                if not source.resolve().is_relative_to(evidence_root) or source.is_symlink():
                    raise RunError('invalid_evidence_artifact_path')
                if source.is_file():
                    destination = output/'evidence'/name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(source.read_bytes())
        _json(output/'provenance.json', build_graph(output, catalog))
        if cancel is not None and cancel():
            result.update(status='cancelled', reason='cancelled_before_build')
        else:
            built = build_case(case, output/'water')
            result.update(initialization=encode(built.initialization), policy=encode(built.policy))
            _json(output/'result.json', result)
            result['initial_snapshot'] = encode(snapshot(built, built.initial, built.start_s))
            _json(output/'result.json', result)
            from .integration import integrate
            run = integrate(built.initial, built.operator, start_s=built.start_s,
                            end_s=built.end_s, policy=built.policy, cancel=cancel,
                            breakpoints_s=built.operator.breakpoints_s(built.start_s, built.end_s))
            result.update(status=run.status, reason=run.reason, integration=encode(run))
            # Persist accepted trajectory before any diagnostic reconstruction.
            _json(output/'result.json', result)
            if run.status == 'completed':
                result['final_snapshot'] = encode(snapshot(built, run.states[-1], run.times_s[-1]))
    except KeyboardInterrupt:
        result.update(status='cancelled', reason='keyboard_interrupt')
    except Exception as exc:
        result.update(status='failed', reason=str(exc), error_type=type(exc).__name__,
                      error_code=getattr(exc, 'code', None))
    finally:
        result['runtime_after'] = runtime_identity()
        if result['runtime_after'] != result['runtime_before']:
            result.update(status='failed', reason='runtime_changed_during_run')
        result['elapsed_seconds'] = time.monotonic()-started
        _json(output/'result.json', result)
        _seal(output)
    return result


_QUANTITIES = {'amounts_mol', 'internal_energy_j', 'temperature_k', 'pressure_pa'}
_EQUATIONS = [
    ('integration.py', 'integrate', 'Conservative cell inventory and energy balance; accepted SSPRK2 quadrature.'),
    ('deforming_solid_storage.py', 'DeformingSolidStorage.temperature_from_total_energy', 'Invert thermal plus skeleton stored energy for temperature; shared pressure closure.'),
    ('deforming_solid_heat.py', 'DeformingSolidHeat.evaluate', 'Recompute geometry, fluid transport, reaction sources and mechanical work from current state.'),
    ('solid_reactions.py', 'SolidReactionConfig.evaluate_cell', 'Stoichiometric sources from declared Arrhenius concentration kinetics.'),
    ('water_phase_transfer.py', 'WaterPhaseTransfer.evaluate', 'Existing-liquid phase transfer using chemical-potential driving force.'),
    ('reacting_skeleton_energy.py', 'ManufacturedReactingSkeletonEnergy.evaluate', 'Manufactured composition-dependent skeleton energy and its derivatives.'),
]


def _leaves(value, pointer=''):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _leaves(item, pointer+'/'+key.replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _leaves(item, pointer+'/'+str(index))
    else:
        yield {'pointer': pointer, 'value': value}


def trace_run(directory: str | Path, quantity: str) -> dict[str, Any]:
    """Frozen dependencies with selected equation navigation anchors."""
    if quantity not in _QUANTITIES:
        raise RunError('unsupported_quantity')
    result, manifest = read_run(directory)
    directory = Path(directory)
    case = json.loads((directory/'case.json').read_bytes())
    if quantity in ('amounts_mol', 'internal_energy_j'):
        try:
            value = result['integration']['states'][-1][quantity]
        except (KeyError, IndexError) as exc:
            raise RunError('quantity_unavailable') from exc
        location = '/integration/states/'+str(len(result['integration']['states'])-1)+'/'+quantity
    else:
        try:
            value = result['final_snapshot'][quantity]
        except KeyError as exc:
            raise RunError('quantity_unavailable') from exc
        location = '/final_snapshot/'+quantity
    equations = []
    for filename, symbol, meaning in _EQUATIONS:
        artifact = 'implementation/'+filename
        if artifact not in manifest['files']:
            raise RunError('equation_artifact_missing')
        equations.append({'artifact': artifact, 'sha256': manifest['files'][artifact],
                          'symbol': symbol, 'meaning': meaning})
    trace = {'quantity': quantity, 'value': value, 'result_pointer': location,
            'result_sha256': manifest['files']['result.json'],
            'case_sha256': result['case_sha256'], 'run_status': result['status'],
            'scientific_status': result['scientific_status'],
            'scope': 'All frozen implementation files and case parameters; equation entries are selected navigation anchors, not a complete equation-level dependency graph or experimental validation.',
            'equations': equations, 'case_parameters': list(_leaves(case)),
            'implementation_artifacts': {k: v for k, v in manifest['files'].items() if k.startswith('implementation/')},
            'evidence_artifacts': {k: v for k, v in manifest['files'].items() if k.startswith('water/')},
            'material_evidence': 'A/B solids, kinetics, carrier, transport and skeleton are manufactured; raw sludge is not admitted.'}
    if 'provenance.json' in manifest['files']:
        from .run_provenance import query_graph
        graph = json.loads((directory/'provenance.json').read_bytes())
        dependency_graph = query_graph(graph, quantity, artifacts=manifest['files'])
        if dependency_graph['case_sha256'] != result['case_sha256']:
            raise RunError('provenance_case_binding_mismatch')
        trace['dependency_graph'] = dependency_graph
        trace['provenance_sha256'] = manifest['files']['provenance.json']
    return trace


def replay_run(directory: str | Path, output: str | Path, *,
               cancel: Callable[[], bool] | None = None) -> dict[str, Any]:
    result, manifest = read_run(directory)
    if result['runtime_before'] != runtime_identity():
        raise RunError('replay_runtime_mismatch')
    return run_case(Path(directory)/'case.json', Path(directory)/'water', output,
                    cancel=cancel, replay_of={'case_sha256': result['case_sha256'],
                    'result_sha256': manifest['files']['result.json']},
                    evidence_directory=Path(directory)/'evidence')
