"""Independent saved-data Fraction prefix audit; no production imports/EOS."""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import traceback

HERE=Path(__file__).resolve().parent

def require(ok,why):
    if not ok:raise AssertionError(why)

def read(p):
    def unique(items):
        d={}
        for k,v in items:
            require(k not in d,'duplicate key');d[k]=v
        return d
    return json.loads(p.read_text(),object_pairs_hook=unique,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))

def f(v):
    if type(v) is dict:
        require(set(v)=={'numerator','denominator'} and type(v['numerator']) is int and type(v['denominator']) is int and v['denominator']>0,'rational encoding')
        return F(v['numerator'],v['denominator'])
    require(type(v) in (int,float) and math.isfinite(v),'finite number')
    return F(v)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);d=parser.parse_args().directory
    report={'audit_status':'failed','scope':'Saved local/cumulative ledgers and global pressure work only; no native root/endpoint/correction-proof certification.','script_sha256':sha(Path(__file__))}
    try:
        wrapper=read(d/'core-result.json');require(wrapper['research_schema']=='ordered_packet_core_capture_v1','research wrapper')
        r=wrapper['result'];case=read(d/'case.json');p=read(d/'original-integration-policy.json');run=read(d/'runner.json')
        report['input_sha256']={n:sha(d/n) for n in ('core-result.json','case.json','original-integration-policy.json','actual-depletion-policy.json','runner.json')}
        require(run['runtime_before']==run['runtime_after'],'runtime unchanged')
        require(run['case_sha256']==sha(d/'case.json'),'case source')
        require(read(d/'initial.json')==r['states'][0] and read(d/'final.json')==r['states'][-1],'state files')
        require(len(r['times_s'])==len(r['states'])==len(r['steps'])+1,'full history')
        n=len(r['states'][0]['amounts_mol']);cols=len(r['states'][0]['amounts_mol'][0]);require(n==4 and cols==5,'registered layout')
        li,vi=3,2;initial=r['states'][0];cn=[[F(0)]*cols for _ in range(n)];ce=[F(0)]*n;cs=[F(0)]*(n+1);ct=[F(0)]*n
        events={};last=None
        for ev in r['events']:
            require(last is None or f(ev['time_s'])>last,'strict event order');last=f(ev['time_s'])
            matches=[i for i,s in enumerate(r['steps']) if s==ev['terminal_panel'] and s['end_s']==ev['time_s']]
            require(len(matches)==1 and matches[0] not in events,'event panel binding');events[matches[0]]=ev
        frames=[frame for packet in r['packets'] for frame in packet]
        require([z['event'] for z in frames]==r['events'],'all frames/events exact')
        for frame in frames:
            ev=frame['event'];k=next(k for k,v in events.items() if v==ev)
            require(frame['state']==r['states'][k+1],'frame complete state binding')
        require([e['correction'] for e in r['events'] if e['correction'] is not None]==r['corrections'],'all corrections')
        # Same binary64 reference-volume construction as declared geometry;
        # subsequent volume products are exact represented-state arithmetic.
        v0=f(float(case['grid']['half_thickness_m']*case['grid']['reference_face_area_m2']/n))
        volume=lambda s:sum(v0*f(s['mechanical_stretches'][i])*f(s['mechanical_stretches'][-1])**2 for i in range(n))
        pe=f(case['mechanics']['external_pressure_pa']);budget=n*f(p['energy_absolute_tolerance_j']);boundary=body=C=F(0);prefix=[]
        for k,s in enumerate(r['steps']):
            before,after=r['states'][k:k+2];require(s['start_s']==r['times_s'][k] and s['end_s']==r['times_s'][k+1] and f(s['end_s'])>f(s['start_s']),'panel clock')
            require(after['energy_model_identity']==initial['energy_model_identity'],'energy identity')
            ev=events.get(k);cor=ev['correction'] if ev else None
            if ev:require(after['amounts_mol'][ev['cell_index']][li]==0,'event zero')
            if cor:
                require(cor['cell_index']==ev['cell_index'] and cor['liquid_index']==li and cor['vapor_index']==vi,'correction indices')
                require(f(cor['ideal_liquid_increment_mol'])==-f(cor['liquid_before_mol']),'liquid correction')
                require(f(cor['ideal_vapor_increment_mol'])==f(cor['liquid_before_mol']),'paired ideal correction')
                require(f(cor['actual_vapor_increment_mol'])==f(after['amounts_mol'][ev['cell_index']][vi])-f(cor['vapor_before_mol']),'actual vapor correction')
            for i in range(n):
                for j in range(cols):
                    delta=f(s['face_species_mol'][i][j])-f(s['face_species_mol'][i+1][j])+f(s['reaction_species_mol'][i][j])
                    if cor and i==cor['cell_index']:
                        if j==li:delta+=f(cor['ideal_liquid_increment_mol'])
                        if j==vi:delta+=f(cor['actual_vapor_increment_mol'])
                    cn[i][j]+=delta
                    require(abs(f(after['amounts_mol'][i][j])-f(before['amounts_mol'][i][j])-delta)<=f(p['amount_absolute_tolerance_mol']),'local N')
                    require(abs(f(after['amounts_mol'][i][j])-f(initial['amounts_mol'][i][j])-cn[i][j])<=f(p['amount_absolute_tolerance_mol']),'prefix N')
                delta=f(s['face_energy_j'][i])-f(s['face_energy_j'][i+1])+f(s['cell_work_j'][i]);ce[i]+=delta
                require(abs(f(after['internal_energy_j'][i])-f(before['internal_energy_j'][i])-delta)<=f(p['energy_absolute_tolerance_j']),'local E')
                require(abs(f(after['internal_energy_j'][i])-f(initial['internal_energy_j'][i])-ce[i])<=f(p['energy_absolute_tolerance_j']),'prefix E')
                residual=f(s['cell_work_j'][i])-sum(f(v[i]) for v in s['cell_work_components_j'].values());require(residual==f(s['component_sum_residual_j'][i]),'component residual');ct[i]+=abs(residual);require(ct[i]<=f(p['energy_absolute_tolerance_j']),'component prefix')
            for i in range(n+1):
                delta=f(s['stretch_increment'][i]);cs[i]+=delta
                require(abs(f(after['mechanical_stretches'][i])-f(before['mechanical_stretches'][i])-delta)<=f(p['stretch_absolute_tolerance']),'local stretch')
                require(abs(f(after['mechanical_stretches'][i])-f(initial['mechanical_stretches'][i])-cs[i])<=f(p['stretch_absolute_tolerance']),'prefix stretch')
            boundary+=f(s['face_energy_j'][0])-f(s['face_energy_j'][-1]);body+=sum(map(f,s['cell_work_components_j']['body']))
            C+=abs(sum(map(f,s['cell_work_components_j']['mechanical_constraint'])))
            de=sum(f(b)-f(a) for a,b in zip(initial['internal_energy_j'],after['internal_energy_j']))
            global_e=de+pe*(volume(after)-volume(initial))-boundary-body
            require(abs(global_e)<=budget and C<=budget,'original global energy target')
            prefix.append({'index':k+1,'global_pressure_work_residual_j':str(global_e),'cumulative_absolute_constraint_sum_j':str(C)})
        report.update(audit_status='passed_saved_prefix_arithmetic',core_status=r['status'],core_reason=r['reason'],prefixes=prefix,events=len(r['events']),packets=len(r['packets']),original_global_target_j=str(budget))
    except Exception as exc:report['error']={'type':type(exc).__name__,'reason':str(exc),'traceback':traceback.format_exc()}
    (HERE/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    require(report['audit_status']=='passed_saved_prefix_arithmetic',str(report.get('error')))

if __name__=='__main__':main()
