"""Original six-gate record comparison audit, without resume authority."""
from dataclasses import dataclass, replace
from fractions import Fraction as F
from collections.abc import Mapping
import math
import numpy as np
from sludge_sandbox.exact_record import EvidenceNode, ExactRunRecord, pack, validate_binding
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.exact_free_host import ExactFreeWaterTransfer
from sludge_sandbox.integration import ConservedState, IntegrationPolicy
from sludge_sandbox.depletion_integration import DepletionPolicy
from sludge_sandbox.pressure_comparison import audit_pressure_comparison, pressure_comparison_binding

class ComparisonAuditError(ValueError):
    """Original comparison evidence is invalid or unbound."""

def require(ok, reason):
    if not ok:
        raise ComparisonAuditError(reason)

def compact(value):
    """Lossless projection of already typed evidence; floats stay binary64 values."""
    if type(value) is EvidenceNode:
        result = {k: compact(v) for k, v in value.values.items()}
        if value.kind == 'OperatorReference':
            result['schema'] = 'research_exact_operator_reference_v1'
        if value.kind == 'Observation':
            result['schema'] = 'research_depletion_observation_v1'
        return result
    if type(value) is F:
        return {'numerator': value.numerator, 'denominator': value.denominator}
    if type(value) is ExactEventTime:
        return {'seconds': compact(value.seconds)}
    if isinstance(value, Mapping):
        return {k: compact(v) for k, v in value.items()}
    if type(value) is tuple:
        return [compact(v) for v in value]
    if type(value) is np.ndarray:
        return value.tolist()
    require(value is None or type(value) in (str, int, float, bool), 'projection_type')
    return value

def q(value):
    if type(value) is dict:
        require(set(value) == {'numerator', 'denominator'}, 'rational_fields')
        n, d = (value['numerator'], value['denominator'])
        require(type(n) is int and type(d) is int and (d > 0) and (math.gcd(n, d) == 1), 'canonical_rational')
        return F(n, d)
    require(type(value) in (int, float) and math.isfinite(value), 'finite_number')
    return F(value)

def same_typed(a,b):
    if type(a) is not type(b):return False
    if type(a) is list:return len(a)==len(b) and all(same_typed(x,y) for x,y in zip(a,b))
    if type(a) is dict:return set(a)==set(b) and all(same_typed(a[k],b[k]) for k in a)
    return a==b


def t(value):
    return q(value['seconds'])

@dataclass(frozen=True)
class ExactComparisonAudit:
    record_sha256: str
    committed_packets: int
    comparisons: int
    pressure_certificates: int
    saved_endpoint_calls: int
    scope: str = 'partial_audit_original_comparison_gates'
    resume_authorized: bool = False
    missing_gates: tuple = ('full_prefix_accounting', 'root_order_and_fullpanel_proofs', 'original_attempt_resource_budget_and_resume')

def state(v):
    return ConservedState(v['amounts_mol'], v['internal_energy_j'], None if v['energy_model_identity'] is None else tuple(v['energy_model_identity']), mechanical_stretches=v['mechanical_stretches'])

def diffs(a, b):
    require(len(a) == len(b), 'comparison_contract:len(a) == len(b)')
    return [diffs(x, y) if isinstance(x, list) else abs(x - y) for x, y in zip(a, b)]

def flat(v):
    for x in v:
        if isinstance(x, list):
            yield from flat(x)
        else:
            yield x

def maximum(a, b):
    return max(flat(diffs(a, b)))

def observation(v, n):
    require(v['schema'] == 'research_depletion_observation_v1', "comparison_contract:v['schema'] == 'research_depletion_observation_v1'")
    for key in ('temperatures_k', 'temperature_errors_k', 'pressures_pa', 'pressure_errors_pa'):
        require(len(v[key]) == n and all((type(x) in (int, float) and math.isfinite(x) for x in v[key])), 'comparison_contract:len(v[key]) == n and all((type(x) in (int, float) and math.isfinite(x) for x in v[key]))')
    require(all((x >= 0 for key in ('temperature_errors_k', 'pressure_errors_pa') for x in v[key])), "comparison_contract:all((x >= 0 for key in ('temperature_errors_k', 'pressure_errors_pa') for x in v[key]))")

def time_error(frame):
    a = frame['terminal']
    i = a['root_order']['selected_cell']
    e = next((x['evidence'] for x in a['root_order']['candidates'] if x['cell_index'] == i))
    require(e['lower'] == a['observations'][-1]['time'], "comparison_contract:e['lower'] == a['observations'][-1]['time']")
    s = e['samples']
    h = t(e['lower']) - t(s['start'])
    hm = t(s['midpoint']) - t(s['start'])
    require(h >= 0 and hm > 0 and t(e['upper']) > t(e['lower']), 'ordered_affine_clock_interval')
    r = sum(map(q, s['liquid_rates_start_mol_s']), F())
    acc = (sum(map(q, s['liquid_rates_mid_mol_s']), F()) - r) / hm
    val = q(s['start_inventory_mol']) + r * h + acc * h * h / 2
    require(val >= 0, 'comparison_contract:val >= 0')
    return F() if val == 0 else t(e['upper']) - t(e['lower'])

def _paired_bound(record,sa,oa,sb,ob,*,policy,binding_a,binding_b):
    require(same_typed(record['states'],[sa,sb]),'paired_actual_states')
    require(same_typed(record['bindings_a'],binding_a) and same_typed(record['bindings_b'],binding_b),'paired_actual_bindings')
    require(len(record['cells'])==len(sa['amounts_mol'])==len(sb['amounts_mol']),'paired_all_cells')
    for i,cell in enumerate(record['cells']):
        for key,vec in [('reported_pressures_pa','pressures_pa'),('reported_temperatures_k','temperatures_k'),('original_pressure_errors_pa','pressure_errors_pa'),('original_temperature_errors_k','temperature_errors_k')]:
            require(list(map(q,cell[key]))==[F(oa[vec][i]),F(ob[vec][i])],'paired_actual_observations')
    return audit_pressure_comparison(record,policy=policy,state_a=state(sa),state_b=state(sb),bindings_a=binding_a,bindings_b=binding_b)


def audit_exact_comparisons(record: ExactRunRecord, actual_original_operator: ExactFreeWaterTransfer, *, original_initial: ConservedState, start: ExactEventTime, end: ExactEventTime, integration_policy: IntegrationPolicy, event_policy: DepletionPolicy, case_sha256: str, runtime_identity: Mapping) -> ExactComparisonAudit:
    require(type(original_initial) is ConservedState and type(integration_policy) is IntegrationPolicy and (type(event_policy) is DepletionPolicy), 'external_original_types')
    require(type(start) is ExactEventTime and type(end) is ExactEventTime,'external_exact_time_types')
    checked = validate_binding(record, actual_original_operator, case_sha256=case_sha256, runtime_identity=runtime_identity)
    require(checked.start == start and checked.end == end and (pack(checked.states[0]) == pack(original_initial)), 'external_initial_interval')
    require(pack(checked.result.initial_policy) == pack(integration_policy) and pack(checked.result.event_policy) == pack(event_policy), 'external_original_policies')
    r = compact(checked.result)
    ep = compact(checked.result.event_policy)
    ip = compact(checked.result.initial_policy)
    n = len(original_initial.amounts_mol)
    pc = ep.get('pressure_comparison')
    pressure_policy = event_policy.pressure_comparison
    pure_certificates = 0
    recorded_endpoint_calls = 0
    binding_cache = {tuple(actual_original_operator.operator.interfaces): (actual_original_operator, pressure_comparison_binding(actual_original_operator.operator) if pc else None)}

    def op_binding(view):
        require(view['schema'] == 'research_exact_operator_reference_v1', 'operator_projection')
        modes = tuple(view['modes'])
        if modes not in binding_cache:
            current = replace(actual_original_operator.operator, interface_modes=modes)
            binding_cache[modes] = (ExactFreeWaterTransfer(current), pressure_comparison_binding(current) if pc else None)
        current, _ = binding_cache[modes]
        require(compact(current._identity) == view['identity'], 'actual_mode_identity')
        return current._identity[1]

    def binding_static(binding, view):
        op_binding(view)
        require(same_typed(binding, binding_cache[tuple(view['modes'])][1]), 'actual_complete_pressure_binding')

    def path_checks(path):
        require(len(path['times']) == len(path['states']) == len(path['steps']) + 1, "comparison_contract:len(path['times']) == len(path['states']) == len(path['steps']) + 1")
        op_binding(path['operator'])
        first_event = t(path['frames'][0]['terminal']['observations'][-1]['time']) if path['frames'] else None
        expected = [when for when in path['times'][1:] if first_event is None or t(when) < first_event]
        require(path['approach_grid'] == expected, "comparison_contract:path['approach_grid'] == expected")
        for f in path['frames']:
            attempt = f['terminal']
            require(attempt['status'] == 'speculative_completed', "comparison_contract:attempt['status'] == 'speculative_completed'")
            require(attempt['observations'][0]['state'] == attempt['initial_state'], "comparison_contract:attempt['observations'][0]['state'] == attempt['initial_state']")
            require(attempt['observations'][1]['state'] == attempt['predictor_panel']['raw_state'], "comparison_contract:attempt['observations'][1]['state'] == attempt['predictor_panel']['raw_state']")
            require(attempt['observations'][-1]['state'] == attempt['corrected_state'], "comparison_contract:attempt['observations'][-1]['state'] == attempt['corrected_state']")
            before = attempt['original_operator']
            after = attempt['candidate_operator']
            op_binding(before)
            op_binding(after)
            modes = before['modes'].copy()
            modes[attempt['root_order']['selected_cell']] = 'depleted_no_nucleation'
            require(after['modes'] == modes, "comparison_contract:after['modes'] == modes")
            require(attempt['observations'][-1]['evaluation']['interface_modes'] == modes, "comparison_contract:attempt['observations'][-1]['evaluation']['interface_modes'] == modes")
            idx = path['times'].index(attempt['observations'][-1]['time'])
            require(path['states'][idx] == attempt['corrected_state'] and path['steps'][idx - 1] == attempt['terminal_panel']['ledger'], "comparison_contract:path['states'][idx] == attempt['corrected_state'] and path['steps'][idx - 1] == attempt['terminal_panel']['ledger']")

    def paired(record, sa, oa, va, sb, ob, vb):
        nonlocal pure_certificates, recorded_endpoint_calls
        require(record['states'] == [sa, sb], "comparison_contract:record['states'] == [sa, sb]")
        binding_static(record['bindings_a'], va)
        binding_static(record['bindings_b'], vb)
        bound = _paired_bound(record,sa,oa,sb,ob,policy=pressure_policy,binding_a=binding_cache[tuple(va['modes'])][1],binding_b=binding_cache[tuple(vb['modes'])][1])
        pure_certificates += len(record['cells'])
        recorded_endpoint_calls += record['endpoint_evaluations']
        return bound
    gates = [F(ep['time_absolute_s']), ep['amount_absolute_mol'], ep['energy_absolute_j'], ep['temperature_absolute_k'], ep['pressure_absolute_pa'], ip['stretch_absolute_tolerance']]

    def comparison(ref, a, b):
        require(a['times'][0] == b['times'][0] and a['states'][0] == b['states'][0], "comparison_contract:a['times'][0] == b['times'][0] and a['states'][0] == b['states'][0]")
        common = ref['common_time']
        require(a['times'][-1] == b['times'][-1] == common, "comparison_contract:a['times'][-1] == b['times'][-1] == common")
        require([f['terminal']['root_order']['selected_cell'] for f in a['frames']] == [f['terminal']['root_order']['selected_cell'] for f in b['frames']], "comparison_contract:[f['terminal']['root_order']['selected_cell'] for f in a['frames']] == [f['terminal']['root_order']['selected_cell'] for f in b['frames']]")
        require(a['operator']['modes'] == b['operator']['modes'] and len(ref['comparison']) == len(a['frames']) > 0, "comparison_contract:a['operator']['modes'] == b['operator']['modes'] and len(ref['comparison']) == len(a['frames']) > 0")
        maxima = [F(), 0.0, 0.0, 0.0, 0.0, 0.0]
        for row, fa, fb in zip(ref['comparison'], a['frames'], b['frames']):
            ea, eb = (fa['terminal']['observations'][-1], fb['terminal']['observations'][-1])
            require(row['event_a'] == ea and row['event_b'] == eb, "comparison_contract:row['event_a'] == ea and row['event_b'] == eb")
            ca, cb = (row['common_a'], row['common_b'])
            sa, sb = (a['states'][-1], b['states'][-1])
            require(row['common_state_a'] == sa and row['common_state_b'] == sb, "comparison_contract:row['common_state_a'] == sa and row['common_state_b'] == sb")
            va, vb = (ea['evaluation'], eb['evaluation'])
            for ob in (va, vb, ca, cb):
                observation(ob, n)
            require(ca['interface_modes'] == a['operator']['modes'] and cb['interface_modes'] == b['operator']['modes'], "comparison_contract:ca['interface_modes'] == a['operator']['modes'] and cb['interface_modes'] == b['operator']['modes']")
            for prefix, x, y in [('event', ea['state'], eb['state']), ('common', sa, sb)]:
                for short, key in [('amount', 'amounts_mol'), ('energy', 'internal_energy_j'), ('stretch', 'mechanical_stretches')]:
                    require(same_typed(row[prefix + '_' + short + '_differences'], diffs(x[key], y[key])), "comparison_contract:same_typed(row[prefix + '_' + short + '_differences'], diffs(x[key], y[key]))")
            dt = abs(t(ea['time']) - t(eb['time'])) + time_error(fa) + time_error(fb)
            thermal = lambda x, y: maximum(x['temperatures_k'], y['temperatures_k']) + max(x['temperature_errors_k']) + max(y['temperature_errors_k'])
            pressure = lambda x, y: maximum(x['pressures_pa'], y['pressures_pa']) + max(x['pressure_errors_pa']) + max(y['pressure_errors_pa'])
            temp = max(thermal(va, vb), thermal(ca, cb))
            independent = max(pressure(va, vb), pressure(ca, cb))
            require(type(row['independent_pressure_bound_pa']) is float and row['independent_pressure_bound_pa'] == independent, "comparison_contract:row['independent_pressure_bound_pa'] == independent")
            if pc:
                require(len(row['paired']) == 2, "comparison_contract:len(row['paired']) == 2")
                event_p = paired(row['paired'][0], ea['state'], va, fa['terminal']['candidate_operator'], eb['state'], vb, fb['terminal']['candidate_operator'])
                common_p = paired(row['paired'][1], sa, ca, a['operator'], sb, cb, b['operator'])
                selected = max(event_p, common_p)
            else:
                require(not row['paired'], "comparison_contract:not row['paired']")
                selected = independent
            values = [dt, max(maximum(ea['state']['amounts_mol'], eb['state']['amounts_mol']), maximum(sa['amounts_mol'], sb['amounts_mol'])), max(maximum(ea['state']['internal_energy_j'], eb['state']['internal_energy_j']), maximum(sa['internal_energy_j'], sb['internal_energy_j'])), temp, selected, max(maximum(ea['state']['mechanical_stretches'], eb['state']['mechanical_stretches']), maximum(sa['mechanical_stretches'], sb['mechanical_stretches']))]
            require(q(row['differences'][0]) == values[0] and same_typed(row['differences'][1:], values[1:]), "comparison_contract:q(row['differences'][0]) == values[0] and same_typed(row['differences'][1:], values[1:])")
            maxima = [max(x, y) for x, y in zip(maxima, values)]
        passed = all((math.isfinite(v) and v <= g for v, g in zip(maxima, gates)))
        require(ref['status'] == ('comparison_pass' if passed else 'comparison_fail'), "comparison_contract:ref['status'] == ('comparison_pass' if passed else 'comparison_fail')")
        return maxima
    refs = r['refinements']
    groups = []
    group = []
    results = {}
    for index, ref in enumerate(refs):
        if ref['role'] == 'terminal' and ref['status'] == 'coarse_reference':
            require(type(ref['level']) is int and ref['level']==0,'original_coarse_level')
            require(q(ref['approach_cap_s'])==min(F(ep['nested_approach']['maximum_step_s']),F(ip['maximum_step_s'])) and q(ref['safe_fraction'])==F(ep['safe_inventory_fraction']),'original_coarse_approach_controls')
            require(0<q(ref['terminal_cap_s'])<=F(ep['terminal_window_s']),'original_coarse_terminal_cap')
            if group:
                groups.append(group)
            group = []
        group.append((index, ref))
        if ref['path'] is not None:
            path_checks(ref['path'])
        if ref['comparison']:
            previous = refs[index - 1]
            require(previous['role'] == 'terminal' and previous['path'] is not None, "comparison_contract:previous['role'] == 'terminal' and previous['path'] is not None")
            if ref['role'] == 'independent':
                require(q(ref['approach_cap_s']) * 2 == q(previous['approach_cap_s']) and q(ref['safe_fraction']) * 2 == q(previous['safe_fraction']), "comparison_contract:q(ref['approach_cap_s']) * 2 == q(previous['approach_cap_s']) and q(ref['safe_fraction']) * 2 == q(previous['safe_fraction'])")
                require(ref['terminal_cap_s'] == previous['terminal_cap_s'] and ref['level'] == previous['level'], "comparison_contract:ref['terminal_cap_s'] == previous['terminal_cap_s'] and ref['level'] == previous['level']")
                require(ref['path']['approach_grid'] != previous['path']['approach_grid'], "comparison_contract:ref['path']['approach_grid'] != previous['path']['approach_grid']")
            else:
                require(ref['level'] == previous['level'] + 1 and q(ref['terminal_cap_s']) * 2 == q(previous['terminal_cap_s']), "comparison_contract:ref['level'] == previous['level'] + 1 and q(ref['terminal_cap_s']) * 2 == q(previous['terminal_cap_s'])")
                require(ref['approach_cap_s'] == previous['approach_cap_s'] and ref['safe_fraction'] == previous['safe_fraction'], "comparison_contract:ref['approach_cap_s'] == previous['approach_cap_s'] and ref['safe_fraction'] == previous['safe_fraction']")
            results[index] = comparison(ref, previous['path'], ref['path'])
    if group:
        groups.append(group)
    committed = 0
    for packet in r['packets']:
        matches = [g for g in groups if len(g) >= 4 and g[-1][1]['role'] == 'independent' and (g[-1][1]['status'] == 'comparison_pass') and ([x['terminal'] for x in g[-2][1]['path']['frames']] == [x['terminal'] for x in packet])]
        require(len(matches) == 1, 'comparison_contract:len(matches) == 1')
        anchored=matches[0]
        anchor=anchored[0][1]
        require(anchor['role']=='terminal' and anchor['status']=='coarse_reference'
                and type(anchor['level']) is int and anchor['level']==0
                and anchor['comparison'] is None and anchor['path'] is not None,
                'committed_original_coarse_anchor')
        require(q(anchor['approach_cap_s'])==min(F(ep['nested_approach']['maximum_step_s']),F(ip['maximum_step_s']))
                and q(anchor['safe_fraction'])==F(ep['safe_inventory_fraction'])
                and 0<q(anchor['terminal_cap_s'])<=F(ep['terminal_window_s']),
                'committed_original_coarse_controls')
        for position,(_,stage) in enumerate(anchored[1:-1],1):
            require(stage['role']=='terminal' and stage['status'] in ('comparison_pass','comparison_fail')
                    and type(stage['level']) is int and stage['level']==position
                    and stage['level']<=ep['maximum_refinements']
                    and bool(stage['comparison']) and stage['path'] is not None,
                    'committed_terminal_refinement_sequence')
        independent=anchored[-1][1]
        require(independent['role']=='independent' and independent['status']=='comparison_pass'
                and type(independent['level']) is int and independent['level']==anchored[-2][1]['level']
                and bool(independent['comparison']) and independent['path'] is not None,
                'committed_independent_sequence')
        g = matches[0]
        fine_i, fine = g[-1]
        chosen_i, chosen = g[-2]
        prev_i, previous = g[-3]
        coarse = g[0][1]
        require(chosen['status'] == previous['status'] == 'comparison_pass' and chosen['role'] == previous['role'] == 'terminal', "comparison_contract:chosen['status'] == previous['status'] == 'comparison_pass' and chosen['role'] == previous['role'] == 'terminal'")
        maximum_values = [max(a, b) for a, b in zip(results[chosen_i], results[fine_i])]
        for j, f in enumerate(packet):
            require(f['coarse_time'] == coarse['path']['frames'][j]['terminal']['observations'][-1]['time'], "comparison_contract:f['coarse_time'] == coarse['path']['frames'][j]['terminal']['observations'][-1]['time']")
            require(f['previous_time'] == previous['path']['frames'][j]['terminal']['observations'][-1]['time'] and f['common_time'] == chosen['common_time'], "comparison_contract:f['previous_time'] == previous['path']['frames'][j]['terminal']['observations'][-1]['time'] and f['common_time'] == chosen['common_time']")
            require(q(f['packet_maximum_differences'][0]) == maximum_values[0] and f['packet_maximum_differences'][1:] == maximum_values[1:], "comparison_contract:q(f['packet_maximum_differences'][0]) == maximum_values[0] and f['packet_maximum_differences'][1:] == maximum_values[1:]")
            endpoint = f['terminal']['observations'][-1]['time']
            idx = r['times_s'].index(endpoint)
            require(r['states'][idx] == f['terminal']['corrected_state'] and r['steps'][idx - 1] == f['terminal']['terminal_panel']['ledger'], "comparison_contract:r['states'][idx] == f['terminal']['corrected_state'] and r['steps'][idx - 1] == f['terminal']['terminal_panel']['ledger']")
        committed += 1
    require(recorded_endpoint_calls <= r['costs']['endpoint_completed'] <= r['costs']['endpoint_attempts'], "comparison_contract:recorded_endpoint_calls <= r['costs']['endpoint_completed'] <= r['costs']['endpoint_attempts']")
    if r['status'] == 'completed':
        require(recorded_endpoint_calls == r['costs']['endpoint_completed'] == r['costs']['endpoint_attempts'], "comparison_contract:recorded_endpoint_calls == r['costs']['endpoint_completed'] == r['costs']['endpoint_attempts']")
    validate_binding(checked, actual_original_operator, case_sha256=case_sha256, runtime_identity=runtime_identity)
    return ExactComparisonAudit(checked.sha256, committed, len(results), pure_certificates, recorded_endpoint_calls)
