"""Explicit paired record schemas/costs and data-only audit regressions; no EOS."""
from dataclasses import replace
from fractions import Fraction as F
import copy
import pytest
from sludge_sandbox import event_record as m
from test_event_record import run


def test_optin_endpoint_costs_select_v2_even_before_first_comparison():
 result,_,_,_=run()
 costs={key:dict(value) for key,value in result.phase_costs.items()}
 costs['comparison'].update(endpoint_attempts=0,endpoint_completed=0)
 changed=replace(result,phase_costs=costs)
 assert m.encode_depletion_result(changed,original_interfaces=('existing_liquid',))['schema']=='sandbox_depletion_result_v2'
 assert m.encode_depletion_result(result,original_interfaces=('existing_liquid',))['schema']=='sandbox_depletion_result_v1'


@pytest.mark.parametrize('attempts,completed,valid',[(2,1,True),(0,0,True),(1,2,False),(-1,0,False),(True,0,False)])
def test_endpoint_costs_attempt_completion_contract(attempts,completed,valid):
 costs={'endpoint_attempts':attempts,'endpoint_completed':completed}
 if valid:m.audit_endpoint_costs(costs,[])
 else:
  with pytest.raises(m.EventRecordError):m.audit_endpoint_costs(costs,[])


def test_recorded_refinement_cost_cannot_exceed_original_cumulative_cost():
 with pytest.raises(m.EventRecordError):
  m.audit_endpoint_costs({'endpoint_attempts':3,'endpoint_completed':2},
   [{'endpoint_attempts':2,'endpoint_completed':1},{'endpoint_attempts':2,'endpoint_completed':1}])


def paired_fixture(monkeypatch):
    """Real pure certificate audit with an explicitly synthetic operator binding."""
    from dataclasses import dataclass
    from types import SimpleNamespace
    from test_pressure_comparison import fixture
    from sludge_sandbox import pressure_comparison as helper
    policy, saved_state, binding, pair = fixture()
    binding['interfaces'] = ['existing_liquid']

    @dataclass
    class Host:
        energy_model_identity: object = None

        def _check_state(self, point):
            assert point.amounts_mol.shape == (1, 3)

    @dataclass
    class Operator:
        base_model: object
        interface_modes: tuple = ('existing_liquid',)
        liquid_index: int = 2

    operator = Operator(Host())
    monkeypatch.setattr(m, 'WaterPhaseTransfer', Operator)
    monkeypatch.setattr(helper, 'pressure_comparison_binding', lambda actual: copy.deepcopy(binding))
    details = {}
    for where in ('event', 'common'):
        for field, differences in (('amounts', [[0., 0., 0.]]), ('energy', [0.]), ('stretches', [0., 0.])):
            details[where+'_'+field] = {'absolute_differences': differences}
        details[where+'_observations'] = {
            'temperature_nominal_difference_k': 0., 'pressure_nominal_difference_pa': 0.,
            'temperature_errors_a_k': [.01], 'temperature_errors_b_k': [.01],
            'pressure_errors_a_pa': [5.], 'pressure_errors_b_pa': [5.],
        }
    details['pressure_comparison'] = {
        'schema': policy.schema, 'original_independent_pressure_difference_pa': 10.,
        'selected_pressure_difference_pa': pair['bound_pa'],
        'pairs': {'event': copy.deepcopy(pair), 'common': copy.deepcopy(pair)},
    }
    ref = SimpleNamespace(comparison_details=details,
                          phase_costs={'comparison': {'endpoint_attempts': 8, 'endpoint_completed': 8}})
    return policy, operator, ref


def test_real_pure_pair_audit_binds_both_comparisons(monkeypatch):
    policy, operator, ref = paired_fixture(monkeypatch)
    assert m.audit_paired_refinement(ref, policy, operator, 10.) == ref.comparison_details['pressure_comparison']['selected_pressure_difference_pa']


@pytest.mark.parametrize('mutation', ['missing_common', 'state_difference', 'pressure_error',
                                    'temperature_error', 'nominal_difference', 'original_bound',
                                    'selected_bound', 'completed_cost', 'interface', 'certificate'])
def test_refinement_external_binding_rejects_tamper(monkeypatch, mutation):
    policy, operator, ref = paired_fixture(monkeypatch)
    d = ref.comparison_details
    payload = d['pressure_comparison']
    if mutation == 'missing_common': del payload['pairs']['common']
    elif mutation == 'state_difference': d['common_amounts']['absolute_differences'][0][0] = 1.
    elif mutation == 'pressure_error': d['event_observations']['pressure_errors_b_pa'][0] = 6.
    elif mutation == 'temperature_error': d['common_observations']['temperature_errors_a_k'][0] = .02
    elif mutation == 'nominal_difference': d['common_observations']['temperature_nominal_difference_k'] = 1.
    elif mutation == 'original_bound': payload['original_independent_pressure_difference_pa'] = 9.
    elif mutation == 'selected_bound': payload['selected_pressure_difference_pa'] = 0.
    elif mutation == 'completed_cost': ref.phase_costs['comparison']['endpoint_completed'] = 7
    elif mutation == 'interface': payload['pairs']['common']['bindings_b']['interfaces'] = ['depleted_no_nucleation']
    elif mutation == 'certificate': payload['pairs']['event']['cells'][0]['certificate']['exact_bound_pa']['numerator'] += 1
    with pytest.raises(ValueError): m.audit_paired_refinement(ref, policy, operator, 10.)


def test_chosen_pair_must_equal_committed_state(monkeypatch):
    from types import SimpleNamespace
    policy, operator, ref = paired_fixture(monkeypatch)
    ref.status = 'comparison_pass'; ref.event_time_s = .1; ref.common_time_s = .2
    ref.start_s = 0.; ref.level = 1
    actual = m.state(ref.comparison_details['pressure_comparison']['pairs']['event']['states'][1])
    event = SimpleNamespace(time_s=.1, common_time_s=.2)
    result = SimpleNamespace(refinements=(ref,), events=(event,), times_s=(.1, .2), states=(actual, actual))
    m.audit_paired_committed_binding(result)
    changed = copy.deepcopy(ref.comparison_details['pressure_comparison']['pairs']['event']['states'][1])
    changed['internal_energy_j'][0] += 1.
    result.states = (m.state(changed), actual)
    with pytest.raises(ValueError, match='committed_paired_state'): m.audit_paired_committed_binding(result)


@pytest.mark.parametrize('explicit_none', [False, True])
def test_legacy_policy_missing_or_null_roundtrips(explicit_none):
    import json
    result, initial, policy, event_policy = run()
    raw = m.encode_depletion_result(result, original_interfaces=('existing_liquid',))
    audited = m.audit_depletion_record(raw, initial, policy, event_policy, ('existing_liquid',),
                                      operator=result.operator, start_s=0., end_s=.05)
    saved = json.loads(audited.original_policy_json)
    assert 'pressure_comparison' not in saved['event_policy']
    if explicit_none: saved['event_policy']['pressure_comparison'] = None
    restored = m.AuditedDepletionRecord(audited.record_json, m.canonical(saved)).restore_result(result.operator)
    assert m.encode_depletion_result(restored, original_interfaces=('existing_liquid',)) == raw


def test_typed_paired_policy_restoration_calls_full_audit(monkeypatch):
    """Parser seam only: audit sentinel checks typed original policy is passed."""
    import json
    from test_pressure_comparison import policy as paired_policy
    result, initial, policy, event_policy = run()
    raw = m.encode_depletion_result(result, original_interfaces=('existing_liquid',))
    audited = m.audit_depletion_record(raw, initial, policy, event_policy, ('existing_liquid',),
                                      operator=result.operator, start_s=0., end_s=.05)
    saved = json.loads(audited.original_policy_json)
    saved['event_policy']['pressure_comparison'] = paired_policy().to_record()
    captured = []
    def audit_sentinel(record, original, integration_policy, restored_policy, *args, **kwargs):
        captured.append(restored_policy.pressure_comparison)
        raise m.EventRecordError('full_audit_called')
    monkeypatch.setattr(m, 'audit_depletion_record', audit_sentinel)
    with pytest.raises(m.EventRecordError, match='full_audit_called'):
        m.AuditedDepletionRecord(audited.record_json, m.canonical(saved)).restore_result(result.operator)
    assert captured == [paired_policy()]
