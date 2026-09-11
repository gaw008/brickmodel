"""Pure metadata/native-body seams: no provider construction or EOS."""
import hashlib
import json
import os
from threading import RLock
from types import ModuleType, SimpleNamespace

import pytest

import sludge_sandbox._heos_rhs_scope as scope
from sludge_sandbox._heos_kernel import HEOSCandidate
from sludge_sandbox.water_properties import WaterSourceError, WaterNumericalError


def shell(cls, **values):
    out = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(out, name, value)
    return out


@pytest.fixture
def world(monkeypatch):
    calls = []
    cp = ModuleType('CoolProp.CoolProp')
    cp.AbstractState = type('FakeNativeState', (), {})
    data = {'config': '{"flag": true}', 'fluid': 'original water bytes'}
    def config():
        calls.append('config')
        return data['config']
    def fluid(*args):
        assert args == ('Water', 'JSON')
        calls.append('fluid')
        return data['fluid']
    cp.get_config_as_json_string = config
    cp.get_fluid_param_string = fluid
    import sys
    monkeypatch.setitem(sys.modules, 'CoolProp.CoolProp', cp)
    kernels = []
    for _ in range(2):
        descriptor = json.dumps({'runtime': {
            'config': json.loads(data['config']),
            'fluid_sha256': hashlib.sha256(data['fluid'].encode()).hexdigest(),
        }}, sort_keys=True)
        kernels.append(shell(HEOSCandidate, _cp=cp, _config=data['config'],
            _fluid_digest=hashlib.sha256(data['fluid'].encode()).hexdigest(),
            _flash=cp.AbstractState(), _check=cp.AbstractState(), _lock=RLock(),
            _sealed=True, reference=object(), _r=1., _mass=2.,
            descriptor_json=descriptor, identity=hashlib.sha256(descriptor.encode()).hexdigest()))
    adapter = object()
    graph = scope._Graph((adapter,), tuple(kernels), (), 'controls')
    monkeypatch.setattr(scope, '_closed_graph', lambda value: graph)
    monkeypatch.setattr(scope, '_validate_graph', lambda value, original: None)
    # Pure inner mechanics only; the actual isolated worker is not executed.
    monkeypatch.setattr(scope, '_require_worker_entry', lambda: None)
    monkeypatch.setattr(scope, 'monotonic', lambda: 10.)
    yield SimpleNamespace(adapter=adapter, kernels=kernels, calls=calls, data=data, graph=graph)
    if scope._worker is not None:
        scope._close_worker(scope._worker)


def admit(world):
    return scope._admit_worker(world.adapter, supervisor_pid=os.getppid(), deadline_monotonic=100.)


def operation(world, kernel=None):
    with (kernel or world.kernels[0])._transaction():
        world.calls.append('body')


def test_default_original_order_and_no_amortization(world):
    operation(world)
    operation(world)
    assert world.calls == ['config', 'fluid', 'body', 'fluid', 'config'] * 2


def test_scope_amortizes_only_actual_members_and_closes(world):
    lease = admit(world)
    with scope._rhs_scope(world.adapter, 'exact time'):
        operation(world)
        operation(world, world.kernels[1])
    assert world.calls == ['config', 'fluid'] * 2 + ['body'] * 2 + ['fluid', 'config'] * 2
    assert scope._worker_audit(lease)['rhs'][0]['native_operations'] == 2
    assert scope._worker_audit(lease)['rhs'][0]['status'] == 'verified'
    world.calls.clear()
    operation(world)
    assert world.calls == ['config', 'fluid', 'body', 'fluid', 'config']


def test_exit_failure_preserves_completed_body(world):
    lease = admit(world)
    with pytest.raises(WaterSourceError, match='fluid_changed'):
        with scope._rhs_scope(world.adapter, 'exact time'):
            operation(world)
            world.data['fluid'] = 'changed'
    assert world.calls.count('body') == 1
    record = scope._worker_audit(lease)['rhs'][0]
    assert record['status'] == 'failed' and record['exit_errors']


def test_primary_exception_and_secondary_exit_failure(world):
    lease = admit(world)
    primary = RuntimeError('actual native failure')
    with pytest.raises(RuntimeError) as caught:
        with scope._rhs_scope(world.adapter, 'exact time'):
            operation(world)
            world.data['config'] = '{}'
            raise primary
    assert caught.value is primary
    record = scope._worker_audit(lease)['rhs'][0]
    assert record['primary_error']['type'] == 'RuntimeError' and record['exit_errors']


def test_warning_remains_per_operation(world):
    import warnings
    lease = admit(world)
    with pytest.raises(WaterNumericalError, match='native_warning'):
        with scope._rhs_scope(world.adapter, 'exact time'):
            with world.kernels[0]._transaction():
                warnings.warn('actual warning')
    assert scope._worker_audit(lease)['rhs'][0]['status'] == 'failed'


def test_foreign_equal_descriptor_kernel_is_rejected(world):
    admit(world)
    foreign = shell(HEOSCandidate, **vars(world.kernels[0]))
    with pytest.raises(WaterSourceError, match='member'):
        with scope._rhs_scope(world.adapter, 'exact time'):
            operation(world, foreign)
    assert 'body' not in world.calls


@pytest.mark.parametrize('parent,deadline', [(True, 100.), (0, 100.), (os.getpid(), 100.),
                                           (os.getppid(), 10.), (os.getppid(), float('inf'))])
def test_invalid_worker_admission(world, parent, deadline):
    with pytest.raises(WaterSourceError):
        scope._admit_worker(world.adapter, supervisor_pid=parent, deadline_monotonic=deadline)
    assert scope._worker is None and not world.calls


def test_entry_failure_runs_no_native_body_and_next_default_call_rechecks(world):
    lease = admit(world)
    world.data['config'] = '{}'
    with pytest.raises(WaterSourceError, match='config_changed'):
        with scope._rhs_scope(world.adapter, 'exact time'):
            operation(world)
    assert 'body' not in world.calls
    scope._close_worker(lease)
    with pytest.raises(WaterSourceError, match='config_changed'):
        operation(world)


def test_default_exception_skips_original_post_yield_checks(world):
    primary = ValueError('body')
    with pytest.raises(ValueError) as caught:
        with world.kernels[0]._transaction():
            raise primary
    assert caught.value is primary and world.calls == ['config', 'fluid']


def test_deadline_after_actual_body_cannot_publish_verified(world, monkeypatch):
    lease = admit(world)
    with pytest.raises(WaterSourceError, match='deadline'):
        with scope._rhs_scope(world.adapter, 'exact time'):
            operation(world)
            monkeypatch.setattr(scope, 'monotonic', lambda: 101.)
    record = scope._worker_audit(lease)['rhs'][0]
    assert record['native_operations'] == 1 and record['elapsed_seconds'] == 91.
    assert record['status'] == 'failed'


def test_nested_scope_rejected_without_losing_outer_record(world):
    lease = admit(world)
    with pytest.raises(WaterSourceError, match='nested'):
        with scope._rhs_scope(world.adapter, 'outer'):
            with scope._rhs_scope(world.adapter, 'inner'):
                pytest.fail('inner body')
    assert len(scope._worker_audit(lease)['rhs']) == 1
    assert scope._active is None


def test_second_thread_cannot_share_active_scope(world):
    from concurrent.futures import ThreadPoolExecutor
    admit(world)
    with scope._rhs_scope(world.adapter, 'outer'):
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(operation, world)
            with pytest.raises(WaterSourceError, match='owner'):
                future.result(timeout=2.)
        operation(world)
    assert world.calls.count('body') == 1


def test_forked_pid_does_not_inherit_admission(world, monkeypatch):
    admit(world)
    original = os.getpid()
    with monkeypatch.context() as patch:
        patch.setattr(scope.os, 'getpid', lambda: original + 100)
        with pytest.raises(WaterSourceError, match='owner'):
            operation(world)
    assert not world.calls


@pytest.mark.parametrize('field', ['_flash', '_check', '_lock', 'reference', '_config'])
def test_live_kernel_replacement_refused_before_native_body(world, field):
    admit(world)
    kernel = world.kernels[0]
    with pytest.raises(WaterSourceError, match='binding'):
        with scope._rhs_scope(world.adapter, 'time'):
            object.__setattr__(kernel, field, object())
            operation(world)
    assert 'body' not in world.calls


def test_native_getter_replacement_cannot_hide_changed_source(world):
    admit(world)
    with pytest.raises(WaterSourceError, match='getter'):
        with scope._rhs_scope(world.adapter, 'time'):
            world.kernels[0]._cp.get_config_as_json_string = lambda: '{}'
            operation(world)
    assert 'body' not in world.calls


def test_closed_lease_cannot_be_reused_and_audit_is_owned(world):
    lease = admit(world)
    with scope._rhs_scope(world.adapter, 'time'):
        operation(world)
    scope._close_worker(lease)
    result = scope._worker_audit(lease)
    result['rhs'][0]['status'] = 'forged'
    assert scope._worker_audit(lease)['rhs'][0]['status'] == 'verified'
    with pytest.raises(WaterSourceError, match='owner'):
        scope._close_worker(lease)
    operation(world)


@pytest.mark.parametrize('actual_class', [False, True])
def test_foreign_column_and_instance_callback_rejected_before_call(monkeypatch, actual_class):
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.source_wet_column import SourceWetColumn
    column = shell(SourceWetColumn) if actual_class else SimpleNamespace()
    object.__setattr__(column, 'evaluate', lambda *a: pytest.fail('foreign callback invoked'))
    adapter = shell(ExactSourceColumn, column=column)
    with pytest.raises(WaterSourceError, match='instance_override|closed_class'):
        scope._closed_graph(adapter)


def rhs_host(world, monkeypatch, *, mutate=False):
    """Actual adapter wrapper; explicitly manufactured fields, no model evaluation."""
    from fractions import Fraction
    import numpy as np
    from sludge_sandbox.exact_event_clock import ExactEventTime
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.source_wet_column import SourceWetColumn
    from sludge_sandbox.source_mass_caloric import DisabledChemicalRates
    from sludge_sandbox.integration import ConservedState
    column = shell(SourceWetColumn, storages=(object(),))
    adapter = shell(ExactSourceColumn, column=column)
    initial = SimpleNamespace(solid_mass_kg=(1.,), gas_amounts_mol=(1., 2., 3.))
    chemistry = DisabledChemicalRates((Fraction(),), (Fraction(),) * 3)
    cell = SimpleNamespace(chemistry=chemistry, phase=SimpleNamespace(phase_water_mol_s=0.))
    face = SimpleNamespace(gas_mol_s=(0., 0., 0.), energy_w=0.)
    def body(*args):
        operation(world)
        if mutate:
            world.data['fluid'] = 'changed'
        return SimpleNamespace(cells=(cell,), faces=(face, face))
    monkeypatch.setattr(SourceWetColumn, 'evaluate', body)
    monkeypatch.setattr(ExactSourceColumn, 'unpack', lambda *a: (initial,))
    monkeypatch.setattr(ExactSourceColumn, 'operator_identity', property(lambda s: ('manufactured',)))
    monkeypatch.setattr(ExactSourceColumn, 'species_ids', property(lambda s: ('liquid_water', 'O2', 'N2', 'H2O')))
    world.adapter = adapter
    return adapter, ConservedState(np.ones((1, 4)), np.ones(1), ('manufactured',)), ExactEventTime(Fraction())


def test_rhs_exit_failure_keeps_actual_candidate_without_success_event(world, monkeypatch):
    from sludge_sandbox.source_run_observer import observer_scope
    adapter, state, time = rhs_host(world, monkeypatch, mutate=True)
    lease = admit(world)
    events = []
    with observer_scope(lambda event, **payload: events.append((event, payload))):
        with pytest.raises(WaterSourceError, match='fluid_changed'):
            adapter.evaluate(state, time)
    assert [event for event, _ in events] == ['rhs_started', 'rhs_failed']
    assert events[-1][1]['evaluation'] is not None
    assert scope._worker_audit(lease)['rhs'][0]['native_operations'] == 1


def test_rhs_return_observer_runs_after_scope_and_original_error_survives(world, monkeypatch):
    from sludge_sandbox.source_run_observer import observer_scope
    adapter, state, time = rhs_host(world, monkeypatch)
    lease = admit(world)
    events = []
    failure = OSError('actual recorder failure')
    def sink(event, **payload):
        events.append((event, payload))
        if event == 'rhs_returned':
            assert scope._active is None
            assert scope._worker_audit(lease)['rhs'][0]['status'] == 'verified'
            raise failure
    with observer_scope(sink):
        with pytest.raises(OSError) as caught:
            adapter.evaluate(state, time)
    assert caught.value is failure
    assert [event for event, _ in events] == ['rhs_started', 'rhs_returned', 'rhs_failed']
    assert events[1][1]['evaluation'] is events[2][1]['evaluation']


def class_graph(monkeypatch):
    """Only a structural class-guard projection, deliberately no physical fields."""
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.source_wet_column import SourceWetColumn
    from sludge_sandbox.source_wet_storage import SourceWetStorage, ManufacturedFixedFluidVolume
    from sludge_sandbox.source_mass_caloric import ArlabosseMassCaloric, ReactionDisabled
    from sludge_sandbox.arlabosse_caloric import ArlabosseDryCaloric
    from sludge_sandbox.rigid_storage import RigidStorage, DeclaredNumericalEnvelope
    from sludge_sandbox.rigid_water_gas import RigidWaterGas, PressurePolicy
    from sludge_sandbox.phase_storage import IdealGasPhase, InversePolicy
    from sludge_sandbox.thermochemistry import ShomateGas, ShomateSegment
    from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    from sludge_sandbox.water_heos import HEOSWaterProperties
    from sludge_sandbox.water_properties import WaterProperties, WaterReference, NumericalLimits
    from sludge_sandbox.mass_wet_storage import WaterElementConvention
    from types import MappingProxyType
    import sys
    backend = ModuleType('iapws')
    backend.IAPWS95 = type('FakePythonIdeal', (), {})
    monkeypatch.setitem(sys.modules, 'iapws', backend)
    waters = tuple(shell(HEOSWaterProperties, _ideal=shell(WaterProperties,
        _model=backend.IAPWS95(), _backend=backend), reference=shell(WaterReference),
        numerical_limits=shell(NumericalLimits), _kernel=object()) for _ in range(4))
    phases = {name: shell(IdealGasPhase, caloric=shell(ShomateGas,
        segments=(shell(ShomateSegment),))) for name in ('O2', 'N2')}
    phases['H2O'] = shell(IdealGasPhase, caloric=shell(IdealWaterVapor, _water=waters[1]))
    fluid = shell(RigidStorage, mechanical=shell(RigidWaterGas, water=waters[0],
        policy=shell(PressurePolicy)), envelope=shell(DeclaredNumericalEnvelope),
        gas_phases=MappingProxyType(phases))
    storage = shell(SourceWetStorage, caloric=shell(ArlabosseMassCaloric,
        provider=shell(ArlabosseDryCaloric)), volume=shell(ManufacturedFixedFluidVolume),
        chemistry=shell(ReactionDisabled), water_element_convention=shell(WaterElementConvention),
        fluid_template=fluid)
    chemical = shell(WaterChemicalPotential, water=waters[2],
        vapor=shell(IdealWaterVapor, _water=waters[3]))
    column = shell(SourceWetColumn, storages=(storage,), chemical=chemical,
        inverse_policies=(InversePolicy(1., 1., 3),), faces=(), liquid_transport=None,
        transfer_coefficients_mol_s_pa=(1.,), cell_widths_m=(1.,), face_area_m2=1.,
        interface_modes=('existing_liquid',), coefficient_source_ids=('manufactured',),
        boundary_conditions=('closed_no_flux', 'closed_no_flux'),
        transport_classification='manufactured_test_fixture')
    return shell(ExactSourceColumn, column=column)


def test_structural_projection_finds_all_four_actual_water_paths(monkeypatch):
    adapter = class_graph(monkeypatch)
    graph = scope._closed_graph(adapter)
    assert len(graph.kernels) == len(graph.waters) == 4
    assert graph.kernels[0] is adapter.column.storages[0].fluid_template.mechanical.water._kernel
    assert graph.kernels[-1] is adapter.column.chemical.vapor._water._kernel


@pytest.mark.parametrize('part', ['gas', 'chemical_water', 'caloric', 'python_ideal', 'policy', 'python_model'])
def test_nested_foreign_collaborator_refused_before_binding(part, monkeypatch):
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from types import MappingProxyType
    adapter = class_graph(monkeypatch)
    storage = adapter.column.storages[0]
    foreign = SimpleNamespace(evaluate=lambda *a: pytest.fail('foreign callback'))
    if part == 'gas':
        phases = dict(storage.fluid_template.gas_phases)
        phases['O2'] = foreign
        object.__setattr__(storage.fluid_template, 'gas_phases', MappingProxyType(phases))
    elif part == 'chemical_water':
        object.__setattr__(adapter.column.chemical, 'water', foreign)
    elif part == 'caloric':
        object.__setattr__(storage.caloric, 'provider', foreign)
    elif part == 'python_ideal':
        object.__setattr__(storage.fluid_template.mechanical.water, '_ideal', foreign)
    elif part == 'python_model':
        object.__setattr__(storage.fluid_template.mechanical.water._ideal, '_model', foreign)
    else:
        object.__setattr__(adapter.column, 'inverse_policies', (foreign,))
    monkeypatch.setattr(ExactSourceColumn, 'operator_identity',
                        property(lambda s: pytest.fail('binding before class checks')))
    with pytest.raises(WaterSourceError, match='closed_class|actual_python'):
        scope._closed_graph(adapter)


def test_generic_process_cannot_admit_private_worker_lease():
    with pytest.raises(WaterSourceError, match='dedicated_isolated_worker_required'):
        scope._admit_worker(object(), supervisor_pid=os.getppid(), deadline_monotonic=1e12)
    assert scope._worker is None
