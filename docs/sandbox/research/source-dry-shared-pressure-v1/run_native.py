"""Prepared single HEOS/source shared-volume wet-to-dry study; importing this file runs no EOS.

Execution completion, numerical event acceptance and material qualification are
separate outcomes. Original error envelopes and scientific gates are retained.
"""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import signal
import sys
import time
from unittest.mock import patch

OUTER_SECONDS = 210.
CALLBACK_CAP = 16
DRY_PATH_CALLBACK_CAP = 24
TOTAL_CALLBACK_CAP = 97  # One probe + three 16-call trials + two 24-call paths.
EXPECTED_CALLBACKS = 32  # Planning estimate only; never asserted as an observation.
INITIAL_LIQUID_MOL = 1e-11
PREVIOUS_RUNNER = 'source-dry-transition-v1/run_native.py'
PREVIOUS_RUNNER_SHA256 = 'a7916d30ee0eb0abf5852a76c5b92eec3a70acd1b0e130cd05a1dc556f2d6e71'
HELPERS = {
    'source-wet-storage-v1/run_native.py': '9a8bbf40651c7dfc31e81c85e8367904e441e210f1c7b1666c9080dbc81b93a6',
    'exact-source-column-v1/run_native.py': 'b0b873960bdc8bc9f2299fc3d0d008fd5fa5a9d3f7a972eb0f080ec3a2d39ab5',
}
LIVE_FIELDS = frozenset(('adapter', 'dry_adapter', 'storage'))


def saved_record(value, base_serialize):
    """Retain nested type/fields and numerical data; omit only live host fields.

    The fixed old serializer supplies Fraction/ndarray/NumPy scalar formats.
    A nonfinite failed observation is explicitly tagged instead of becoming
    invalid JSON or preventing the original failed attempt from being saved.
    """
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else {'type': 'nonfinite_binary64', 'value': repr(value)}
    if is_dataclass(value):
        return {'type': type(value).__module__+'.'+type(value).__qualname__,
                'fields': {field.name: saved_record(getattr(value, field.name), base_serialize)
                           for field in fields(value) if field.name not in LIVE_FIELDS}}
    if isinstance(value, Mapping):
        return {key: saved_record(item, base_serialize) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [saved_record(item, base_serialize) for item in value]
    return saved_record(base_serialize(value), base_serialize)


def run(root, output):
    root, output = Path(root), Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    result = dict(status='started', numerical_comparison_completed=False,
        numerical_event_accepted=False, material_qualified=False,
        scope='explicit_shared_volume_N1_source_wet_to_dry_numerical_scenario',
        pressure_strategy='explicit_shared_source_dry_volume',
        prior_independent_pressure_failure_unchanged=True,
        initial_liquid_mol=INITIAL_LIQUID_MOL, prior_1e_minus_6_scenario_unchanged=True,
        outer_seconds=OUTER_SECONDS, per_trial_callback_cap=CALLBACK_CAP,
        per_dry_path_callback_cap=DRY_PATH_CALLBACK_CAP, total_callback_cap=TOTAL_CALLBACK_CAP,
        expected_callbacks_not_measurement=EXPECTED_CALLBACKS, captures=[], returned_candidates=[],
        backend_constructors_started=0, backend_constructors_completed=0,
        constructor_reference_anchor_checks=0, initial_energy_evaluations_attempted=0,
        helper_hashes=HELPERS, previous_runner_sha256=PREVIOUS_RUNNER_SHA256,
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

    def save():
        result['wall_seconds'] = time.monotonic()-started
        pending = output.with_suffix(output.suffix+'.pending')
        pending.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
        pending.replace(output)

    def require(ok, reason):
        if not ok:
            raise AssertionError(reason)

    def timeout(*_):
        result['outer_timeout_requested'] = True
        raise TimeoutError('outer_210s_budget_exceeded')

    def load_helper(name):
        path = root/'docs/sandbox/research'/name
        require(hashlib.sha256(path.read_bytes()).hexdigest() == HELPERS[name], 'constructor_changed:'+name)
        spec = importlib.util.spec_from_file_location('prepared_'+name.split('/')[0].replace('-', '_'), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    encode = None
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, OUTER_SECONDS)
    try:
        save()
        require(hashlib.sha256((root/'docs/sandbox/research'/PREVIOUS_RUNNER).read_bytes()).hexdigest()
                == PREVIOUS_RUNNER_SHA256, 'previous_prepared_runner_changed')
        source = load_helper('source-wet-storage-v1/run_native.py')
        serializer = load_helper('exact-source-column-v1/run_native.py').serialize
        encode = lambda value: saved_record(value, serializer)
        from sludge_sandbox.depletion_integration import DepletionPolicy
        from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy
        from sludge_sandbox.exact_event_clock import ExactEventTime as T
        from sludge_sandbox.exact_source_column import ExactSourceColumn
        from sludge_sandbox.integration import IntegrationPolicy
        from sludge_sandbox.phase_storage import InversePolicy
        from sludge_sandbox.source_wet_column import SourceWetColumn
        from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
        from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial
        from sludge_sandbox.source_approach import propose_source_approach, evaluate_source_approach
        from sludge_sandbox.source_root_comparison import evaluate_source_root_refinement
        from sludge_sandbox.source_net_prefix import _same
        import sludge_sandbox.source_dry_transition as transition_module
        from sludge_sandbox._heos_kernel import HEOSCandidate
        from sludge_sandbox.source_dry_shared_pressure import declare_source_shared_dry_volume

        original_init = HEOSCandidate.__init__

        def counted_init(self, *args, **kwargs):
            result['backend_constructors_started'] += 1
            save()
            original_init(self, *args, **kwargs)
            result['backend_constructors_completed'] += 1
            # A successful constructor runs one manifest/reference anchor check;
            # these counts do not purport to count every internal native update.
            result['constructor_reference_anchor_checks'] += 1
            save()

        with patch.object(HEOSCandidate, '__init__', counted_init):
            storage, _ = source.make_case(root)
            waterdir = root/'data/sandbox/water'
            chemical = WaterChemicalPotential(waterdir, backend='heos',
                backend_manifest=waterdir/'heos-8.0.0-approved-manifest.json')
        require(result['backend_constructors_started'] == result['backend_constructors_completed'] == 4,
                'four_actual_provider_constructors')
        column = SourceWetColumn((storage,), (InversePolicy(1e-5, 1e-6, 100),), chemical,
            (1e-9,), (), (.25,), .01, ('existing_liquid',),
            ('manufactured:source-column-transport',))
        require(column.liquid_transport is None, 'no_liquid_transport_in_N1_scenario')
        shared = declare_source_shared_dry_volume(storage)
        shared.check()
        result['shared_volume_declaration'] = encode(shared)
        result['shared_parameter_runtime_admission'] = dict(
            same_initial_storage_object=shared.storage is storage,
            same_initial_volume_object=shared.volume is storage.volume,
            object_identity_scope='current_process_only_not_offline_reconstruction')
        save()
        state = storage.state(INITIAL_LIQUID_MOL, (.125, .25, 1e-12), 0.)
        result.update(initial_unset_energy=encode(state), initial_temperature_k=325.,
                      initial_energy_evaluations_attempted=1)
        save()
        point = storage.evaluate(state, 325.)
        state = replace(state, internal_energy_j=point.total_internal_energy_j)
        adapter = ExactSourceColumn(column)
        initial = adapter.pack((state,))
        result.update(status='constructed', initial_energy_point=encode(point), initial=encode(initial),
            adapter_provenance=encode(adapter.provenance()), build_seconds=time.monotonic()-started)
        save()
        actual = ExactSourceColumn.evaluate
        phase_name = 'initial_rate_probe'

        def observed(self, packed, at):
            require(type(self) is ExactSourceColumn and type(self.column) is SourceWetColumn,
                    'actual_prepared_source_column_required')
            require(self.energy_model_identity == adapter.energy_model_identity
                    and self.species_ids == adapter.species_ids
                    and all(_same(getattr(self.column, field.name), getattr(column, field.name))
                            for field in fields(column) if field.name not in ('interface_modes', '_identity')),
                    'prepared_source_energy_mass_or_column_changed')
            require((self is adapter and self.interfaces == ('existing_liquid',))
                    or (self is not adapter and self.interfaces == ('depleted_no_nucleation',)),
                    'explicit_original_wet_or_new_dry_adapter_required')
            require(len(self.column.storages) == 1 and self.column.storages[0] is shared.storage
                    and self.column.storages[0].volume is shared.volume,
                    'same_declared_live_storage_and_volume_required')
            require(not result.get('outer_timeout_requested'), 'outer_timeout_already_requested')
            require(len(result['captures']) < TOTAL_CALLBACK_CAP, 'total_source_callback_cap')
            item = dict(ordinal=len(result['captures'])+1, phase=phase_name,
                packed_input=encode(packed), time=encode(at), operator_identity=encode(self.operator_identity),
                energy_identity=encode(self.energy_model_identity), interface_modes=encode(self.interfaces),
                same_object_as_initial_adapter=self is adapter,
                same_declared_storage_object=self.column.storages[0] is shared.storage,
                same_declared_volume_object=self.column.storages[0].volume is shared.volume)
            result['captures'].append(item)
            save()
            try:
                value = actual(self, packed, at)
                item['evaluation'] = encode(value)
                save()
                return value
            except Exception as exc:
                item.update(exception_type=type(exc).__name__, exception=str(exc))
                save()
                raise

        original_candidate = transition_module.execute_source_dry_candidate

        def retained_candidate(*args, **kwargs):
            nonlocal phase_name
            phase_name = 'coarse_dry_candidate' if not result['returned_candidates'] else 'shifted_dry_candidate'
            candidate = original_candidate(*args, **kwargs)
            # Persist the returned object before the outer comparison can fail.
            result['returned_candidates'].append(encode(candidate))
            if candidate.terminal is not None:
                result.setdefault('dry_adapter_provenance', []).append(encode(candidate.terminal.dry_adapter.provenance()))
            save()
            return candidate

        with patch.object(ExactSourceColumn, 'evaluate', observed):
            first = adapter.evaluate(initial, T(F()))
            phase = first.source_evaluation.cells[0].phase.phase_water_mol_s
            result['initial_phase_water_mol_s'] = encode(phase)
            save()
            require(math.isfinite(phase) and phase > 0, 'initial_phase_not_positive')
            horizon = F(3, 2)*F(state.liquid_water_mol)/F(phase)
            require(math.isfinite(float(horizon)) and float(horizon) > 0, 'unrepresentable_horizon')
            policy = IntegrationPolicy(float(horizon), float(horizon), 2**-30,
                1e-8, 1e-7, 1e-3, 1., 1e5, 4, 4, 180.)
            source_mass = chemical.reference.molar_mass_kg_mol
            require(_same(source_mass, storage.water.reference.molar_mass_kg_mol), 'actual_shared_water_molar_mass')
            rounding = DepletionRoundoffPolicy(correction_absolute_mol=1e-15,
                correction_fraction_evaporated=1e-8, storage_absolute_mol=1e-15,
                cumulative_storage_absolute_mol=1e-14, element_absolute_mol=2e-15,
                cumulative_element_absolute_mol=2e-14, mass_absolute_kg=1e-16,
                cumulative_mass_absolute_kg=1e-15, cumulative_correction_absolute_mol=1e-14,
                molar_mass_kg_mol=source_mass)
            event = DepletionPolicy(time_absolute_s=1e-8, amount_absolute_mol=1e-11,
                energy_absolute_j=1e-7, temperature_absolute_k=1e-5, pressure_absolute_pa=1e-4,
                terminal_window_s=.001, maximum_refinements=32, roundoff_policy=rounding,
                terminal_method='affine_midpoint')
            result.update(horizon=encode(horizon), integration_policy=encode(policy), event_policy=encode(event),
                molar_mass_binding=dict(actual_source_kg_mol=source_mass, previous_test_literal_kg_mol=.018015268,
                    exact_difference_kg_mol=encode(F(source_mass)-F(.018015268)),
                    difference_in_previous_literal_ulps=encode((F(source_mass)-F(.018015268))/F(math.ulp(.018015268))),
                    source='actual_WaterChemicalPotential.reference.molar_mass_kg_mol', threshold_relaxation=False))
            save()
            phase_name = 'seed'
            seed = evaluate_source_prefix_trial(adapter, initial, start=T(F()), end=T(horizon),
                integration_policy=policy, maximum_callbacks=CALLBACK_CAP)
            result['seed'] = encode(seed)
            save()
            require(seed.reason == 'source_prefix_negative_inventory_minimum' and len(seed.captures) == 2,
                    'seed_requires_actual_first_mid_negative_prefix')
            proposal = propose_source_approach(seed, event_policy=event)
            result['proposal'] = encode(proposal)
            save()
            require(proposal.status == 'positive_numerical_proposal', 'no_positive_approach_proposal')
            phase_name = 'approach'
            approach = evaluate_source_approach(proposal, maximum_callbacks=CALLBACK_CAP)
            result['approach'] = encode(approach)
            save()
            require(approach.status == 'validated_positive_numerical_approach', 'actual_approach_not_validated')
            phase_name = 'shifted_seed'
            refinement = evaluate_source_root_refinement(approach, maximum_callbacks=CALLBACK_CAP)
            result['refinement'] = encode(refinement)
            result['requested_dry_common_end'] = encode(seed.end)
            save()
            require(refinement.clock is not None, 'independent_shifted_root_not_available')
            with patch.object(transition_module, 'execute_source_dry_candidate', retained_candidate):
                transition = transition_module.evaluate_source_dry_transition(refinement, end=seed.end,
                    maximum_callbacks_per_path=DRY_PATH_CALLBACK_CAP, shared_volume=shared)
            result['transition'] = encode(transition)
            result.update(numerical_comparison_completed=True,
                          numerical_event_accepted=transition.numerical_event_accepted)
            save()
        require(not result.get('outer_timeout_requested'), 'outer_timeout_after_transition')
        require(transition.material_qualified is False, 'no_material_qualification')
        require(len(result['captures']) == 1+len(seed.captures)+approach.new_evaluations
                +refinement.new_evaluations+sum(len(candidate.captures) for candidate in transition.candidates),
                'all_actual_attempts_retained')
        result.update(status='completed', all_actual_attempts_retained=True)
        save()
        print(json.dumps(dict(status=result['status'], callbacks=len(result['captures']),
            numerical_comparison_completed=True, numerical_event_accepted=transition.numerical_event_accepted,
            transition_status=transition.status, clock_gate=transition.clock_gate,
            endpoint_gates=transition.endpoint_gates, conditional_pressure_gates=transition.conditional_pressure_gates,
            selected_pressure_bounds_pa=[None if x is None else float(x) for x in transition.selected_pressure_bounds_pa],
            selected_pressure_gates=transition.selected_pressure_gates, pressure_strategy=transition.pressure_strategy,
            material_qualified=False, wall_seconds=result['wall_seconds'])))
        return 0
    except Exception as exc:
        result.update(status='resource_limit' if result.get('outer_timeout_requested') else 'failed',
                      exception_type=type(exc).__name__, exception=str(exc))
        # Retain completed trial/assessment/candidate objects from every known
        # source exception, including nested causes, without omitting evidence.
        chain, seen, current = [], set(), exc
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            entry = dict(exception_type=type(current).__name__, exception=str(current))
            if encode is not None:
                for name in ('stage', 'proposal', 'trial', 'comparison', 'pressure',
                             'records', 'refinement', 'candidate', 'candidates'):
                    if hasattr(current, name):
                        entry[name] = encode(getattr(current, name))
            chain.append(entry)
            current = current.__cause__ if current.__cause__ is not None else current.__context__
        result['exception_chain'] = chain
        save()
        print(json.dumps({key: result.get(key) for key in ('status', 'exception_type', 'exception', 'wall_seconds')}))
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        signal.signal(signal.SIGALRM, previous)


if __name__ == '__main__':
    sys.exit(run(*sys.argv[1:]))
