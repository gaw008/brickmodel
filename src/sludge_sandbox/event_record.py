"""Data-only explicit depletion records; no dynamic class/provider loading."""
from dataclasses import dataclass, fields, replace
from fractions import Fraction as F
import json,math
import numpy as np
from sludge_sandbox.verification_case import encode
from sludge_sandbox.integration import ConservedState,StepLedger,Rates,IntegrationPolicy
from sludge_sandbox.depletion_integration import DepletionPolicy,NestedApproachPolicy,DepletionResult,DepletionEvent,DepletionRefinement,DepletionEvaluation,AffineTerminalEvidence,ManufacturedDepletionAdapter
from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy,DepletionRoundoffTotals,DepletionWritebackRecord,DepletionClockEvidence,depletion_writeback
from sludge_sandbox.affine_depletion_clock import AffineDepletionClockEvidence
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
from sludge_sandbox.deforming_solid_storage import _digest

class EventRecordError(ValueError):pass

def require(ok,reason):
    if not ok:raise EventRecordError(reason)

def canonical(value):return json.dumps(value,separators=(',',':'),allow_nan=False).encode()
def frozen(value):
    if isinstance(value,list):return tuple(frozen(v) for v in value)
    if isinstance(value,dict):return {k:frozen(v) for k,v in value.items()}
    return value

def exact(value):
    require(type(value) is dict and set(value)=={'numerator','denominator'},'exact_fraction_required')
    require(type(value['numerator']) is int and type(value['denominator']) is int and value['denominator']>0,'invalid_fraction')
    return F(value['numerator'],value['denominator'])

def numeric_tree(value):
    if isinstance(value,(list,tuple)):
        for v in value:numeric_tree(v)
    else:require(type(value) in (int,float) and math.isfinite(value),'finite_numeric_required')

def object_fields(cls,data):
    require(type(data) is dict and set(data)=={f.name for f in fields(cls)},'exact_'+cls.__name__+'_fields_required')
    return dict(data)

def state(data):
    d=object_fields(ConservedState,data)
    for key in ('amounts_mol','internal_energy_j','mechanical_stretches'):
        if d[key] is not None:numeric_tree(d[key])
    d['energy_model_identity']=frozen(d['energy_model_identity'])
    return ConservedState(**d)

def numeric_record(cls,data):
    d=object_fields(cls,data)
    for key,value in d.items():
        if value is None:continue
        if 'roundoff' in key or key.startswith('component_sum_residual'):
            if isinstance(value,dict):d[key]={k:tuple(exact(x) for x in v) for k,v in value.items()}
            else:d[key]=tuple(exact(x) for x in value)
        elif isinstance(value,dict):
            for v in value.values():numeric_tree(v)
        else:numeric_tree(value)
    result=cls(**{f.name:d[f.name] for f in fields(cls) if f.init})
    require(encode(result)==data,'derived_record_field_mismatch')
    return result

def clock(data):
    if data is None:return None
    cls=AffineDepletionClockEvidence if 'midpoint_s' in data else DepletionClockEvidence
    d=object_fields(cls,data)
    for v in d.values():numeric_tree(v)
    return cls(**{k:frozen(v) for k,v in d.items()})

def correction(data):
    if data is None:return None
    d=object_fields(DepletionWritebackRecord,data)
    for k,v in d.items():
        if k=='clock_evidence':d[k]=clock(v)
        elif isinstance(v,dict):d[k]=exact(v)
        elif k!='qualification':numeric_tree(v)
    for k in ('cell_index','liquid_index','vapor_index'):require(type(d[k]) is int,'integer_index_required')
    return DepletionWritebackRecord(**d)

def observation(data):
    d=object_fields(DepletionEvaluation,data);d['rates']=numeric_record(Rates,d['rates'])
    for k,v in d.items():
        if k!='rates':numeric_tree(v);d[k]=tuple(v)
    cells=d['rates'].reaction_species_mol_s.shape[0]
    require(all(len(v)==cells for key,v in d.items() if key!='rates'),'observation_cell_shape')
    require(all(v>=0 for key in ('temperature_errors_k','pressure_errors_pa') for v in d[key]),'negative_observation_error')
    return DepletionEvaluation(**d)

def evidence(data):
    if data is None:return None
    d=object_fields(AffineTerminalEvidence,data)
    return AffineTerminalEvidence(clock(d['clock']),state(d['midpoint_state']),observation(d['initial_observation']),observation(d['midpoint_observation']))

def event(data):
    d=object_fields(DepletionEvent,data)
    d['terminal_panel']=numeric_record(StepLedger,d['terminal_panel']);d['correction']=correction(d['correction']);d['terminal_evidence']=evidence(d['terminal_evidence']);d['event_time_rounding_s']=exact(d['event_time_rounding_s'])
    require(type(d['cell_index']) is int,'integer_event_cell')
    for k,v in d.items():
        if k not in ('terminal_panel','correction','terminal_evidence','event_time_rounding_s','qualification') and v is not None:numeric_tree(v)
    return DepletionEvent(**d)

def binding(operator,initial):
    require(type(operator) in (WaterPhaseTransfer,ManufacturedDepletionAdapter),'explicit_operator_required')
    identity=getattr(operator,'energy_model_identity',initial.energy_model_identity)
    if type(operator) is WaterPhaseTransfer:identity=getattr(operator.base_model,'energy_model_identity',initial.energy_model_identity)
    content=None
    if type(operator) is WaterPhaseTransfer:
        chemical=operator.chemical
        chemical._check_identity()
        implementation=chemical.water.implementation
        content={'full_configuration_sha256':_digest(tuple((f.name,getattr(operator,f.name)) for f in fields(operator) if f.name!='interface_modes')),
            'chemical_method_id':chemical.method_id,'chemical_reference_pressure_pa':chemical.reference_pressure_pa,
            'chemical_temperature_range_k':encode(chemical.temperature_range_k),
            'chemical_gas_constant_j_mol_k':chemical.gas_constant_j_mol_k,'chemical_caloric_method_id':chemical.caloric_method_id,
            'water_implementation_sha256':None if implementation is None else implementation.sha256}
    return {'actual_content':content,'program_knots_s':encode(getattr(operator,'program_knots_s',())), 'energy_model_identity':encode(identity),'source_ids':encode(tuple(operator.source_ids)),
        'species_order':encode(getattr(operator,'species_order',tuple(str(i) for i in range(initial.amounts_mol.shape[1])))),
        'liquid_index':operator.liquid_index,'water_vapor_index':operator.water_vapor_index,
        'operator_contract':encode(getattr(operator,'deterministic_contract',())),
        'operator_kind':'water_phase_transfer' if type(operator) is WaterPhaseTransfer else 'manufactured_adapter'}

def encode_depletion_result(run,*,original_interfaces):
    require(type(run) is DepletionResult,'explicit_depletion_result')
    data={f.name:encode(getattr(run,f.name)) for f in fields(run) if f.name not in ('operator','roundoff_totals')}
    schema='sandbox_depletion_result_v2' if 'endpoint_attempts' in run.phase_costs.get('comparison',{}) else 'sandbox_depletion_result_v1'
    data.update(schema=schema,final_interfaces=list(run.operator.interfaces),
        original_interfaces=list(original_interfaces),operator_binding=binding(run.operator,run.states[0]),roundoff_totals=run.roundoff_totals.to_record())
    canonical(data)
    return data

def restore_final_operator(original_operator,record):
    initial=state(record['states'][0]);require(binding(original_operator,initial)==record['operator_binding'],'operator_binding_mismatch')
    original=tuple(record['original_interfaces']);final=tuple(record['final_interfaces'])
    require(tuple(original_operator.interfaces)==original,'original_modes_mismatch')
    require(len(final)==len(original),'mode_shape')
    cells=[]
    for i,(a,b) in enumerate(zip(original,final)):
        require(a in ('existing_liquid','depleted_no_nucleation') and b in ('existing_liquid','depleted_no_nucleation'),'invalid_mode')
        if a!=b:require(a=='existing_liquid' and b=='depleted_no_nucleation','nucleation_forbidden');cells.append(i)
    return original_operator.with_depleted_cells(state(record['states'][-1]),cells)

def decode_result(record,operator):
    names={f.name for f in fields(DepletionResult)}-{'operator'}
    require(type(record) is dict and set(record)==names|{'schema','final_interfaces','original_interfaces','operator_binding'},'exact_result_fields')
    require(record['schema'] in ('sandbox_depletion_result_v1','sandbox_depletion_result_v2'),'unsupported_record_schema')
    require(tuple(operator.interfaces)==tuple(record['final_interfaces']),'final_modes_mismatch')
    require(binding(operator,state(record['states'][0]))==record['operator_binding'],'operator_binding_mismatch')
    d={k:record[k] for k in names};d['operator']=operator;d['states']=tuple(state(v) for v in d['states']);d['steps']=tuple(numeric_record(StepLedger,v) for v in d['steps']);d['events']=tuple(event(v) for v in d['events']);d['corrections']=tuple(correction(v) for v in d['corrections'])
    d['roundoff_totals']=DepletionRoundoffTotals.from_record(d['roundoff_totals'])
    for k in ('cumulative_amounts_mol','cumulative_energy_j','cumulative_absolute_component_residual_j'):
        if d[k] is not None:d[k]=tuple(exact(v) for v in d[k])
    d['times_s']=tuple(d['times_s']);d['refinements']=tuple(DepletionRefinement(**object_fields(DepletionRefinement,v)) for v in d['refinements'])
    return DepletionResult(**d)

@dataclass(frozen=True)
class AuditedDepletionRecord:
    record_json: bytes
    original_policy_json: bytes
    def restore_result(self,operator):
        require(type(self.record_json) is bytes and type(self.original_policy_json) is bytes,'immutable_record_bytes')
        try:return self._restore(operator)
        except EventRecordError:raise
        except (ValueError,TypeError,KeyError,IndexError,OverflowError,AttributeError) as exc:raise EventRecordError('invalid_depletion_record:'+str(exc)) from exc
    def _restore(self,operator):
        def pairs(items):
            result={}
            for key,value in items:
                require(key not in result,'duplicate_json_key');result[key]=value
            return result
        data=json.loads(self.record_json,object_pairs_hook=pairs);policy=json.loads(self.original_policy_json,object_pairs_hook=pairs)
        require(set(policy)=={'integration_policy','event_policy','start_s','end_s'},'original_policy_fields')
        ip=IntegrationPolicy(**policy['integration_policy']);ep=dict(policy['event_policy'])
        ep['roundoff_policy']=DepletionRoundoffPolicy(**ep['roundoff_policy'])
        if ep['nested_approach'] is not None:ep['nested_approach']=NestedApproachPolicy(**ep['nested_approach'])
        if ep.get('pressure_comparison') is not None:
            from .pressure_comparison import restore_pressure_comparison_policy
            ep['pressure_comparison']=restore_pressure_comparison_policy(ep['pressure_comparison'])
        ep=DepletionPolicy(**ep)
        audit_depletion_record(data,state(data['states'][0]),ip,ep,data['original_interfaces'],operator=operator,start_s=policy['start_s'],end_s=policy['end_s'])
        return decode_result(data,operator)


def audit_depletion_record(record,original_initial,original_integration_policy,original_event_policy,original_interfaces,*,operator,start_s,end_s):
    """Recompute every accepted prefix; original policies never reset at resume."""
    try:return _audit(record,original_initial,original_integration_policy,original_event_policy,original_interfaces,operator,start_s,end_s)
    except EventRecordError:raise
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,AttributeError) as exc:raise EventRecordError('invalid_depletion_record:'+str(exc)) from exc


def _audit(record,initial,p,ep,original_interfaces,operator,start,end):
    canonical(record);require(record['original_interfaces']==list(original_interfaces),'original_modes_mismatch')
    r=decode_result(record,operator);require(encode(r.states[0])==encode(initial),'original_initial_mismatch')
    paired=ep.pressure_comparison is not None
    if paired:
        from .pressure_comparison import pressure_comparison_binding
        actual_binding=pressure_comparison_binding(operator)
        require(ep.pressure_comparison.to_record()['cell_boxes']==actual_binding['boxes'],
                'original_pressure_box_binding')
    require(record['schema']==('sandbox_depletion_result_v2' if paired else 'sandbox_depletion_result_v1'),'record_comparison_schema_mismatch')
    require(r.status in ('completed','cancelled','resource_limit','domain_exit','numerical_failure','failed','unsupported'),'invalid_status')
    require(len(r.states)==len(r.times_s)==len(r.steps)+1 and r.times_s[0]==start and start<=r.times_s[-1]<=end,'history_shape')
    if r.status=='completed':require(r.times_s[-1]==end,'incomplete_completed_record')
    for v in r.times_s:numeric_tree(v)
    for name in ('evaluations','rejected_trials','attempted_steps'):require(type(getattr(r,name)) is int and getattr(r,name)>=0,'invalid_resource_counter')
    for cost,attr in (('evaluations','evaluations'),('panels','attempted_steps'),('rejections','rejected_trials')):
        require(set(r.phase_costs)=={'ordinary','approach','terminal','dry','comparison'},'phase_cost_schema')
        for phase,values in r.phase_costs.items():
            expected={'evaluations','panels','rejections'}|({'endpoint_attempts','endpoint_completed'} if paired and phase=='comparison' else set())
            require(set(values)==expected and all(type(v) is int and v>=0 for v in values.values()),'phase_cost_counter')
        require(sum(v[cost] for v in r.phase_costs.values())==getattr(r,attr),'phase_cost_total')
        saved=[]
        for ref in r.refinements:
            for phase,values in ref.phase_costs.items():
                expected={'evaluations','panels','rejections'}|({'endpoint_attempts','endpoint_completed'} if paired and phase=='comparison' else set())
                require(set(values)==expected and all(type(v) is int and v>=0 for v in values.values()),'refinement_cost_counter');saved.append(values[cost])
        require(sum(saved)<=getattr(r,attr),'refinement_cost_total')
    if paired:audit_endpoint_costs(r.phase_costs['comparison'],[ref.phase_costs['comparison'] for ref in r.refinements])
    require(set(r.reuse_counts)=={'observations','panels'} and all(type(v) is int and v>=0 for v in r.reuse_counts.values()),'reuse_counter')
    require(r.approach_strategy==(ep.nested_approach.strategy_id if ep.nested_approach else 'legacy'),'approach_strategy_mismatch')
    numeric_tree(r.elapsed_seconds);require(r.elapsed_seconds>=0,'negative_elapsed')
    require(r.attempted_steps>=len(r.steps) and r.attempted_steps<=p.maximum_steps and r.rejected_trials<=p.maximum_rejections,'resource_budget')
    require(r.safe_inventory_fraction==ep.safe_inventory_fraction and r.terminal_method==ep.terminal_method,'event_policy_mismatch')
    require(r.roundoff_totals.policy==ep.roundoff_policy,'roundoff_policy_mismatch')
    cells,columns=initial.amounts_mol.shape;li=operator.liquid_index;vi=operator.water_vapor_index
    cn=[F()]*(cells*columns);cu=[F()]*cells;ct=[F()]*cells;mechanical=initial.mechanical_stretches is not None
    cm=[F()]*(cells+1) if mechanical else [];cx=cm.copy();cq=cm.copy();totals=DepletionRoundoffTotals(ep.roundoff_policy)
    modes=list(original_interfaces);event_steps={};last_event=-math.inf;nonempty=[]
    for ev in r.events:
        require(0<=ev.cell_index<cells and modes[ev.cell_index]=='existing_liquid' and ev.time_s>last_event,'invalid_event_order')
        last_event=ev.time_s;modes[ev.cell_index]='depleted_no_nucleation'
        indices=[i for i,l in enumerate(r.steps) if l.end_s==ev.time_s and encode(l)==encode(ev.terminal_panel)]
        require(len(indices)==1,'terminal_step_binding');index=indices[0];require(index not in event_steps,'duplicate_terminal');event_steps[index]=ev
        require(r.states[index+1].amounts_mol[ev.cell_index,li]==0,'event_not_zero')
        if ev.correction is not None:nonempty.append(ev.correction)
        limits=(ep.time_absolute_s,ep.amount_absolute_mol,ep.energy_absolute_j,ep.temperature_absolute_k,ep.pressure_absolute_pa)
        vals=(ev.event_time_difference_s,ev.common_amount_difference_mol,ev.common_energy_difference_j,ev.common_temperature_difference_k,ev.common_pressure_difference_pa)
        require(all(0<=v<=z for v,z in zip(vals,limits)),'event_comparison_gate')
        if mechanical:require(ev.stretch_difference is not None and 0<=ev.stretch_difference<=p.stretch_absolute_tolerance,'event_stretch_gate')
    require(tuple(modes)==tuple(r.operator.interfaces) and encode(nonempty)==encode(r.corrections),'correction_modes_binding')
    schema=None
    active_modes=list(original_interfaces)
    for k,l in enumerate(r.steps):
        before,after=r.states[k:k+2]
        require(l.face_species_mol.shape==(cells+1,columns) and l.reaction_species_mol.shape==(cells,columns) and l.face_energy_j.shape==(cells+1,) and l.cell_work_j.shape==(cells,),'ledger_state_shape')
        if not mechanical:require(l.stretch_increment is None and l.stretch_quadrature_roundoff is None,'unexpected_mechanical_ledger')
        require(l.start_s==r.times_s[k] and l.end_s==r.times_s[k+1] and l.end_s>l.start_s,'step_clock')
        require(after.energy_model_identity==initial.energy_model_identity and after.amounts_mol.shape==initial.amounts_mol.shape,'state_binding')
        require((after.mechanical_stretches is not None)==mechanical,'mechanical_presence')
        ev=event_steps.get(k);cor=ev.correction if ev else None
        if ev is not None and ep.terminal_method=='affine_midpoint':audit_affine(ev,before,after,li,vi,ep,active_modes)
        if ev is not None:active_modes[ev.cell_index]='depleted_no_nucleation'
        if cor is not None:
            require(cor.clock_evidence is not None and cor.clock_evidence.start_s==l.start_s and cor.clock_evidence.end_s==l.end_s and cor.clock_evidence.time_absolute_s==ep.time_absolute_s,'correction_clock_binding')
            require(cor.cell_index==ev.cell_index and cor.liquid_index==li and cor.vapor_index==vi,'correction_indices')
            raw=np.array(after.amounts_mol);raw[cor.cell_index,li]=cor.liquid_before_mol;raw[cor.cell_index,vi]=cor.vapor_before_mol
            raw=ConservedState(raw,after.internal_energy_j,energy_model_identity=after.energy_model_identity,mechanical_stretches=after.mechanical_stretches)
            fixed,recomputed,totals=depletion_writeback(raw,cell_index=cor.cell_index,liquid_index=li,vapor_index=vi,
                panel_liquid_start_mol=float(before.amounts_mol[cor.cell_index,li]),
                panel_liquid_terms_mol=(float(l.face_species_mol[cor.cell_index,li]),-float(l.face_species_mol[cor.cell_index+1,li]),float(l.reaction_species_mol[cor.cell_index,li])),
                positive_evaporated_mol=ev.positive_evaporated_mol,policy=ep.roundoff_policy,totals=totals,clock_evidence=cor.clock_evidence)
            require(encode(recomputed)==encode(cor) and encode(fixed)==encode(after),'writeback_reconstruction')
        for i in range(cells):
            for j in range(columns):
                delta=F(float(l.face_species_mol[i,j]))-F(float(l.face_species_mol[i+1,j]))+F(float(l.reaction_species_mol[i,j]))
                if cor and i==cor.cell_index:
                    if j==li:delta+=cor.ideal_liquid_increment_mol
                    if j==vi:delta+=cor.actual_vapor_increment_mol
                cn[i*columns+j]+=delta
                require(abs(F(float(after.amounts_mol[i,j]))-F(float(initial.amounts_mol[i,j]))-cn[i*columns+j])<=F(p.amount_absolute_tolerance_mol),'amount_prefix_budget')
                require(abs(F(float(after.amounts_mol[i,j]))-F(float(before.amounts_mol[i,j]))-delta)<=F(p.amount_absolute_tolerance_mol),'amount_local_budget')
            delta=F(float(l.face_energy_j[i]))-F(float(l.face_energy_j[i+1]))+F(float(l.cell_work_j[i]));cu[i]+=delta
            require(abs(F(float(after.internal_energy_j[i]))-F(float(initial.internal_energy_j[i]))-cu[i])<=F(p.energy_absolute_tolerance_j),'energy_prefix_budget')
            require(abs(F(float(after.internal_energy_j[i]))-F(float(before.internal_energy_j[i]))-delta)<=F(p.energy_absolute_tolerance_j),'energy_local_budget')
        current_schema=None if l.cell_work_components_j is None else tuple(l.cell_work_components_j)
        if k:require(current_schema==schema,'component_schema_changed')
        schema=current_schema
        if l.cell_work_components_j is not None:
            keys=tuple(l.cell_work_components_j);require(schema is None or schema==keys,'component_schema_changed');schema=keys
            require(l.component_sum_residual_j is not None and l.component_quadrature_roundoff_j is not None,'component_fields_missing')
            for i in range(cells):
                residual=F(float(l.cell_work_j[i]))-sum((F(float(v[i])) for v in l.cell_work_components_j.values()),F())
                require(residual==l.component_sum_residual_j[i],'component_residual_mismatch');ct[i]+=abs(residual);require(ct[i]<=F(p.energy_absolute_tolerance_j),'component_prefix_budget')
        if mechanical:
            require(l.stretch_increment is not None and l.stretch_quadrature_roundoff is not None and len(l.stretch_increment)==len(cm),'mechanical_ledger_shape')
            for i in range(len(cm)):
                v=F(float(l.stretch_increment[i]));z=l.stretch_quadrature_roundoff[i];cm[i]+=v;cx[i]+=v-z;cq[i]+=abs(z);d=F(float(after.mechanical_stretches[i]))-F(float(initial.mechanical_stretches[i]));local=F(float(after.mechanical_stretches[i]))-F(float(before.mechanical_stretches[i]));tol=F(p.stretch_absolute_tolerance)
                require(max(abs(d-cm[i]),abs(d-cx[i]),abs(local-v),abs(local-v+z),cq[i])<=tol,'mechanical_prefix_budget')
    require(tuple(cn)==r.cumulative_amounts_mol and tuple(cu)==r.cumulative_energy_j,'stored_cumulative_mismatch')
    require(r.cumulative_absolute_component_residual_j is None and schema is None or tuple(ct)==r.cumulative_absolute_component_residual_j,'stored_component_mismatch')
    require(totals==r.roundoff_totals,'stored_roundoff_totals_mismatch')
    audit_refinements(r,p,ep,mechanical,operator=operator)
    return AuditedDepletionRecord(canonical(record),canonical({'integration_policy':encode(p),'event_policy':encode(ep),'start_s':start,'end_s':end}))


def audit_refinements(result, policy, event_policy, mechanical, *, operator=None):
    """Check retained comparison diagnostics without rerunning physical providers."""
    limits=(event_policy.time_absolute_s,event_policy.amount_absolute_mol,event_policy.energy_absolute_j,event_policy.temperature_absolute_k,event_policy.pressure_absolute_pa)
    if mechanical:limits+= (policy.stretch_absolute_tolerance,)
    for ref in result.refinements:
        for key in ('start_s','terminal_cap_s','common_time_s','event_time_s','elapsed_seconds','next_common_time_s','approach_cap_s','approach_safe_inventory_fraction'):
            value=getattr(ref,key)
            if value is not None:numeric_tree(value)
        require(type(ref.status) is str and type(ref.approach_role) is str,'refinement_text_type')
        def diagnostic_numbers(value):
            if isinstance(value,dict) or hasattr(value,'items'):
                for key,item in value.items():
                    require(type(key) is str,'diagnostic_key');diagnostic_numbers(item)
            else:numeric_tree(value)
        paired=event_policy.pressure_comparison is not None
        numeric_details=dict(ref.comparison_details)
        if paired:numeric_details.pop('pressure_comparison',None)
        diagnostic_numbers(numeric_details)
        if ref.differences is not None:numeric_tree(ref.differences)
        require(type(ref.level) is int and 0<=ref.level<event_policy.maximum_refinements,'refinement_level')
        require(type(ref.evaluations) is int and 0<=ref.evaluations<=result.evaluations,'refinement_evaluations')
        require(math.isfinite(ref.elapsed_seconds) and 0<=ref.elapsed_seconds<=result.elapsed_seconds,'refinement_elapsed')
        require(ref.start_s<ref.common_time_s and ref.terminal_cap_s>0,'refinement_clock')
        if ref.differences is None:
            require('pressure_comparison' not in ref.comparison_details,'paired_record_without_comparison')
            continue
        require(len(ref.differences)==len(limits),'comparison_dimension')
        require(all(math.isfinite(v) and v>=0 for v in ref.differences),'comparison_nonnegative')
        d=ref.comparison_details
        def maximum(name):
            item=d[name];values=np.asarray(item['absolute_differences'],dtype=float)
            require(values.size>0 and np.isfinite(values).all() and (values>=0).all(),'comparison_array')
            require(float(values.max())==item['maximum'] and values[tuple(item['maximum_index'])]==item['maximum'],'comparison_maximum')
            return item['maximum']
        expected=[None,max(maximum('event_amounts'),maximum('common_amounts')),max(maximum('event_energy'),maximum('common_energy'))]
        for quantity,unit in (('temperature','k'),('pressure','pa')):
            vals=[]
            for where in ('event_observations','common_observations'):
                obs=d[where];a=obs[f'{quantity}_errors_a_{unit}'];b=obs[f'{quantity}_errors_b_{unit}'];nominal=obs[f'{quantity}_nominal_difference_{unit}']
                require(all(math.isfinite(v) and v>=0 for v in (*a,*b,nominal)),'comparison_point_bounds')
                vals.append(nominal+max(a)+max(b))
            expected.append(max(vals))
        if paired:
            expected[4]=audit_paired_refinement(ref,event_policy.pressure_comparison,operator,expected[4])
        if mechanical:expected.append(max(maximum('event_stretches'),maximum('common_stretches')))
        require(tuple(expected[1:])==tuple(ref.differences[1:]),'comparison_diagnostics_mismatch')
        require(abs(d['terminal_end_a_s']-d['terminal_end_b_s'])<=ref.differences[0],'comparison_clock_difference')
        passed=all(v<=lim for v,lim in zip(ref.differences,limits))
        require((ref.status in ('comparison_pass','independent_approach_pass'))==passed,'comparison_status_mismatch')
        for key in ('approach_grid_a_s','approach_grid_b_s'):
            grid=d[key];require(all(math.isfinite(v) for v in grid) and all(a<b for a,b in zip(grid,grid[1:])),'approach_grid_clock')
    for ev in result.events:
        matches=[i for i,ref in enumerate(result.refinements) if ref.status=='comparison_pass' and ref.event_time_s==ev.time_s and ref.common_time_s==ev.common_time_s]
        require(matches,'event_missing_refinement')
        index=matches[-1];current=result.refinements[index]
        require(index>0,'two_successive_comparisons_required');prior=result.refinements[index-1]
        require(prior.status=='comparison_pass' and prior.level+1==current.level and prior.start_s==current.start_s and prior.common_time_s==current.common_time_s,'two_successive_comparisons_required')
        require(prior.event_time_s==ev.previous_time_s,'previous_event_binding')
        diffs=tuple(current.differences)
        if event_policy.nested_approach is not None:
            require(index+1<len(result.refinements),'independent_comparison_required');fine=result.refinements[index+1]
            require(fine.status=='independent_approach_pass' and fine.approach_role=='independent_halved_controls' and fine.start_s==current.start_s and fine.common_time_s==current.common_time_s and fine.level==current.level,'independent_comparison_required')
            require(fine.approach_cap_s==current.approach_cap_s/2 and fine.approach_safe_inventory_fraction==current.approach_safe_inventory_fraction/2,'independent_controls_not_halved')
            require(fine.comparison_details['approach_grid_a_s']!=fine.comparison_details['approach_grid_b_s'],'independent_grid_not_distinct')
            diffs=tuple(max(a,b) for a,b in zip(diffs,fine.differences))
        actual=(ev.event_time_difference_s,ev.common_amount_difference_mol,ev.common_energy_difference_j,ev.common_temperature_difference_k,ev.common_pressure_difference_pa)
        if mechanical:actual+=(ev.stretch_difference,)
        require(actual==diffs,'event_aggregate_differences_mismatch')
    if event_policy.pressure_comparison is not None:audit_paired_committed_binding(result)


def audit_affine(ev,before,after,li,vi,ep,modes):
    proof=ev.terminal_evidence
    require(type(proof) is AffineTerminalEvidence,'affine_evidence_required')
    c=proof.clock;l=ev.terminal_panel
    require(c.start_s==l.start_s and c.end_s==l.end_s and c.time_absolute_s==ep.time_absolute_s,'affine_clock_binding')
    require(c.event_time_rounding_s==ev.event_time_rounding_s,'affine_rounding_binding')
    h=F(c.end_s)-F(c.start_s);hm=F(c.midpoint_s)-F(c.start_s)
    a=proof.initial_observation;b=proof.midpoint_observation;cell=ev.cell_index
    def liquid(obs):
        r=obs.rates;return (float(r.face_species_mol_s[cell,li]),-float(r.face_species_mol_s[cell+1,li]),float(r.reaction_species_mol_s[cell,li]))
    require(liquid(a)==c.liquid_rates_start_mol_s and liquid(b)==c.liquid_rates_mid_mol_s,'affine_sample_binding')
    c.inventory_residual(float(before.amounts_mol[cell,li]),(float(l.face_species_mol[cell,li]),-float(l.face_species_mol[cell+1,li]),float(l.reaction_species_mol[cell,li])))
    def integral(x,y,dt):return dt*F(float(x))+dt*dt*(F(float(y))-F(float(x)))/(2*hm)
    pairs=(('face_species_mol_s','face_species_mol'),('face_energy_w','face_energy_j'),('reaction_species_mol_s','reaction_species_mol'),('cell_power_w','cell_work_j'))
    for rate,name in pairs:
        x=getattr(a.rates,rate);y=getattr(b.rates,rate);actual=getattr(l,name)
        require(x.shape==y.shape==actual.shape,'affine_field_shape')
        require(all(float(integral(x[idx],y[idx],h))==actual[idx] for idx in np.ndindex(x.shape)),'affine_quadrature_binding')
    raw_amounts=np.empty_like(before.amounts_mol);raw_energy=np.empty_like(before.internal_energy_j)
    for i,j in np.ndindex(raw_amounts.shape):
        raw_amounts[i,j]=float(F(float(before.amounts_mol[i,j]))+F(float(l.face_species_mol[i,j]))-F(float(l.face_species_mol[i+1,j]))+F(float(l.reaction_species_mol[i,j])))
    for i in range(len(raw_energy)):
        raw_energy[i]=float(F(float(before.internal_energy_j[i]))+F(float(l.face_energy_j[i]))-F(float(l.face_energy_j[i+1]))+F(float(l.cell_work_j[i])))
    raw_stretches=None if before.mechanical_stretches is None else np.array([float(F(float(x))+F(float(delta))) for x,delta in zip(before.mechanical_stretches,l.stretch_increment)])
    raw=ConservedState(raw_amounts,raw_energy,before.energy_model_identity,mechanical_stretches=raw_stretches)
    expected_amounts=np.array(after.amounts_mol)
    if ev.correction is not None:
        expected_amounts[cell,li]=ev.correction.liquid_before_mol
        expected_amounts[cell,vi]=ev.correction.vapor_before_mol
    else:require(raw.amounts_mol[cell,li]==0,'affine_uncorrected_raw_liquid_nonzero')
    expected=ConservedState(expected_amounts,after.internal_energy_j,after.energy_model_identity,mechanical_stretches=after.mechanical_stretches)
    require(encode(raw)==encode(expected),'affine_binary64_endpoint_binding')
    for idx in np.ndindex(before.amounts_mol.shape):
        i,j=idx
        def net(obs):
            r=obs.rates;return F(float(r.face_species_mol_s[i,j]))-F(float(r.face_species_mol_s[i+1,j]))+F(float(r.reaction_species_mol_s[i,j]))
        n=F(float(before.amounts_mol[idx]));v=net(a);q=(net(b)-v)/(2*hm)
        candidates=[n,n+h*v+h*h*q]
        if q>0 and 0<-v/(2*q)<h:
            t=-v/(2*q);candidates.append(n+t*v+t*t*q)
        minimum=min(candidates)
        require(minimum>=0 and not(j==li and i!=cell and modes[i]=='existing_liquid' and n>0 and minimum==0),'affine_inventory_interior_crossing')
        r=a.rates;pred=n+sum((F(float(hm*F(float(z)))) for z in (r.face_species_mol_s[i,j],-r.face_species_mol_s[i+1,j],r.reaction_species_mol_s[i,j])),F())
        require(float(pred)==proof.midpoint_state.amounts_mol[idx],'affine_predictor_amount')
    if before.mechanical_stretches is not None:
        for i,x in enumerate(a.rates.mechanical_rates_per_s):
            exact_value=integral(x,b.rates.mechanical_rates_per_s[i],h)
            require(float(exact_value)==l.stretch_increment[i] and F(float(exact_value))-exact_value==l.stretch_quadrature_roundoff[i],'affine_mechanical_quadrature')
            require(float(F(float(before.mechanical_stretches[i]))+F(float(hm*F(float(x)))))==proof.midpoint_state.mechanical_stretches[i],'affine_predictor_stretch')
    for key,values in (a.rates.cell_power_components_w or {}).items():
        for i,x in enumerate(values):
            exact_value=integral(x,b.rates.cell_power_components_w[key][i],h)
            require(float(exact_value)==l.cell_work_components_j[key][i] and F(float(exact_value))-exact_value==l.component_quadrature_roundoff_j[key][i],'affine_component_quadrature')
    for i,u in enumerate(before.internal_energy_j):
        r=a.rates;pred=F(float(u))+sum((F(float(hm*F(float(z)))) for z in (r.face_energy_w[i],-r.face_energy_w[i+1],r.cell_power_w[i])),F())
        require(float(pred)==proof.midpoint_state.internal_energy_j[i],'affine_predictor_energy')
    require(proof.midpoint_state.energy_model_identity==before.energy_model_identity,'affine_predictor_identity')
    initial_evap=F(float(a.evaporation_mol_s[cell]));slope=(F(float(b.evaporation_mol_s[cell]))-initial_evap)/hm
    cuts=[F(),h]
    if slope and 0<-initial_evap/slope<h:cuts.insert(1,-initial_evap/slope)
    gross=sum((initial_evap*(right-left)+slope*(right*right-left*left)/2 for left,right in zip(cuts,cuts[1:]) if initial_evap+slope*(left+right)/2>0),F())
    expected=float(gross)
    if F(expected)>gross:expected=math.nextafter(expected,-math.inf)
    require(ev.positive_evaporated_mol==expected,'affine_gross_evaporation_binding')


def audit_endpoint_costs(total, refinements):
    """Charge successful and failed endpoint work without resetting the prefix."""
    def checked(value):
        attempts=value['endpoint_attempts'];completed=value['endpoint_completed']
        require(type(attempts) is int and type(completed) is int and 0<=completed<=attempts,
                'endpoint_cost_order')
        return attempts,completed
    maximum=checked(total);used=[0,0]
    for row in refinements:
        costs=checked(row)
        for i,v in enumerate(costs):used[i]+=v
    require(all(v<=limit for v,limit in zip(used,maximum)),'endpoint_refinement_cost_exceeds_total')


def audit_paired_refinement(ref, comparison_policy, operator, original_pressure):
    """Bind all paired cells to actual closure content and legacy diagnostics."""
    from .pressure_comparison import audit_pressure_comparison, pressure_comparison_binding
    details=ref.comparison_details
    payload=encode(details.get('pressure_comparison'))
    require(type(payload) is dict and set(payload)=={'schema','original_independent_pressure_difference_pa',
            'selected_pressure_difference_pa','pairs'},'paired_refinement_fields')
    require(payload['schema']==comparison_policy.schema,'paired_refinement_schema')
    numeric_tree(payload['original_independent_pressure_difference_pa'])
    require(payload['original_independent_pressure_difference_pa']==original_pressure,'original_pressure_formula_changed')
    require(type(payload['pairs']) is dict and set(payload['pairs'])=={'event','common'},'complete_event_common_pairs')
    require(type(operator) is WaterPhaseTransfer,'actual_paired_operator_required')
    selected=[];cost=0
    for where in ('event','common'):
        pair=payload['pairs'][where]
        require(type(pair) is dict and type(pair.get('states')) is list and len(pair['states'])==2,'paired_states_shape')
        left,right=map(state,pair['states'])
        require(left.energy_model_identity==right.energy_model_identity==operator.base_model.energy_model_identity,
                'paired_state_energy_identity')
        bindings=[]
        for label,point_state in (('a',left),('b',right)):
            saved=pair['bindings_'+label];modes=saved['interfaces']
            require(type(modes) is list and len(modes)==point_state.amounts_mol.shape[0],'paired_modes_shape')
            for i,mode in enumerate(modes):
                amount=point_state.amounts_mol[i,operator.liquid_index]
                require(mode==('existing_liquid' if amount>0 else 'depleted_no_nucleation'),'paired_interface_inventory_binding')
            actual=replace(operator,interface_modes=tuple(modes))
            actual.base_model._check_state(point_state)
            bindings.append(pressure_comparison_binding(actual))
        for field,attribute in (('amounts','amounts_mol'),('energy','internal_energy_j'),('stretches','mechanical_stretches')):
            difference=np.abs(getattr(left,attribute)-getattr(right,attribute))
            require(encode(difference)==encode(details[where+'_'+field]['absolute_differences']),
                    'paired_state_difference_binding')
        bound=audit_pressure_comparison(pair,policy=comparison_policy,state_a=left,state_b=right,
                                        bindings_a=bindings[0],bindings_b=bindings[1])
        cells=pair['cells'];obs=details[where+'_observations']
        for quantity,unit in (('temperature','k'),('pressure','pa')):
            values=[tuple(float(exact(v)) for v in cell['reported_'+quantity+'s_'+unit]) for cell in cells]
            require(max(abs(a-b) for a,b in values)==obs[quantity+'_nominal_difference_'+unit],
                    'paired_reported_observation_difference')
            key='original_temperature_errors_k' if quantity=='temperature' else 'original_pressure_errors_pa'
            for j,side in enumerate(('a','b')):
                errors=[float(exact(cell[key][j])) for cell in cells]
                require(errors==list(obs[quantity+'_errors_'+side+'_'+unit]),'paired_original_point_error_binding')
        selected.append(bound);cost+=pair['endpoint_evaluations']
    numeric_tree(payload['selected_pressure_difference_pa'])
    require(payload['selected_pressure_difference_pa']==max(selected),'paired_selected_pressure_maximum')
    require(cost<=ref.phase_costs['comparison']['endpoint_completed'],'paired_completed_cost_underreported')
    return max(selected)


def audit_paired_committed_binding(result):
    """Anchor retained chosen/finer comparison states to the committed history."""
    def pairs(ref):return ref.comparison_details['pressure_comparison']['pairs']
    for index,ref in enumerate(result.refinements):
        if ref.status not in ('comparison_pass','comparison_fail','independent_approach_pass','independent_approach_fail'):
            continue
        require('pressure_comparison' in ref.comparison_details,'missing_paired_refinement')
        if index and ref.status in ('comparison_pass','comparison_fail'):
            previous=result.refinements[index-1]
            if (previous.status in ('comparison_pass','comparison_fail') and previous.start_s==ref.start_s
                    and previous.common_time_s==ref.common_time_s and previous.level+1==ref.level):
                for where in ('event','common'):
                    require(encode(pairs(previous)[where]['states'][1])==encode(pairs(ref)[where]['states'][0]),
                            'successive_paired_state_binding')
        if ref.status in ('independent_approach_pass','independent_approach_fail'):
            require(index>0,'independent_paired_reference_missing')
            previous=result.refinements[index-1]
            for where in ('event','common'):
                require(encode(pairs(previous)[where]['states'][1])==encode(pairs(ref)[where]['states'][0]),
                        'independent_paired_reference_state')
    for ev in result.events:
        refs=[ref for ref in result.refinements if ref.status=='comparison_pass'
              and ref.event_time_s==ev.time_s and ref.common_time_s==ev.common_time_s]
        require(bool(refs),'committed_paired_comparison_missing');ref=refs[-1]
        for where,time in (('event',ev.time_s),('common',ev.common_time_s)):
            require(time in result.times_s,'committed_paired_clock_missing')
            actual=result.states[result.times_s.index(time)]
            require(encode(pairs(ref)[where]['states'][1])==encode(actual),'committed_paired_state_mismatch')
