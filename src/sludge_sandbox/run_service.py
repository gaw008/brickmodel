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
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .checkpoint import ResumePrefix


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
        from .exact_run_service import verify_exact_artifacts
        verify_exact_artifacts(directory,result,manifest)
        from .source_run_service import verify_source_artifacts
        verify_source_artifacts(directory,result,manifest)
        return result, manifest
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RunError('invalid_run') from exc


def export_run(directory: str | Path) -> dict[str, Any]:
    """Export verified results; exact canonical JSON stays a lossless text field."""
    directory=Path(directory)
    result,manifest=read_run(directory)
    exported={'result':result,'manifest':manifest}
    from .exact_run_service import KIND,RECORD
    if result.get('integration_kind')==KIND and result.get('exact_record') is not None:
        raw=(directory/RECORD).read_bytes()
        if _hash(raw)!=manifest['files'][RECORD]:raise RunError('exact_export_changed_after_validation')
        exported['canonical_exact_record']={'artifact':RECORD,'sha256':_hash(raw),
            'encoding':'utf-8 JSON text; preserve string without parsing numeric fields','text':raw.decode('utf-8')}
        exported['export_scope']='Verified canonical numerical record plus result and manifest; referenced input/source files are not bundled. This is not a standalone replay directory.'
    from .source_run_service import KIND as SOURCE_KIND, RECORD as SOURCE_RECORD
    if result.get('integration_kind') == SOURCE_KIND and result.get('source_record') is not None:
        raw = (directory / SOURCE_RECORD).read_bytes()
        if _hash(raw) != manifest['files'][SOURCE_RECORD]:
            raise RunError('source_export_changed_after_validation')
        exported['canonical_source_record'] = {'artifact': SOURCE_RECORD, 'sha256': _hash(raw),
            'encoding': 'utf-8 JSON text; preserve exact numeric fields', 'text': raw.decode('utf-8')}
        exported['export_scope'] = 'Complete passive study plus result and manifest; private assets and event files are not bundled. Not a standalone replay directory.'
    return exported


_EVENT_SCHEMA = 'sludge_sandbox_free_event_case_v1'
_EXACT_EVENT_SCHEMA = 'sludge_sandbox_free_exact_event_case_v1'
_EVENT_SCHEMAS = (_EVENT_SCHEMA,_EXACT_EVENT_SCHEMA)


def _event_cancelled(parent: dict[str, Any]) -> None:
    record = parent.get('integration')
    if (parent.get('integration_kind') != 'water_depletion_v1'
            or parent.get('status') != 'cancelled' or type(record) is not dict
            or record.get('schema') not in ('sandbox_depletion_result_v1','sandbox_depletion_result_v2')
            or record.get('status') != 'cancelled' or record.get('reason') != 'cancel_requested'
            or not record.get('steps')):
        raise RunError('resume_requires_cancelled_event_prefix')


def _run_event(built, result: dict[str, Any], parent: dict[str, Any] | None,
               output: Path, cancel: Callable[[], bool] | None) -> None:
    """Adapt complete event evidence without flattening it into ordinary ledgers."""
    from dataclasses import replace
    from .checkpoint import exact_state_equal
    from .depletion_integration import integrate_depletion
    from .event_record import (audit_depletion_record, encode_depletion_result,
                               restore_final_operator, state)
    from .verification_case import encode, snapshot
    result['integration_kind'] = 'water_depletion_v1'
    event_policy = built.depletion_policy
    if event_policy is None:
        raise RunError('event_case_requires_explicit_policy')
    if getattr(event_policy, 'ordered_event_policy', None) is not None:
        raise RunError('ordered_packet_service_codec_unavailable')
    result['depletion_policy'] = encode(event_policy)
    initial, start, operator = built.initial, built.start_s, built.operator
    original_interfaces = tuple(operator.interfaces)
    continuation = None
    boundary = None
    if parent is None:
        result['initial_snapshot'] = encode(snapshot(built, initial, start))
    else:
        _event_cancelled(parent)
        if parent.get('policy') != encode(built.policy) or parent.get('depletion_policy') != encode(event_policy):
            raise RunError('resume_event_original_policy_mismatch')
        record = parent['integration']
        if not exact_state_equal(state(record['states'][0]), built.initial):
            raise RunError('resume_live_initial_mismatch')
        if not exact_state_equal(state(parent['initial_snapshot']['state']), built.initial):
            raise RunError('resume_initial_snapshot_binding_mismatch')
        # Source/case/runtime/manifest checks precede this point. Reconstruct
        # actual modes from the freshly built original operator, never saved code.
        operator = restore_final_operator(built.operator, record)
        continuation = audit_depletion_record(record, built.initial, built.policy, event_policy,
            original_interfaces, operator=operator, start_s=built.start_s, end_s=built.end_s)
        restored = continuation.restore_result(operator)
        initial, start = restored.states[-1], restored.times_s[-1]
        if start >= built.end_s:
            raise RunError('resume_requires_interior_event_prefix')
        boundary = {key:len(record[key]) for key in ('times_s','states','steps','events','corrections','refinements')}
        boundary.update(schema='sandbox_depletion_continuation_boundary_v1',
            checkpoint_time_s=start, semantics='Core returns complete cumulative history; counts mark historical prefix, not a locally accepted suffix.',
            prior_attempted_steps=restored.attempted_steps, prior_evaluations=restored.evaluations,
            prior_rejected_trials=restored.rejected_trials, prior_elapsed_seconds=restored.elapsed_seconds)
        result['continuation_boundary'] = boundary
        result['checkpoint_snapshot'] = encode(snapshot(replace(built,operator=operator), initial, start))
    _json(output/'result.json', result)
    run = integrate_depletion(initial, operator, start_s=start, end_s=built.end_s,
        integration_policy=built.policy, event_policy=event_policy, cancel=cancel, continuation=continuation)
    record = encode_depletion_result(run, original_interfaces=original_interfaces)
    # This raw complete result survives audit or diagnostic failure. It is not
    # mislabeled as a suffix and cannot be merged a second time.
    _json(output/'depletion_result.json', record)
    audit_depletion_record(record,built.initial,built.policy,event_policy,original_interfaces,
        operator=run.operator,start_s=built.start_s,end_s=built.end_s)
    result.update(status=run.status, reason=run.reason, integration=record)
    _json(output/'result.json', result)
    if run.status == 'completed':
        result['final_snapshot'] = encode(snapshot(replace(built,operator=run.operator), run.states[-1],run.times_s[-1]))


def run_case(case_path: str | Path, water_directory: str | Path, output: str | Path, *,
             cancel: Callable[[], bool] | None = None,
             replay_of: dict[str, str] | None = None,
             evidence_directory: str | Path | None = None,
             _resume: ResumePrefix | None = None,
             _event_replay: ResumePrefix | None = None,
             _exact_on_commit: Callable | None = None) -> dict[str, Any]:
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
        if case.payload['schema']==_EXACT_EVENT_SCHEMA:
            from .exact_run_service import KIND
            result.update(integration_kind=KIND,integration=None)
        if _event_replay is not None:
            from .checkpoint import ResumePrefix
            from .exact_run_service import ExactParent
            if type(_event_replay) not in (ResumePrefix,ExactParent) or _resume is not None or case.payload['schema'] not in _EVENT_SCHEMAS:
                raise RunError('invalid_private_event_replay_record')
            replay_parent=_event_replay.result()
            if (replay_parent['case_sha256']!=result['case_sha256'] or
                    replay_parent['runtime_before']!=result['runtime_before'] or
                    replay_parent['runtime_after']!=result['runtime_before']):
                raise RunError('replay_parent_binding_mismatch')
            (output/'replay_parent').mkdir()
            (output/'replay_parent/result.json').write_bytes(_event_replay.parent_result_raw)
            (output/'replay_parent/manifest.json').write_bytes(_event_replay.parent_manifest_raw)
            if case.payload['schema']==_EXACT_EVENT_SCHEMA:
                if type(_event_replay) is not ExactParent:raise RunError('exact_replay_record_required')
                (output/'replay_parent/exact-run-record.json').write_bytes(_event_replay.parent_exact_raw)
        if _resume is not None:
            from .checkpoint import ResumePrefix
            if not isinstance(_resume, ResumePrefix):
                raise RunError('invalid_private_resume_record')
            parent = _resume.result()
            if (parent['case_sha256'] != result['case_sha256'] or
                    parent['runtime_before'] != result['runtime_before'] or
                    parent['runtime_after'] != result['runtime_before']):
                raise RunError('resume_parent_binding_mismatch')
            (output/'parent').mkdir()
            (output/'parent/result.json').write_bytes(_resume.parent_result_raw)
            (output/'parent/manifest.json').write_bytes(_resume.parent_manifest_raw)
            if case.payload['schema']==_EXACT_EVENT_SCHEMA:
                from .exact_run_service import ExactParent
                if type(_resume) is not ExactParent:raise RunError('exact_resume_record_required')
                (output/'parent/exact-run-record.json').write_bytes(_resume.parent_exact_raw)
            result['resume_of'] = {
                'result_sha256': _resume.parent_result_sha256,
                'manifest_sha256': _resume.parent_manifest_sha256,
                'case_sha256': parent['case_sha256'],
                'historical_artifacts': 'parent/result.json and parent/manifest.json preserve historical evidence; parent/ is not a standalone run bundle.',
                'adaptive_restart': 'Original initial_step_s restarts the adaptive controller and exact nominal clock at the last accepted absolute time. The continuation is not claimed bit-identical to an uninterrupted adaptive solve.',
                'wall_scope': 'Remaining original integrate-only wall budget; rebuilding and diagnostics are reported separately by service elapsed_seconds.'}
            result['policy'] = parent['policy']
            result['initialization'] = parent.get('initialization')
            result['initial_snapshot'] = parent['initial_snapshot']
            # Exact parent history remains historical until a child canonical record exists.
            result['integration'] = (None if case.payload['schema']==_EXACT_EVENT_SCHEMA
                                     else parent['integration'])
        (output/'water').mkdir()
        for source in sorted(Path(water_directory).iterdir()):
            if source.is_symlink() or not source.is_file():
                raise RunError('water_directory_requires_regular_files')
            (output/'water'/source.name).write_bytes(source.read_bytes())
        (output/'implementation').mkdir()
        for source in sorted(Path(__file__).parent.glob('*.py')):
            (output/'implementation'/source.name).write_bytes(source.read_bytes())
        from .run_provenance import catalog_bytes, evidence_paths, build_graph
        catalog_raw = (catalog_bytes(case.payload['model_id'],case_schema=case.payload['schema'])
            if case.payload['schema'] in _EVENT_SCHEMAS else catalog_bytes(case.payload['model_id']))
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
        input_parent = _resume if _resume is not None else _event_replay
        if input_parent is not None:
            if (_hash(input_parent.parent_result_raw)!=input_parent.parent_result_sha256 or
                    _hash(input_parent.parent_manifest_raw)!=input_parent.parent_manifest_sha256):
                raise RunError('private_parent_bytes_mismatch')
            parent_files = json.loads(input_parent.parent_manifest_raw)['files']
            if parent_files.get('result.json')!=input_parent.parent_result_sha256:
                raise RunError('private_parent_manifest_result_mismatch')
            for name, digest in parent_files.items():
                if name.startswith(('water/', 'evidence/', 'implementation/')) or name in ('case.json', 'equation_catalog.json'):
                    copied = output/name
                    if not copied.is_file() or _hash(copied.read_bytes()) != digest:
                        raise RunError('resume_copied_source_binding_mismatch:'+name)
            copied_inputs = {p.relative_to(output).as_posix() for root in ('water', 'evidence', 'implementation')
                             for p in (output/root).rglob('*') if p.is_file()}
            expected_inputs = {name for name in parent_files if name.startswith(('water/', 'evidence/', 'implementation/'))}
            if copied_inputs != expected_inputs:
                raise RunError('resume_copied_source_membership_mismatch')
        if cancel is not None and cancel():
            result.update(status='cancelled', reason='cancelled_before_build')
        else:
            built = build_case(case, output/'water')
            result.update(initialization=encode(built.initialization), policy=encode(built.policy))
            _json(output/'result.json', result)
            if case.payload['schema'] == _EXACT_EVENT_SCHEMA:
                from .exact_run_service import run_exact_event
                run_exact_event(built,result,_resume,output,cancel,replay_parent=_event_replay,on_commit=_exact_on_commit)
            elif case.payload['schema'] == _EVENT_SCHEMA:
                if _event_replay is not None:
                    from .checkpoint import exact_state_equal
                    from .event_record import state
                    if (replay_parent.get('policy')!=encode(built.policy) or
                            replay_parent.get('depletion_policy')!=encode(built.depletion_policy)):
                        raise RunError('replay_original_policy_mismatch')
                    if not exact_state_equal(state(replay_parent['initial_snapshot']['state']),built.initial):
                        raise RunError('replay_live_initial_mismatch')
                _run_event(built, result, parent if _resume is not None else None, output, cancel)
            else:
                if _resume is None:
                    initial = built.initial
                    start_s = built.start_s
                    policy = built.policy
                    result['initial_snapshot'] = encode(snapshot(built, built.initial, built.start_s))
                else:
                    from .checkpoint import validate_cancelled, exact_state_equal, remaining_policy
                    from .integration import IntegrationPolicy
                    if encode(IntegrationPolicy(**parent['policy'])) != encode(built.policy):
                        raise RunError('resume_policy_mismatch')
                    prefix = validate_cancelled(parent, built.policy, start_s=built.start_s, end_s=built.end_s)
                    if not exact_state_equal(prefix.states[0], built.initial):
                        raise RunError('resume_live_initial_mismatch')
                    if prefix.states[-1].energy_model_identity != built.initial.energy_model_identity:
                        raise RunError('resume_live_energy_binding_mismatch')
                    initial, start_s = prefix.states[-1], prefix.times_s[-1]
                    policy = remaining_policy(parent['integration'], built.policy)
                    result['suffix_policy'] = encode(policy)
                    result['checkpoint_snapshot'] = encode(snapshot(built, initial, start_s))
                _json(output/'result.json', result)
                from .integration import integrate
                run = integrate(initial, built.operator, start_s=start_s,
                                end_s=built.end_s, policy=policy, cancel=cancel,
                                breakpoints_s=built.operator.breakpoints_s(start_s, built.end_s))
                if _resume is None:
                    result.update(status=run.status, reason=run.reason, integration=encode(run))
                else:
                    # Raw locally accepted suffix is evidence, not yet service acceptance.
                    suffix = encode(run)
                    _json(output/'resume_suffix.json', suffix)
                    from .checkpoint import merge_integration
                    merged, audit = merge_integration(parent['integration'], suffix, built.policy,
                                                      start_s=built.start_s, end_s=built.end_s)
                    result.update(status=merged['status'], reason=merged['reason'],
                                  integration=merged, resume_ledger_audit=audit)
                # Persist accepted trajectory before any diagnostic reconstruction.
                _json(output/'result.json', result)
                if result['status'] == 'completed':
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
_FREE_QUANTITIES = _QUANTITIES | {'mechanical_stretches', 'geometry', 'free'}
_EQUATIONS = [
    ('integration.py', 'integrate', 'Conservative cell inventory and energy balance; accepted SSPRK2 quadrature.'),
    ('deforming_solid_storage.py', 'DeformingSolidStorage.temperature_from_total_energy', 'Invert thermal plus skeleton stored energy for temperature; shared pressure closure.'),
    ('deforming_solid_heat.py', 'DeformingSolidHeat.evaluate', 'Recompute geometry, fluid transport, reaction sources and mechanical work from current state.'),
    ('solid_reactions.py', 'SolidReactionConfig.evaluate_cell', 'Stoichiometric sources from declared Arrhenius concentration kinetics.'),
    ('water_phase_transfer.py', 'WaterPhaseTransfer.evaluate', 'Existing-liquid phase transfer using chemical-potential driving force.'),
    ('reacting_skeleton_energy.py', 'ManufacturedReactingSkeletonEnergy.evaluate', 'Manufactured composition-dependent skeleton energy and its derivatives.'),
]

_FREE_EQUATIONS = [
    _EQUATIONS[0],
    ('current_solid_storage.py', 'CurrentSolidStorage.temperature_from_total_energy', 'Invert current-composition thermal plus recoverable energy at actual free geometry.'),
    ('free_solid_slab.py', 'FreeSolidSlab.evaluate', 'Decode current cells and jointly assemble transport, free mechanics and local constraint power.'),
    ('free_slab_rates.py', 'solve_free_slab_rates', 'Solve cell normal rates and common tangent rate with current composition-scaled viscosity; preserve local constraint power.'),
    *_EQUATIONS[3:],
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
    if quantity not in _FREE_QUANTITIES:
        raise RunError('unsupported_quantity')
    result, manifest = read_run(directory)
    directory = Path(directory)
    case = json.loads((directory/'case.json').read_bytes())
    model = case.get('model_id') if isinstance(case, dict) else None
    if model == 'manufactured_reacting_wet_prescribed_slab_v1':
        anchors = _EQUATIONS
        if quantity not in _QUANTITIES:
            raise RunError('unsupported_quantity')
    elif model == 'manufactured_reacting_wet_free_slab_v1':
        anchors = _FREE_EQUATIONS
        if case.get('schema')==_EXACT_EVENT_SCHEMA:
            anchors=[('exact_depletion_integration.py','integrate_exact_depletion','Exact rational stage clocks, original full-history event acceptance and budgets.'),
                ('exact_terminal_executor.py','execute_exact_terminal','Source-bound exact ordered terminal evaluation and correction.'),
                ('exact_record_audit.py','audit_exact_run','Original-prefix conservation audit.'),
                ('exact_terminal_proof_audit.py','audit_committed_terminal_proofs','All-candidate root, panel and correction audit.'),
                ('exact_record_comparison_audit.py','audit_exact_comparisons','Original six-gate refinement audit.'),
                ('exact_resource_audit.py','audit_exact_resources','Original cumulative recorded resource audit.'),*_FREE_EQUATIONS[1:]]
            anchors=[(f,symbol.replace('.evaluate','.evaluate_autonomous') if f in ('free_solid_slab.py','water_phase_transfer.py') else symbol,meaning) for f,symbol,meaning in anchors]
        elif case.get('schema')==_EVENT_SCHEMA:
            anchors = [('depletion_integration.py','integrate_depletion','Event-aware mechanical continuation with full original-prefix accounting.'),
                       ('depletion_roundoff.py','depletion_writeback','Paired depletion correction and exact storage-roundoff evidence.'),*_FREE_EQUATIONS[1:]]
    else:
        raise RunError('unsupported_trace_model')
    availability = None
    if not isinstance(result.get('final_snapshot'), dict):
        value = None
        location = None
        availability = {'status': 'unavailable', 'reason': 'final_snapshot_unavailable',
                        'run_reason': result.get('reason'),
                        'semantics': 'No final result value is reported; initial or accepted-prefix values are not substituted.'}
    elif quantity in ('amounts_mol', 'internal_energy_j', 'mechanical_stretches'):
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
    for filename, symbol, meaning in anchors:
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
    if case.get('schema')==_EXACT_EVENT_SCHEMA:
        trace['canonical_exact_record']=result.get('exact_record')
        trace['canonical_result_pointer']=(('/result/fields/states/sequence/'+str(len(result['integration']['states'])-1)+'/fields/'+quantity) if location is not None and quantity in ('amounts_mol','internal_energy_j','mechanical_stretches') else None)
        trace['clock_semantics']='Exact rational clocks retained in canonical record; integration.times_s is display-only elapsed time.'
    if availability is not None:
        trace['value_availability'] = availability
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
    from .source_run_service import KIND as SOURCE_KIND, replay_source_case
    if result.get('integration_kind') == SOURCE_KIND:
        return replay_source_case(directory, output, cancel=cancel)
    if result['runtime_before'] != runtime_identity():
        raise RunError('replay_runtime_mismatch')
    event_binding=None
    from .verification_case import read_case
    saved_case=json.loads((Path(directory)/'case.json').read_bytes())
    if isinstance(saved_case,dict) and saved_case.get('schema') in _EVENT_SCHEMAS:
        case=read_case(Path(directory)/'case.json')
        from .checkpoint import ResumePrefix
        from .run_provenance import catalog_filename
        current=runtime_identity()
        if result.get('runtime_after')!=current:
            raise RunError('replay_runtime_mismatch')
        if any(manifest['files'].get('implementation/'+name)!=digest for name,digest in current['modules'].items()):
            raise RunError('replay_implementation_binding_mismatch')
        catalog_name=catalog_filename(case.payload['model_id'],case_schema=case.payload['schema'])
        if manifest['files'].get('equation_catalog.json')!=current['catalogs'].get(catalog_name):
            raise RunError('replay_catalog_binding_mismatch')
        if case.sha256!=result['case_sha256'] or case.case_id!=result.get('case_id'):
            raise RunError('replay_case_binding_mismatch')
        result_raw=(Path(directory)/'result.json').read_bytes()
        manifest_raw=(Path(directory)/'manifest.json').read_bytes()
        if _hash(result_raw)!=manifest['files']['result.json'] or json.loads(manifest_raw)!=manifest:
            raise RunError('replay_parent_changed_after_validation')
        if case.payload['schema']==_EXACT_EVENT_SCHEMA:
            from .exact_run_service import parent_from
            event_binding=parent_from(directory,result,manifest)
        else:
            event_binding=ResumePrefix(result_raw,manifest_raw,_hash(result_raw),_hash(manifest_raw))
    if event_binding is None:
        return run_case(Path(directory)/'case.json', Path(directory)/'water', output,
                        cancel=cancel, replay_of={'case_sha256': result['case_sha256'],
                        'result_sha256': manifest['files']['result.json']},
                        evidence_directory=Path(directory)/'evidence')
    return run_case(Path(directory)/'case.json', Path(directory)/'water', output,
                    cancel=cancel, replay_of={'case_sha256': result['case_sha256'],
                    'result_sha256': manifest['files']['result.json']},
                    evidence_directory=Path(directory)/'evidence', _event_replay=event_binding)


def _validate_event_resume_policy(case_record, saved_policy):
    """Preflight scalar settings before the actual model can bind source boxes.

    The freshly built complete policy is still compared in _run_event before
    restoration or integration. This check cannot certify a saved box identity.
    """
    from .verification_case import _build_depletion_policy, encode
    expected = encode(_build_depletion_policy(case_record, validation_only=True))
    if type(saved_policy) is not dict:
        raise RunError('resume_case_event_policy_mismatch')
    scalar = dict(saved_policy)
    if case_record['schema'] in ('sandbox_depletion_policy_v2','sandbox_exact_depletion_policy_v1'):
        from .pressure_comparison import restore_pressure_comparison_policy
        typed = scalar.pop('pressure_comparison', None)
        if not (case_record['schema']=='sandbox_exact_depletion_policy_v1' and case_record['pressure_comparison'] is None and typed is None):
            restore_pressure_comparison_policy(typed)
    if scalar != expected:
        raise RunError('resume_case_event_policy_mismatch')


def resume_run(directory: str | Path, output: str | Path, *,
               cancel: Callable[[], bool] | None = None,
               _exact_on_commit: Callable | None = None) -> dict[str, Any]:
    """Continue a verified cancelled accepted prefix using the current installed model."""
    from .checkpoint import ResumePrefix, validate_cancelled
    from .integration import IntegrationPolicy
    from .verification_case import read_case, encode

    directory = Path(directory)
    result, manifest = read_run(directory)
    from .source_run_service import KIND as SOURCE_KIND
    if result.get('integration_kind') == SOURCE_KIND:
        raise RunError('source_study_resume_not_implemented_use_explicit_new_replay')
    current = runtime_identity()
    if result.get('runtime_before') != current or result.get('runtime_after') != current:
        raise RunError('resume_runtime_mismatch')
    for name, digest in current['modules'].items():
        if manifest['files'].get('implementation/'+name) != digest:
            raise RunError('resume_implementation_binding_mismatch')
    case = read_case(directory/'case.json')
    from .run_provenance import catalog_filename
    catalog_name = (catalog_filename(case.payload['model_id'],case_schema=case.payload['schema'])
        if case.payload['schema'] in _EVENT_SCHEMAS else catalog_filename(case.payload['model_id']))
    catalog_sha = current['catalogs'].get(catalog_name)
    if catalog_sha is None or manifest['files'].get('equation_catalog.json') != catalog_sha:
        raise RunError('resume_catalog_binding_mismatch')
    if case.sha256 != result['case_sha256'] or case.case_id != result.get('case_id'):
        raise RunError('resume_case_binding_mismatch')
    try:
        policy_values = dict(case.payload['numerics']['integration'])
        for name in ('initial_step_s', 'maximum_step_s'):
            policy_values[name] /= 2**case.payload['refinement']
        policy = IntegrationPolicy(**policy_values)
        if encode(IntegrationPolicy(**result['policy'])) != encode(policy):
            raise RunError('resume_case_policy_mismatch')
        if case.payload['schema']==_EXACT_EVENT_SCHEMA:
            from .exact_run_service import KIND
            if result.get('integration_kind')!=KIND or result.get('status')!='cancelled' or result.get('core_status')!='cancelled' or not result.get('integration',{}).get('steps'):
                raise RunError('resume_requires_cancelled_exact_prefix')
            _validate_event_resume_policy(case.payload['numerics']['depletion'],result.get('depletion_policy'))
        elif case.payload['schema']==_EVENT_SCHEMA:
            _event_cancelled(result)
            _validate_event_resume_policy(case.payload['numerics']['depletion'],result.get('depletion_policy'))
        else:
            validate_cancelled(result, policy, start_s=case.payload['numerics']['start_s'],
                               end_s=case.payload['numerics']['end_s'])
        if not isinstance(result['initial_snapshot'], dict):
            raise RunError('resume_initial_snapshot_missing')
    except (KeyError, TypeError) as exc:
        raise RunError('invalid_resume_record') from exc
    result_raw = (directory/'result.json').read_bytes()
    manifest_raw = (directory/'manifest.json').read_bytes()
    if (_hash(result_raw) != manifest['files']['result.json'] or
            json.loads(manifest_raw) != manifest):
        raise RunError('resume_parent_changed_after_validation')
    if case.payload['schema']==_EXACT_EVENT_SCHEMA:
        from .exact_run_service import parent_from
        prefix=parent_from(directory,result,manifest)
    else:
        prefix = ResumePrefix(result_raw, manifest_raw, _hash(result_raw), _hash(manifest_raw))
    extra={'_exact_on_commit':_exact_on_commit} if case.payload['schema']==_EXACT_EVENT_SCHEMA else {}
    return run_case(directory/'case.json', directory/'water', output, cancel=cancel,
                    evidence_directory=directory/'evidence', _resume=prefix,**extra)
