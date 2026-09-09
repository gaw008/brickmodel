"""Saved-data-only exact audit; no model imports or native calls."""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import traceback


def q(value):
    if isinstance(value, dict):
        return F(value['numerator'], value['denominator'])
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('invalid exact numeric input')
    return F(value)


def polynomial(n, r, a, h):
    return n + r*h + a*h*h/2


def positive_integral(r, a, h):
    points = [F(0), h]
    if a and 0 < -r/a < h:
        points.insert(1, -r/a)
    return sum((r*(v-u)+a*(v*v-u*u)/2 for u,v in zip(points,points[1:])
                if r+a*(u+v)/2 > 0), F())


def order_check(order, initial_observation, midpoint_observation, modes, liquid_index, initial_state=None):
    start = q(order['start_s'])
    candidates = []
    indices=[row['cell_index'] for row in order['roots']]
    assert len(indices)==len(set(indices))
    assert set(indices)=={i for i,mode in enumerate(modes) if mode=='existing_liquid'}
    hm=q(order['midpoint_s'])-start
    assert hm>0
    for row in order['roots']:
        n,r,a = (q(row[k]) for k in ('initial_mol','rate_mol_s','acceleration_mol_s2'))
        assert n>0
        i=row['cell_index']; li=liquid_index
        def net(obs):
            rates=obs['rates']
            return q(rates['face_species_mol_s'][i][li])-q(rates['face_species_mol_s'][i+1][li])+q(rates['reaction_species_mol_s'][i][li])
        assert r==net(initial_observation)
        assert a==(net(midpoint_observation)-r)/hm
        if initial_state is not None:
            assert n==q(initial_state['amounts_mol'][i][li])
        interval = row['root_interval_s']
        if interval is None:
            h = q(row['upper_elapsed_s'])
            locations = [F(0),h]
            if a and 0 < -r/a < h:
                locations.append(-r/a)
            assert min(polynomial(n,r,a,x) for x in locations) > 0
            continue
        lo,hi = map(q,interval)
        assert start < lo <= hi <= start+q(row['upper_elapsed_s'])
        assert polynomial(n,r,a,lo-start) >= 0
        assert polynomial(n,r,a,hi-start) <= 0
        assert r+a*(lo-start) < 0 and r+a*(hi-start) < 0
        candidates.append((lo,hi,row['cell_index']))
    candidates.sort()
    assert candidates and candidates[0][2] == order['selected_cell']
    if len(candidates)>1:
        assert candidates[0][1] < candidates[1][0]
    return {'selected_cell':order['selected_cell'], 'root_intervals':[
        {'cell':i,'lower':str(lo),'upper':str(hi)} for lo,hi,i in candidates],
        'strict_next_gap_s':str(candidates[1][0]-candidates[0][1]) if len(candidates)>1 else None}


def perform(directory, report):
    def read(name):
        data=(directory/name).read_bytes()
        report['inputs'][name]=hashlib.sha256(data).hexdigest()
        return json.loads(data)
    wrapper=read('core-result.json'); result=wrapper['result']
    report['actual_status']=result['status']; report['actual_reason']=result['reason']
    assert result['status']=='failed' and result['reason']=='correction_exceeds_evaporation_fraction'
    assert result['events']==result['packets']==result['corrections']==[]
    assert len(result['steps'])>0 and len(result['times_s'])==len(result['steps'])+1
    assert read('runtime-before.json')==read('runtime-after.json')
    case=read('case.json'); policy=read('actual-depletion-policy.json')
    read('original-integration-policy.json'); read('original-depletion-policy.json'); read('runner.json')
    diagnostics=[r['comparison_details']['writeback_failure'] for r in result['refinements']
                 if 'writeback_failure' in r['comparison_details']]
    assert len(diagnostics)==1
    d=diagnostics[0]
    assert d['schema']=='ordered_affine_writeback_failure_v1' and d.get('available',True)
    assert d['roundoff_policy']==policy['roundoff_policy']
    assert d['reason']==result['reason']
    i,li=d['cell_index'],d['liquid_index']
    start,raw=d['initial_state'],d['raw_state']
    clock=d['clock']; h=q(clock['end_s'])-q(clock['start_s']); hm=q(clock['midpoint_s'])-q(clock['start_s'])
    assert 0 < hm < h
    assert clock['time_absolute_s']==policy['time_absolute_s']==case['numerics']['depletion']['time_absolute_s']
    assert d['roundoff_policy']==case['numerics']['depletion']['roundoff_policy']
    n=q(start['amounts_mol'][i][li]); assert q(clock['start_inventory_mol'])==n
    terms=d['signed_liquid_terms_mol']; left=clock['liquid_rates_start_mol_s']; right=clock['liquid_rates_mid_mol_s']
    for observed,rates in ((d['initial_observation'],left),(d['midpoint_observation'],right)):
        rr=observed['rates']
        assert list(rates)==[rr['face_species_mol_s'][i][li],-rr['face_species_mol_s'][i+1][li],rr['reaction_species_mol_s'][i][li]]
    assert len(terms)==len(left)==len(right)==3
    assert len(start['mechanical_stretches'])==len(d['stretch_increment'])==len(raw['mechanical_stretches'])==len(start['amounts_mol'])+1
    for term,a,b in zip(terms,left,right):
        assert term==float(q(a)*h+(q(b)-q(a))*h*h/(2*hm))
    rr=sum(map(q,left),F()); aa=(sum(map(q,right),F())-rr)/hm
    residual=polynomial(n,rr,aa,h)
    neighbor=q(math.nextafter(clock['end_s'],math.inf))-q(clock['start_s'])
    assert residual>=0 and polynomial(n,rr,aa,neighbor)<0
    assert polynomial(n,rr,aa,h+q(clock['time_absolute_s']))<=0
    f=d['integrated_fields']
    for cell,row in enumerate(start['amounts_mol']):
        for species,value in enumerate(row):
            expected=q(value)+q(f['face_species_mol'][cell][species])-q(f['face_species_mol'][cell+1][species])+q(f['reaction_species_mol'][cell][species])
            assert float(expected)==raw['amounts_mol'][cell][species]
        assert float(q(start['internal_energy_j'][cell])+q(f['face_energy_j'][cell])-q(f['face_energy_j'][cell+1])+q(f['cell_work_j'][cell]))==raw['internal_energy_j'][cell]
    for before,increment,after in zip(start['mechanical_stretches'],d['stretch_increment'],raw['mechanical_stretches']):
        assert float(q(before)+q(increment))==after
    e0=q(d['initial_observation']['evaporation_mol_s'][i]); em=q(d['midpoint_observation']['evaporation_mol_s'][i])
    gross=positive_integral(e0,(em-e0)/hm,h)
    assert gross==q(d['exact_positive_evaporated_mol'])
    evap=q(d['positive_evaporated_mol']); assert evap<=gross<q(math.nextafter(d['positive_evaporated_mol'],math.inf))
    delta=q(raw['amounts_mol'][i][li]); limit=evap*q(d['roundoff_policy']['correction_fraction_evaporated'])
    report['fraction']={k:str(v) for k,v in {'delta_mol':delta,'exact_gross_mol':gross,'downward_gross_mol':evap,'limit_mol':limit,'excess_mol':delta-limit,'delta_over_gross':delta/evap,'clock_polynomial_residual_mol':residual,'panel_duration_s':h}.items()}
    assert delta>limit>0
    previous=d['previous_uncommitted_frames']; assert previous
    modes=read('original-interfaces.json')
    if isinstance(modes,dict):
        modes=modes['interfaces']
    modes=list(modes)
    report['previous_uncommitted_orders']=[]
    for frame in previous:
        evidence=frame['event']['terminal_evidence']
        prior_order=frame['root_order']; prior_clock=evidence['clock']
        assert prior_order['selected_cell']==frame['event']['cell_index']
        assert prior_order['start_s']==prior_clock['start_s'] and prior_order['midpoint_s']==prior_clock['midpoint_s']
        selected_rows=[row for row in prior_order['roots'] if row['cell_index']==prior_order['selected_cell']]
        assert len(selected_rows)==1 and q(selected_rows[0]['initial_mol'])==q(prior_clock['start_inventory_mol'])
        report['previous_uncommitted_orders'].append(order_check(frame['root_order'],evidence['initial_observation'],evidence['midpoint_observation'],modes,li))
        modes[frame['event']['cell_index']]='depleted_no_nucleation'
    assert modes==d['process_local_source_binding'][8]
    report['previous_initial_inventory_binding']='Previous frame full start state is not saved: coefficient rates and complete active set are bound, but nonselected initial inventories only checked as stored polynomial inputs.'
    report['failed_uncommitted_order']=order_check(d['root_order'],d['initial_observation'],d['midpoint_observation'],modes,li,start)
    assert d['root_order']['selected_cell']==i
    report['accepted_steps']=len(result['steps']); report['committed_events']=0
    report['uncommitted_previous_frames']=len(previous)
    report['qualification']='Failure arithmetic and numerical affine root ordering only; no committed packet, true-RHS localization, spatial convergence or material validation.'


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('directory',type=Path)
    args=parser.parse_args(); out=Path(__file__).with_name('audit-result.json')
    report={'status':'started','inputs':{}}
    try:
        perform(args.directory,report); report['status']='passed'
    except Exception:
        report['status']='failed'; report['traceback']=traceback.format_exc()
    finally:
        out.write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':
    raise SystemExit(main())
