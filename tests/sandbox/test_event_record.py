from dataclasses import replace
import json,copy
import pytest
from sludge_sandbox.depletion_integration import ManufacturedDepletionAdapter,DepletionEvaluation,integrate_depletion
from sludge_sandbox.integration import ConservedState,Rates
from test_depletion_integration import policies
import sludge_sandbox.event_record as m

def run():
 def callback(s,t,modes):
  sink=1. if modes[0]=='existing_liquid' else 0.
  rates=Rates([[0.,0.],[0.,0.]],[0.,0.],[[-sink,sink]],[1.],{'body':[1.]},mechanical_rates_per_s=[.1,.1])
  return DepletionEvaluation(rates,(sink,),(300.,),(0.,),(1e5,),(0.,))
 op=ManufacturedDepletionAdapter(evaluate_callback=callback,liquid_index=0,water_vapor_index=1,interfaces=('existing_liquid',),program_knots_s=(),source_ids=('manufactured:test',))
 initial=ConservedState([[.02,0.]],[300.],mechanical_stretches=[1.,1.])
 p,e=policies();p=replace(p,stretch_absolute_tolerance=1e-9,stretch_scale=1.)
 out=integrate_depletion(initial,op,start_s=0.,end_s=.05,integration_policy=p,event_policy=e)
 assert out.status=='completed',out.reason
 return out,initial,p,e

def test_roundtrip_and_reaudit():
 out,initial,p,e=run();record=m.encode_depletion_result(out,original_interfaces=('existing_liquid',))
 audited=m.audit_depletion_record(record,initial,p,e,('existing_liquid',),operator=out.operator,start_s=0.,end_s=.05)
 restored=audited.restore_result(out.operator)
 assert m.encode_depletion_result(restored,original_interfaces=('existing_liquid',))==record
 corrupt=copy.deepcopy(record);corrupt['cumulative_energy_j'][0]['numerator']+=1
 forged=m.AuditedDepletionRecord(m.canonical(corrupt),audited.original_policy_json)
 with pytest.raises(m.EventRecordError):forged.restore_result(out.operator)

@pytest.fixture(scope='module')
def affine_record():
 from test_depletion_spine import configured,oracle,initial
 p,e=configured();p=replace(p,relative_tolerance=1e-11);e=replace(e,terminal_method='affine_midpoint',amount_absolute_mol=1e-10)
 op,_=oracle(.002);start=initial()
 out=integrate_depletion(start,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e)
 assert out.status=='completed',out.reason
 record=m.encode_depletion_result(out,original_interfaces=op.interfaces)
 audited=m.audit_depletion_record(record,start,p,e,op.interfaces,operator=out.operator,start_s=0.,end_s=.2)
 return out,record,audited

def test_affine_roundtrip(affine_record):
 out,record,audited=affine_record
 assert m.encode_depletion_result(audited.restore_result(out.operator),original_interfaces=record['original_interfaces'])==record

@pytest.mark.parametrize('target',['cumulative','comparison','independent','clock','midpoint','mode','counter','source','correction'])
def test_affine_tamper_refused(affine_record,target):
 out,original,audited=affine_record;record=copy.deepcopy(original)
 if target=='cumulative':record['cumulative_amounts_mol'][0]['numerator']+=1
 if target=='comparison':record['events'][0]['common_energy_difference_j']=1.
 if target=='independent':record['refinements']=[r for r in record['refinements'] if r['status']!='independent_approach_pass']
 if target=='clock':record['events'][0]['terminal_evidence']['clock']['start_inventory_mol']*=2
 if target=='midpoint':record['events'][0]['terminal_evidence']['midpoint_state']['amounts_mol'][0][0]*=2
 if target=='mode':record['final_interfaces'][0]='existing_liquid'
 if target=='counter':record['attempted_steps']=-1
 if target=='source':record['operator_binding']['source_ids']=['other']
 if target=='correction':record['corrections']=[]
 with pytest.raises(m.EventRecordError):m.AuditedDepletionRecord(m.canonical(record),audited.original_policy_json).restore_result(out.operator)

def test_reversed_cell_order_events_roundtrip():
 from test_depletion_multicell import two_cell_oracle,initial_state
 original=two_cell_oracle()
 def callback(state,t,modes):
  import numpy as np
  viewed=ConservedState(state.amounts_mol[::-1],state.internal_energy_j[::-1])
  obs=original.evaluate_callback(viewed,t,modes[::-1]);r=obs.rates
  rates=Rates(-r.face_species_mol_s[::-1],-r.face_energy_w[::-1],r.reaction_species_mol_s[::-1],r.cell_power_w[::-1])
  return DepletionEvaluation(rates,obs.evaporation_mol_s[::-1],obs.temperatures_k[::-1],obs.temperature_errors_k[::-1],obs.pressures_pa[::-1],obs.pressure_errors_pa[::-1])
 op=replace(original,evaluate_callback=callback)
 old=initial_state();start=ConservedState(old.amounts_mol[::-1],old.internal_energy_j[::-1]);p,e=policies()
 out=integrate_depletion(start,op,start_s=0.,end_s=.012,integration_policy=p,event_policy=e)
 assert out.status=='completed',out.reason
 assert [ev.cell_index for ev in out.events]==[1,0]
 record=m.encode_depletion_result(out,original_interfaces=op.interfaces)
 audited=m.audit_depletion_record(record,start,p,e,op.interfaces,operator=out.operator,start_s=0.,end_s=.012)
 assert m.encode_depletion_result(audited.restore_result(out.operator),original_interfaces=op.interfaces)==record

@pytest.mark.parametrize('raw',[b'null',b'[]',b'{"x":1,"x":2}',b'{'])
def test_malformed_raw_refuses(affine_record,raw):
 out,_,audited=affine_record
 with pytest.raises(m.EventRecordError):m.AuditedDepletionRecord(raw,audited.original_policy_json).restore_result(out.operator)

def test_exact_zero_affine_has_no_correction():
 from test_depletion_integration import oracle
 p,e=policies();e=replace(e,terminal_method='affine_midpoint')
 start=ConservedState([[.03125,0.]],[600.]);op=oracle(a=1.)
 out=integrate_depletion(start,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e)
 assert out.status=='completed' and len(out.events)==1 and out.events[0].correction is None and not out.corrections
 record=m.encode_depletion_result(out,original_interfaces=op.interfaces)
 audited=m.audit_depletion_record(record,start,p,e,op.interfaces,operator=out.operator,start_s=0.,end_s=.2)
 assert m.encode_depletion_result(audited.restore_result(out.operator),original_interfaces=op.interfaces)==record

@pytest.mark.parametrize('target',['omit_correction','short_observation','negative_error'])
def test_affine_exact_endpoint_and_observation_guard(affine_record,target):
 out,original,audited=affine_record;record=copy.deepcopy(original)
 if target=='omit_correction':
  assert record['events'][0]['correction'] is not None
  record['events'][0]['correction']=None;record['corrections']=[]
 elif target=='short_observation':record['events'][0]['terminal_evidence']['initial_observation']['temperature_errors_k']=[]
 else:record['events'][0]['terminal_evidence']['initial_observation']['pressure_errors_pa']=[-1.]
 with pytest.raises(m.EventRecordError):m.AuditedDepletionRecord(m.canonical(record),audited.original_policy_json).restore_result(out.operator)

def test_affine_omitted_correction_rejected_before_tolerance_audit(affine_record):
 out,_,audited=affine_record
 ev=out.events[0];i=out.times_s.index(ev.time_s)
 from sludge_sandbox.depletion_integration import DepletionPolicy,NestedApproachPolicy
 from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy
 policy=json.loads(audited.original_policy_json)['event_policy']
 policy['roundoff_policy']=DepletionRoundoffPolicy(**policy['roundoff_policy']);policy['nested_approach']=NestedApproachPolicy(**policy['nested_approach'])
 ep=DepletionPolicy(**policy)
 assert ev.correction is not None and ev.correction.liquid_before_mol<ep.amount_absolute_mol
 with pytest.raises(m.EventRecordError,match='affine_uncorrected_raw_liquid_nonzero'):
  m.audit_affine(replace(ev,correction=None),out.states[i-1],out.states[i],0,1,ep,['existing_liquid'])

@pytest.mark.parametrize('target',['bool_difference','string_array','null_diff_bad_clock'])
def test_refinement_numeric_types_strict(affine_record,target):
 out,original,audited=affine_record;record=copy.deepcopy(original)
 ref=next(r for r in record['refinements'] if r['differences'] is not None)
 if target=='bool_difference':ref['differences'][0]=False
 elif target=='string_array':ref['comparison_details']['event_energy']['absolute_differences'][0]='0.0'
 else:
  ref=next(r for r in record['refinements'] if r['differences'] is None);ref['common_time_s']=True
 with pytest.raises(m.EventRecordError):m.AuditedDepletionRecord(m.canonical(record),audited.original_policy_json).restore_result(out.operator)
