"""One bounded HEOS/source-mass partitioned root/common-endpoint study.

Imports are passive; actual source callbacks and partial failures are saved.
This is an integration test, not a sludge-material qualification.
"""
from dataclasses import fields, replace
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
TOTAL_CALLBACK_CAP = 81  # One rate probe and five trials, each capped at 16.
HELPERS = {
    'source-wet-storage-v1/run_native.py': '9a8bbf40651c7dfc31e81c85e8367904e441e210f1c7b1666c9080dbc81b93a6',
    'exact-source-column-v1/run_native.py': 'b0b873960bdc8bc9f2299fc3d0d008fd5fa5a9d3f7a972eb0f080ec3a2d39ab5',
}


def run(root, output):
    root, output = Path(root), Path(output)
    started = time.monotonic()
    result = dict(status='started', material_qualified=False, event_admitted=False,
        scope='N1_partitioned_surrogate_roots_and_positive_common_reference_endpoints',
        outer_seconds=OUTER_SECONDS, per_trial_callback_cap=CALLBACK_CAP,
        total_callback_cap=TOTAL_CALLBACK_CAP, captures=[], backend_constructors_started=0,
        backend_constructors_completed=0, constructor_reference_anchor_checks=0,
        initial_energy_evaluations_attempted=0, helper_hashes=HELPERS)

    def save():
        result['wall_seconds'] = time.monotonic()-started
        pending = output.with_suffix('.pending')
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
        require(hashlib.sha256(path.read_bytes()).hexdigest()==HELPERS[name], 'constructor_changed:'+name)
        spec = importlib.util.spec_from_file_location('prepared_'+name.split('/')[0].replace('-','_'), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, OUTER_SECONDS)
    save()
    try:
        source = load_helper('source-wet-storage-v1/run_native.py')
        encode = load_helper('exact-source-column-v1/run_native.py').serialize
        from sludge_sandbox.depletion_integration import DepletionPolicy
        from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy
        from sludge_sandbox.exact_event_clock import ExactEventTime as T
        from sludge_sandbox.exact_source_column import ExactSourceColumn
        from sludge_sandbox.integration import IntegrationPolicy
        from sludge_sandbox.phase_storage import InversePolicy
        from sludge_sandbox.source_wet_column import SourceWetColumn
        from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
        from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial
        from sludge_sandbox.source_approach import (
            propose_source_approach, evaluate_source_approach, SourceApproachAssessmentError,
        )
        from sludge_sandbox.source_root_comparison import (
            evaluate_source_root_refinement,positive_source_common_end,
            evaluate_source_common_endpoint,SourceRootStudyError,
        )
        from sludge_sandbox.source_prefix_trial import SourcePrefixTrial
        from sludge_sandbox._heos_kernel import HEOSCandidate

        def record(value, omit=()):
            return {f.name: encode(getattr(value,f.name)) for f in fields(value) if f.name not in omit}

        def pressure_record(value):
            data = record(value,('comparison','endpoint_bounds'))
            data['endpoint_bounds'] = [[record(bound,('storage',)) for bound in pair]
                                       for pair in value.endpoint_bounds]
            return data

        original_init = HEOSCandidate.__init__

        def counted_init(self,*args,**kwargs):
            result['backend_constructors_started'] += 1
            save()
            original_init(self,*args,**kwargs)
            result['backend_constructors_completed'] += 1
            # Each manifest-checked successful constructor performs one native
            # reference-anchor check. This is not all internal EOS updates.
            result['constructor_reference_anchor_checks'] += 1
            save()

        with patch.object(HEOSCandidate,'__init__',counted_init):
            storage, _ = source.make_case(root)
            waterdir = root/'data/sandbox/water'
            chemical = WaterChemicalPotential(waterdir, backend='heos',
                backend_manifest=waterdir/'heos-8.0.0-approved-manifest.json')
        require(result['backend_constructors_started']==result['backend_constructors_completed']==4,
                'four_actual_provider_constructors')
        # N1 has no interior face; no manufactured mobility is required.
        column = SourceWetColumn((storage,), (InversePolicy(1e-5,1e-6,100),), chemical,
            (1e-9,), (), (.25,), .01, ('existing_liquid',),
            ('manufactured:source-column-transport',))
        state = storage.state(1e-6,(.125,.25,1e-12),0.)
        result.update(initial_unset_energy=encode(state), initial_temperature_k=325.,
                      initial_energy_evaluations_attempted=1)
        save()
        point = storage.evaluate(state,325.)
        state = replace(state,internal_energy_j=point.total_internal_energy_j)
        adapter = ExactSourceColumn(column)
        initial = adapter.pack((state,))
        result.update(status='constructed', initial_energy_point=encode(point), initial=encode(initial),
            adapter_provenance=encode(adapter.provenance()), build_seconds=time.monotonic()-started)
        save()
        actual = ExactSourceColumn.evaluate
        phase_name = 'initial_rate_probe'

        def observed(self,state,at):
            require(self is adapter, 'only_prepared_adapter')
            require(not result.get('outer_timeout_requested'), 'outer_timeout_already_requested')
            require(len(result['captures'])<TOTAL_CALLBACK_CAP, 'total_source_callback_cap')
            item = dict(ordinal=len(result['captures'])+1, phase=phase_name,
                        packed_input=encode(state), time=encode(at))
            result['captures'].append(item)
            save()
            try:
                value = actual(self,state,at)
                item['evaluation'] = encode(value)
                save()
                return value
            except Exception as exc:
                item.update(exception_type=type(exc).__name__, exception=str(exc))
                save()
                raise

        with patch.object(ExactSourceColumn,'evaluate',observed):
            first = adapter.evaluate(initial,T(F()))
            phase = first.source_evaluation.cells[0].phase.phase_water_mol_s
            result['initial_phase_water_mol_s'] = phase
            save()
            require(math.isfinite(phase) and phase>0, 'initial_phase_not_positive')
            horizon = F(3,2)*F(state.liquid_water_mol)/F(phase)
            require(math.isfinite(float(horizon)) and float(horizon)>0, 'unrepresentable_horizon')
            policy = IntegrationPolicy(float(horizon),float(horizon),2**-30,
                1e-8,1e-7,1e-3,1.,1e5,4,4,180.)
            rounding = DepletionRoundoffPolicy(correction_absolute_mol=1e-15,
                correction_fraction_evaporated=1e-8,storage_absolute_mol=1e-15,
                cumulative_storage_absolute_mol=1e-14,element_absolute_mol=2e-15,
                cumulative_element_absolute_mol=2e-14,mass_absolute_kg=1e-16,
                cumulative_mass_absolute_kg=1e-15,cumulative_correction_absolute_mol=1e-14,
                molar_mass_kg_mol=.018015268)
            event = DepletionPolicy(time_absolute_s=1e-8,amount_absolute_mol=1e-11,
                energy_absolute_j=1e-7,temperature_absolute_k=1e-5,pressure_absolute_pa=1e-4,
                terminal_window_s=.001,maximum_refinements=32,roundoff_policy=rounding)
            result.update(horizon=encode(horizon), integration_policy=encode(policy), event_policy=encode(event))
            save()
            phase_name = 'seed'
            seed = evaluate_source_prefix_trial(adapter,initial,start=T(F()),end=T(horizon),
                integration_policy=policy,maximum_callbacks=CALLBACK_CAP)
            result['seed'] = record(seed,('adapter',))
            save()
            require(not result.get('outer_timeout_requested'), 'outer_timeout_after_seed')
            seed.check()
            require(seed.reason=='source_prefix_negative_inventory_minimum' and len(seed.captures)==2,
                    'prepared_seed_did_not_produce_actual_first_mid_negative_prefix')
            proposal = propose_source_approach(seed,event_policy=event)
            result['proposal'] = record(proposal,('original_trial',))
            save()
            require(proposal.status=='positive_numerical_proposal', 'no_positive_approach_proposal')
            phase_name = 'approach'
            try:
                out = evaluate_source_approach(proposal,maximum_callbacks=CALLBACK_CAP)
            except SourceApproachAssessmentError as exc:
                result.update(assessment_stage=exc.stage, trial=record(exc.trial,('adapter',)),
                    comparison=record(exc.comparison,('trial',)) if exc.comparison is not None else None,
                    pressure=pressure_record(exc.pressure) if exc.pressure is not None else None)
                save()
                raise
            result.update(trial=record(out.trial,('adapter',)) if out.trial is not None else None,
                comparison=record(out.comparison,('trial',)) if out.comparison is not None else None,
                pressure=pressure_record(out.pressure) if out.pressure is not None else None,
                approach=record(out,('proposal','trial','comparison','pressure')))
            save()
            require(out.status=='validated_positive_numerical_approach', 'initial_approach_not_validated')
            phase_name = 'shifted_seed'
            try:
                refinement = evaluate_source_root_refinement(out,maximum_callbacks=CALLBACK_CAP)
                result.update(root_refinement=record(refinement,('approach','shifted_trial','shifted_proposal')),
                    shifted_seed=record(refinement.shifted_trial,('adapter',)),
                    shifted_proposal=record(refinement.shifted_proposal,('original_trial',)))
                save()
                require(refinement.clock is not None, 'partitioned_roots_not_available:'+str(refinement.reason))
                require(not result.get('outer_timeout_requested'), 'outer_timeout_after_refinement')
                common_end = positive_source_common_end(refinement)
                result['requested_common_end'] = encode(common_end)
                save()
                phase_name = 'common_paths'
                common = evaluate_source_common_endpoint(refinement,end=common_end,
                    maximum_callbacks_per_trial=CALLBACK_CAP)
                result.update(common_comparison=record(common,('refinement','coarse_trial','shifted_trial','pressure_pairs')),
                    coarse_common_trial=record(common.coarse_trial,('adapter',)),
                    shifted_common_trial=record(common.shifted_trial,('adapter',)),
                    common_pressure_pairs=[[record(bound,('storage',)) for bound in pair] for pair in common.pressure_pairs])
                save()
            except SourceRootStudyError as exc:
                # Parent structures are saved above. Retain every newly returned
                # actual trial even when source callbacks or postprocessing fail.
                result.update(root_study_stage=exc.stage,failed_study_trials=[record(value,('adapter',))
                    for value in exc.records if type(value) is SourcePrefixTrial])
                save()
                raise
        result.update(trial=record(out.trial,('adapter',)) if out.trial is not None else None,
            comparison=record(out.comparison,('trial',)) if out.comparison is not None else None,
            pressure=pressure_record(out.pressure) if out.pressure is not None else None,
            approach=record(out,('proposal','trial','comparison','pressure')))
        save()
        require(not result.get('outer_timeout_requested'), 'outer_timeout_after_approach')
        require(out.status=='validated_positive_numerical_approach', 'approach_not_validated:'+str(out.reason))
        require(len(result['captures'])==1+len(seed.captures)+out.new_evaluations
                +refinement.new_evaluations+common.new_evaluations, 'all_actual_attempts_retained')
        require(out.trial.end==proposal.end and out.trial.reference.times_s[-1]==proposal.end,
                'fresh_trial_and_reference_same_proposed_end')
        require(out.trial.captures[1].time!=seed.captures[1].time, 'fresh_midpoint_required')
        require(out.trial.prefix.raw_state.amounts_mol[0,0]>0, 'positive_new_liquid')
        result.update(status='completed', all_actual_attempts_retained=True)
        save()
        print(json.dumps(dict(status=result['status'], callbacks=len(result['captures']),
            seed_status=seed.status, horizon_s=float(horizon), approach_s=float(proposal.choice.duration_s),
            discrepancy=out.trial.discrepancy, approach_seconds=out.trial.elapsed_seconds,
            root_distance_lower_s=float(refinement.clock.distance_lower_s),
            root_distance_upper_s=float(refinement.clock.distance_upper_s),
            clock_gate=refinement.clock.gate, common_end_s=float(common_end.seconds),
            common_endpoint_gates=common.gates, conditional_pressure_gate=common.conditional_pressure_gate,
            wall_seconds=result['wall_seconds'])))
        return 0
    except Exception as exc:
        result.update(status='resource_limit' if result.get('outer_timeout_requested') else 'failed',
                      exception_type=type(exc).__name__, exception=str(exc))
        save()
        print(json.dumps({k:result.get(k) for k in ('status','exception_type','exception','wall_seconds')}))
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL,0.)
        signal.signal(signal.SIGALRM,previous)


if __name__=='__main__':
    sys.exit(run(*sys.argv[1:]))
