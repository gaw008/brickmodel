"""Private single-worker RHS verification; default water calls remain per-point.

Only the closed managed worker may call admission. PID/owner checks bind that
worker's lifetime; they do not prove process isolation or block raw CP setters.
The worker entry owns those execution conditions. No decoded record is a lease.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass, field, fields
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from threading import RLock, current_thread, get_ident, main_thread
from time import monotonic
from types import MappingProxyType, ModuleType
from typing import Iterator

from .water_properties import WaterSourceError


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise WaterSourceError('heos_rhs_' + reason)


def _task() -> object | None:
    try:
        return asyncio.current_task()
    except RuntimeError:  # No running event loop in the synchronous worker.
        return None


def _closed(value: object, cls: type) -> None:
    _require(type(value) is cls, 'closed_class_required:' + cls.__name__)
    _require(set(vars(value)) <= {item.name for item in fields(cls)},
             'instance_override:' + cls.__name__)


@dataclass(frozen=True)
class _Graph:
    objects: tuple[object, ...]
    kernels: tuple[object, ...]
    waters: tuple[object, ...]
    controls: str


def _closed_graph(adapter: object) -> _Graph:
    # Establish every executable collaborator class before invoking bindings.
    from .exact_source_column import ExactSourceColumn
    from .source_wet_column import SourceWetColumn
    _closed(adapter, ExactSourceColumn)
    column = adapter.column
    _closed(column, SourceWetColumn)
    from .source_wet_storage import SourceWetStorage, ManufacturedFixedFluidVolume
    from .source_mass_caloric import ArlabosseMassCaloric, ReactionDisabled
    from .arlabosse_caloric import ArlabosseDryCaloric
    from .rigid_storage import RigidStorage, DeclaredNumericalEnvelope
    from .rigid_water_gas import RigidWaterGas, PressurePolicy
    from .phase_storage import IdealGasPhase, InversePolicy
    from .thermochemistry import ShomateGas, ShomateSegment
    from .ideal_water_vapor import IdealWaterVapor
    from .water_chemical_potential import WaterChemicalPotential
    from .water_heos import HEOSWaterProperties
    from .water_properties import WaterProperties, WaterReference, NumericalLimits
    from .mass_wet_storage import WaterElementConvention
    from .mass_wet_transport import WetFace
    from .solid_fluid_heat import LiquidTransportConfig
    from .liquid_transport import SaturationMobilityTable, LiquidConnection
    from .deforming_solid_storage import _digest

    _require(type(column.storages) is tuple and bool(column.storages), 'storages')
    _closed(column.chemical, WaterChemicalPotential)
    _closed(column.chemical.vapor, IdealWaterVapor)
    objects, waters = [column.chemical, column.chemical.vapor], []
    for storage in column.storages:
        _closed(storage, SourceWetStorage)
        fluid = storage.fluid_template
        for value, cls in ((storage.caloric, ArlabosseMassCaloric),
                           (storage.volume, ManufacturedFixedFluidVolume),
                           (storage.chemistry, ReactionDisabled),
                           (storage.water_element_convention, WaterElementConvention),
                           (fluid, RigidStorage)):
            _closed(value, cls)
            objects.append(value)
        _closed(storage.caloric.provider, ArlabosseDryCaloric)
        _closed(fluid.mechanical, RigidWaterGas)
        _closed(fluid.mechanical.policy, PressurePolicy)
        _closed(fluid.envelope, DeclaredNumericalEnvelope)
        _require(type(fluid.gas_phases) is MappingProxyType
                 and set(fluid.gas_phases) == {'O2', 'N2', 'H2O'}, 'closed_gas_mapping')
        objects.extend((storage, storage.caloric.provider, fluid.mechanical,
                        fluid.mechanical.policy, fluid.envelope))
        for name in ('O2', 'N2', 'H2O'):
            phase = fluid.gas_phases[name]
            _closed(phase, IdealGasPhase)
            _closed(phase.caloric, IdealWaterVapor if name == 'H2O' else ShomateGas)
            objects.extend((phase, phase.caloric))
            if name != 'H2O':
                _require(type(phase.caloric.segments) is tuple, 'shomate_segments')
                for segment in phase.caloric.segments:
                    _closed(segment, ShomateSegment)
                    objects.append(segment)
        waters.extend((fluid.mechanical.water, fluid.gas_phases['H2O'].caloric._water))
    for values, cls in ((column.inverse_policies, InversePolicy), (column.faces, WetFace)):
        _require(type(values) is tuple, 'closed_column_tuples')
        for value in values:
            _closed(value, cls)
            objects.append(value)
    if column.liquid_transport is not None:
        config = column.liquid_transport
        _closed(config, LiquidTransportConfig)
        objects.append(config)
        for values, cls in ((config.relations, SaturationMobilityTable),
                            (config.connections, LiquidConnection)):
            _require(type(values) is tuple, 'closed_liquid_tuples')
            for value in values:
                _closed(value, cls)
                objects.append(value)
    waters.extend((column.chemical.water, column.chemical.vapor._water))
    kernels, unique_waters = [], []
    for water in waters:
        _closed(water, HEOSWaterProperties)
        _closed(water._ideal, WaterProperties)
        _closed(water.reference, WaterReference)
        _closed(water.numerical_limits, NumericalLimits)
        backend, model = water._ideal._backend, water._ideal._model
        _require(type(backend) is ModuleType and backend is sys.modules.get('iapws')
                 and type(model) is backend.IAPWS95, 'actual_python_ideal_backend')
        _require(not {'_phi0', '_phir', '_Helmholtz'}.intersection(vars(model)),
                 'python_ideal_method_override')
        objects.extend((water, water._ideal, water._ideal._model, water._ideal._backend,
                        backend.IAPWS95, water.reference, water.numerical_limits))
        if not any(water is prior for prior in unique_waters):
            unique_waters.append(water)
        if not any(water._kernel is prior for prior in kernels):
            kernels.append(water._kernel)
    controls = _digest(tuple((item.name, getattr(column, item.name)) for item in fields(column)
        if item.name not in ('storages', 'chemical', 'interface_modes', '_identity')))
    return _Graph(tuple(objects), tuple(kernels), tuple(unique_waters), controls)


def _validate_graph(adapter: object, original: _Graph) -> None:
    graph = _closed_graph(adapter)
    _require(len(graph.objects) == len(original.objects)
             and all(a is b for a, b in zip(graph.objects, original.objects))
             and len(graph.kernels) == len(original.kernels)
             and all(a is b for a, b in zip(graph.kernels, original.kernels))
             and graph.controls == original.controls, 'original_live_graph_changed')
    adapter.operator_identity
    for water in graph.waters:
        water._guard()


_IDENTITY_FIELDS = ('_cp', '_flash', '_check', '_lock', 'reference')
_VALUE_FIELDS = ('_config', '_fluid_digest', 'descriptor_json', 'identity', '_r', '_mass', '_sealed')
_CP_FIELDS = ('AbstractState', 'get_config_as_json_string', 'get_fluid_param_string')
_LOCK_TYPE = type(RLock())


def _kernel_binding(kernel: object) -> tuple:
    from ._heos_kernel import HEOSCandidate
    _require(type(kernel) is HEOSCandidate, 'new_actual_kernel_required')
    _require(type(kernel._cp) is ModuleType and kernel._cp is sys.modules.get('CoolProp.CoolProp'),
             'actual_native_module')
    _require(type(kernel._flash) is kernel._cp.AbstractState
             and type(kernel._check) is kernel._cp.AbstractState, 'actual_native_states')
    _require(type(kernel._lock) is _LOCK_TYPE, 'actual_native_lock')
    _require(kernel._sealed is True, 'sealed_kernel_required')
    _require(all(type(getattr(kernel, name)) is str for name in _VALUE_FIELDS[:4]), 'kernel_strings')
    _require(all(type(getattr(kernel, name)) is float and math.isfinite(getattr(kernel, name))
                 for name in ('_r', '_mass')), 'kernel_constants')
    descriptor = json.loads(kernel.descriptor_json)
    _require(hashlib.sha256(kernel.descriptor_json.encode()).hexdigest() == kernel.identity
             and json.dumps(descriptor['runtime']['config'], sort_keys=True) == kernel._config
             and descriptor['runtime']['fluid_sha256'] == kernel._fluid_digest, 'kernel_descriptor')
    return (tuple(getattr(kernel, name) for name in (*_IDENTITY_FIELDS, *_VALUE_FIELDS))
            + tuple(getattr(kernel._cp, name) for name in _CP_FIELDS))


def _unchanged(kernel: object, binding: tuple) -> None:
    for name, original in zip((*_IDENTITY_FIELDS, *_VALUE_FIELDS), binding):
        current = getattr(kernel, name)
        _require(current is original if name in _IDENTITY_FIELDS else
                 type(current) is type(original) and current == original, 'kernel_binding_changed')
    for name, original in zip(_CP_FIELDS, binding[len(_IDENTITY_FIELDS) + len(_VALUE_FIELDS):]):
        _require(getattr(kernel._cp, name) is original, 'native_getter_changed')


@dataclass(frozen=True)
class _WorkerAdmission:
    pid: int
    thread: int
    supervisor_pid: int
    deadline: float
    graph: _Graph
    bindings: tuple[tuple, ...]
    records: list[dict] = field(default_factory=list)
    closed: bool = False


@dataclass
class _ActiveRHS:
    worker: _WorkerAdmission
    record: dict


_worker: _WorkerAdmission | None = None
_active: _ActiveRHS | None = None


def _owner(lease: _WorkerAdmission) -> None:
    _require(lease is _worker and not lease.closed and os.getpid() == lease.pid
             and os.getppid() == lease.supervisor_pid and get_ident() == lease.thread
             and _task() is None, 'worker_owner_changed')


def _require_worker_entry() -> None:
    entry = sys.modules.get('__main__')
    spec = getattr(entry, '__spec__', None)
    _require(sys.flags.isolated and type(entry) is ModuleType
             and getattr(spec, 'name', None) == 'sludge_sandbox.source_managed_worker'
             and type(getattr(entry, '__file__', None)) is str
             and Path(entry.__file__).resolve() == Path(__file__).with_name('source_managed_worker.py').resolve(),
             'dedicated_isolated_worker_required')


def _admit_worker(adapter: object, *, supervisor_pid: int,
                  deadline_monotonic: float) -> _WorkerAdmission:
    """Private worker bootstrap seam; caller owns dedicated closed-process admission."""
    global _worker
    _require_worker_entry()
    _require(_worker is None and _active is None, 'worker_already_admitted')
    _require(type(supervisor_pid) is int and 0 < supervisor_pid == os.getppid()
             and supervisor_pid != os.getpid(), 'supervisor_pid')
    _require(current_thread() is main_thread() and _task() is None, 'synchronous_main_thread')
    _require(type(deadline_monotonic) is float and math.isfinite(deadline_monotonic)
             and deadline_monotonic > monotonic(), 'finite_future_deadline')
    graph = _closed_graph(adapter)
    bindings = tuple(_kernel_binding(kernel) for kernel in graph.kernels)
    _validate_graph(adapter, graph)
    _worker = _WorkerAdmission(os.getpid(), get_ident(), supervisor_pid,
                               deadline_monotonic, graph, bindings)
    return _worker


def _close_worker(lease: _WorkerAdmission) -> None:
    global _worker
    _owner(lease)
    _require(_active is None, 'cannot_close_active_rhs')
    object.__setattr__(lease, 'closed', True)
    _worker = None


def _worker_audit(lease: _WorkerAdmission) -> dict:
    """Owned data copy; no live token and no external source/isolation certification."""
    _require(type(lease) is _WorkerAdmission, 'actual_worker_admission')
    return json.loads(json.dumps({'mode': 'managed_single_rhs_boundary_v1',
        'pid': lease.pid, 'supervisor_pid': lease.supervisor_pid, 'closed': lease.closed,
        'rhs': lease.records, 'material_qualified': False}, allow_nan=False))


def _error(exc: BaseException) -> dict:
    return {'type': type(exc).__name__, 'reason': str(exc)}


def _verify(lease: _WorkerAdmission, record: dict, *, after: bool) -> list[BaseException]:
    errors = []
    for kernel, binding in zip(lease.graph.kernels, lease.bindings):
        check = {'stage': 'exit' if after else 'entry', 'kernel_identity': binding[8],
                 'status': 'started'}
        record['checks'].append(check)
        try:
            _unchanged(kernel, binding)
            operations = ('fluid', 'config') if after else ('config', 'fluid')
            for operation in operations:
                if operation == 'fluid':
                    actual = hashlib.sha256(kernel._cp.get_fluid_param_string('Water', 'JSON').encode()).hexdigest()
                    check['fluid_sha256'] = actual
                    if actual != kernel._fluid_digest:
                        raise WaterSourceError('heos_runtime_fluid_changed')
                else:
                    actual = json.dumps(json.loads(kernel._cp.get_config_as_json_string()), sort_keys=True)
                    check['config_sha256'] = hashlib.sha256(actual.encode()).hexdigest()
                    if actual != kernel._config:
                        raise WaterSourceError('heos_runtime_config_changed')
            check['status'] = 'verified'
        except BaseException as exc:
            check.update(status='failed', error=_error(exc))
            errors.append(exc)
    return errors


def _active_for_kernel(kernel: object) -> bool:
    """Called by the real kernel before its original locked warning/native body."""
    if _worker is None:
        return False
    _owner(_worker)
    if _active is None:
        return False
    _require(_active.worker is _worker, 'active_worker_mismatch')
    _require(monotonic() < _worker.deadline, 'original_deadline_exhausted')
    for member, binding in zip(_worker.graph.kernels, _worker.bindings):
        if member is kernel:
            _unchanged(kernel, binding)
            _active.record['native_operations'] += 1
            return True
    raise WaterSourceError('heos_rhs_kernel_not_member')


@contextmanager
def _rhs_scope(adapter: object, time: object) -> Iterator[None]:
    global _active
    if _worker is None:
        yield
        return
    lease = _worker
    _owner(lease)
    _require(_active is None, 'nested_rhs_forbidden')
    record = {'ordinal': len(lease.records) + 1, 'time': repr(time), 'status': 'started',
              'native_operations': 0, 'checks': [], 'primary_error': None, 'exit_errors': []}
    lease.records.append(record)
    started = monotonic()
    primary = None
    try:
        _require(started < lease.deadline, 'original_deadline_exhausted')
        _validate_graph(adapter, lease.graph)
        with ExitStack() as locks:
            for kernel, binding in sorted(zip(lease.graph.kernels, lease.bindings), key=lambda pair: id(pair[0])):
                _unchanged(kernel, binding)
                locks.enter_context(binding[3])
            errors = _verify(lease, record, after=False)
            if errors:
                raise errors[0]
            _active = _ActiveRHS(lease, record)
            try:
                yield
            except BaseException as exc:
                primary = exc
                raise
            finally:
                _active = None
                errors = _verify(lease, record, after=True)
                try:
                    _owner(lease)
                    _validate_graph(adapter, lease.graph)
                    _require(monotonic() < lease.deadline, 'original_deadline_exhausted')
                except BaseException as exc:
                    errors.append(exc)
                record['exit_errors'] = [_error(exc) for exc in errors]
                if errors:
                    if primary is not None:
                        for error in errors:
                            primary.add_note('HEOS RHS exit verification: ' + repr(error))
                    else:
                        raise errors[0]
        record['status'] = 'verified'
    except BaseException as exc:
        record.update(status='failed', primary_error=_error(exc))
        raise
    finally:
        record['elapsed_seconds'] = max(0., monotonic() - started)
