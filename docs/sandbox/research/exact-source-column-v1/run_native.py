"""Prepared one-shot exact-time source-liquid integration; no EOS at import."""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from fractions import Fraction as F
from pathlib import Path
import importlib.util
import json
import signal
import sys
import time

DURATION = F(1, 1024)
POLICY_VALUES = (1/1024, 1/1024, 1/16384, 1e-8, 1e-7, 1e-3, 1., 1e5, 4, 4, 450.)
OUTER_SECONDS = 510.


def serialize(value):
    import numpy as np
    if isinstance(value, F):
        return {'numerator': value.numerator, 'denominator': value.denominator}
    if isinstance(value, np.ndarray):
        return {'dtype': str(value.dtype), 'shape': list(value.shape), 'values': serialize(value.tolist())}
    if isinstance(value, np.generic):
        return serialize(value.item())
    if is_dataclass(value):
        return {'type': type(value).__module__+'.'+type(value).__qualname__,
                'fields': {f.name: serialize(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, Mapping):
        return {key: serialize(v) for key, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serialize(v) for v in value]
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise TypeError('unsupported_result_type:'+type(value).__name__)


def construct(root):
    path = Path(root)/'docs/sandbox/research/source-liquid-column-v1/run_native.py'
    spec = importlib.util.spec_from_file_location('archived_source_liquid_native', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    column, states, _, mobility_sha256 = module.construct(root)
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    adapter = ExactSourceColumn(column)
    return adapter, adapter.pack(states), mobility_sha256


def require(condition, reason):
    if not condition:
        raise AssertionError(reason)


def audit(adapter, run, captures, policy):
    import numpy as np
    count = adapter.column.cell_count
    fixed_mass = tuple(s.dry_mass_kg for s in adapter.column.storages)
    reports = []
    amount_limit = F(policy.amount_absolute_tolerance_mol)
    energy_limit = F(policy.energy_absolute_tolerance_j)
    cumulative_n = [[F() for _ in range(4)] for _ in range(count)]
    cumulative_u = [F() for _ in range(count)]
    require(len(captures) == run.evaluations, 'all_actual_evaluations_saved')
    require(len(run.steps)+1 == len(run.states), 'accepted_step_state_shape')
    for packed in run.states:
        require(packed.amounts_mol.shape == (count, 4), 'four_fluid_mol_columns')
        require(packed.mechanical_stretches is None, 'no_dynamic_mechanics')
        unpacked = adapter.unpack(packed)
        require(tuple(s.solid_mass_kg for s in unpacked) == tuple((m,) for m in fixed_mass), 'all_fixed_dry_kg_masses')
    for item in captures:
        output = item['evaluation']
        require(output.time == item['time'], 'exact_callback_time_preserved')
        require(np.array_equal(output.rates.face_species_mol_s[:, 0],
            np.array([getattr(f, 'liquid_mol_s', 0.) for f in output.source_evaluation.faces])), 'liquid_faces_mapped')
        require(output.rates.face_species_mol_s[0, 0] == output.rates.face_species_mol_s[-1, 0] == 0., 'closed_liquid_boundaries')
        require(np.all(output.rates.reaction_species_mol_s[:, 0]+output.rates.reaction_species_mol_s[:, 3] == 0.), 'opposite_water_phase_sources')
        require(np.all(output.rates.cell_power_w == 0.), 'no_extra_latent_power')
    for step_index, (old, new, ledger) in enumerate(zip(run.states, run.states[1:], run.steps)):
        require(ledger.stretch_increment is None, 'no_mechanical_ledger')
        require(ledger.face_species_mol[0, 0] == ledger.face_species_mol[-1, 0] == 0., 'zero_boundary_liquid_integral')
        local_n = []
        local_u = []
        local_water = []
        for i in range(count):
            row = []
            for j in range(4):
                term = F(float(ledger.face_species_mol[i, j]))-F(float(ledger.face_species_mol[i+1, j]))+F(float(ledger.reaction_species_mol[i, j]))
                residual = F(float(new.amounts_mol[i, j]))-F(float(old.amounts_mol[i, j]))-term
                require(abs(residual) <= amount_limit, 'local_amount_policy_roundoff')
                cumulative_n[i][j] += term
                cumulative_residual = F(float(new.amounts_mol[i, j]))-F(float(run.states[0].amounts_mol[i, j]))-cumulative_n[i][j]
                require(abs(cumulative_residual) <= amount_limit, 'cumulative_amount_policy_roundoff')
                row.append(residual)
            local_n.append(row)
            term_u = F(float(ledger.face_energy_j[i]))-F(float(ledger.face_energy_j[i+1]))+F(float(ledger.cell_work_j[i]))
            residual_u = F(float(new.internal_energy_j[i]))-F(float(old.internal_energy_j[i]))-term_u
            require(abs(residual_u) <= energy_limit, 'local_U_policy_roundoff')
            cumulative_u[i] += term_u
            require(abs(F(float(new.internal_energy_j[i]))-F(float(run.states[0].internal_energy_j[i]))-cumulative_u[i]) <= energy_limit, 'cumulative_U_policy_roundoff')
            local_u.append(residual_u)
            require(F(float(ledger.reaction_species_mol[i, 0]))+F(float(ledger.reaction_species_mol[i, 3])) == 0, 'phase_integral_cancels')
            local_water.append(row[0]+row[3])
        water = lambda state: sum((F(float(state.amounts_mol[i, 0]))+F(float(state.amounts_mol[i, 3])) for i in range(count)), F())
        boundary_water = sum((F(float(ledger.face_species_mol[0, j]))-F(float(ledger.face_species_mol[-1, j])) for j in (0, 3)), F())
        global_water_residual = water(new)-water(old)-boundary_water
        global_u_residual = sum(map(lambda v: F(float(v)), new.internal_energy_j), F())-sum(map(lambda v: F(float(v)), old.internal_energy_j), F())-F(float(ledger.face_energy_j[0]))+F(float(ledger.face_energy_j[-1]))-sum((F(float(v)) for v in ledger.cell_work_j), F())
        require(global_water_residual == sum(local_water, F()), 'global_water_matches_actual_local_residuals')
        require(global_u_residual == sum(local_u, F()), 'global_U_matches_actual_local_residuals')
        reports.append({'step_index': step_index, 'local_amount_residual_mol': local_n,
            'local_water_residual_mol': local_water, 'local_U_residual_j': local_u,
            'global_water_residual_mol': global_water_residual, 'global_U_residual_j': global_u_residual,
            'per_quantity_amount_policy_bound_mol': amount_limit, 'per_cell_U_policy_bound_j': energy_limit,
            'global_water_derived_bound_mol': 2*count*amount_limit, 'global_U_derived_bound_j': count*energy_limit})
    return {'accepted_ledgers': reports, 'callback_count': len(captures),
        'same_time_callbacks_preserved': True, 'roundoff_is_reported_not_assumed_zero': True,
        'material_qualified': False}


def main(root, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    captures = []
    result = {'status': 'started', 'material_qualified': False, 'policy_values': POLICY_VALUES,
              'duration_s': {'numerator': 1, 'denominator': 1024}, 'outer_seconds': OUTER_SECONDS,
              'captures': []}
    def save():
        result['wall_seconds'] = time.monotonic()-started
        temporary = output.with_suffix(output.suffix+'.pending')
        temporary.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
        temporary.replace(output)
    def timeout(*args):
        raise TimeoutError('outer_510s_budget_exceeded')
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, OUTER_SECONDS)
    save()
    try:
        from sludge_sandbox.integration import IntegrationPolicy, IntegrationError, DomainExit
        from sludge_sandbox.exact_event_clock import ExactEventTime
        from sludge_sandbox.exact_integration import integrate_exact
        adapter, initial, mobility_sha256 = construct(root)
        policy = IntegrationPolicy(*POLICY_VALUES)
        start, end = ExactEventTime(F()), ExactEventTime(DURATION)
        result.update(status='constructed', initial=serialize(initial), mobility_sha256=mobility_sha256,
            adapter_provenance=serialize(adapter.provenance()), policy=serialize(policy),
            build_seconds=time.monotonic()-started)
        save()
        def callback(packed, at):
            ordinal = len(captures)
            result['pending_callback'] = {'ordinal': ordinal, 'packed_input': serialize(packed), 'time': serialize(at)}
            save()
            try:
                evaluation = adapter.evaluate(packed, at)
            except (IntegrationError, DomainExit):
                raise
            except ValueError as exc:
                raise IntegrationError('source_column_callback:'+str(exc)) from exc
            captures.append({'ordinal': ordinal, 'packed_input': packed, 'time': at, 'evaluation': evaluation})
            result['captures'].append(serialize(captures[-1]))
            result.pop('pending_callback', None)
            save()
            return evaluation.rates
        run = integrate_exact(initial, callback, start_s=start, end_s=end, policy=policy,
                              breakpoints_s=adapter.breakpoints(start, end))
        # Preserve the native integrator result BEFORE unpack/audit can fail.
        result.update(status=run.status, integrator_result=serialize(run))
        save()
        result['final_unpacked_states'] = serialize(adapter.unpack(run.states[-1]))
        result['audit'] = serialize(audit(adapter, run, captures, policy))
        require(run.status == 'completed' and run.times_s[-1] == end, 'complete_original_segment_required')
        save()
        print(json.dumps({'status': run.status, 'accepted_steps': len(run.steps), 'callbacks': len(captures),
            'rejected_trials': run.rejected_trials, 'elapsed_seconds': run.elapsed_seconds, 'wall_seconds': result['wall_seconds']}))
        return 0
    except Exception as exc:
        result.update(status='failed', exception_type=type(exc).__name__, exception=str(exc))
        save()
        print(json.dumps({k: result.get(k) for k in ('status', 'exception_type', 'exception', 'wall_seconds')}))
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        signal.signal(signal.SIGALRM, previous)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
