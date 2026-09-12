"""Independent saved-state arithmetic only; no application/RHS/integrator import."""
from decimal import Decimal as D, getcontext, localcontext
import hashlib
import json
import math
from pathlib import Path
import traceback

getcontext().prec = 80
ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
STUDY = ROOT / 'docs/sandbox/research/cooling-spatial-v1'
BASE = Path('/private/tmp/brick-cooling-thermoelastic-v1')
OUT = Path(__file__).resolve().parent
C, B, ALPHA, VOL, TR = map(D, ('100000', '10', '.0001', '.0002', '300'))
ZERO = D(0)
ROUND = D(128) * D(2) ** -53 * 310 / 4
HASHES = {}


def dec(x):
    return D.from_float(x) if isinstance(x, float) else D(x)


def check(ok, label):
    if not ok:
        raise ValueError(label)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(x):
    if isinstance(x, list):
        for v in x:
            finite(v)
    elif isinstance(x, dict):
        for v in x.values():
            finite(v)
    elif isinstance(x, float):
        check(math.isfinite(x), 'nonfinite JSON float')


def read(path):
    HASHES[str(path)] = sha(path)
    value = json.loads(path.read_text())
    finite(value)
    return value


def write(name, value):
    with (OUT / name).open('x') as f:
        json.dump(value, f, default=str, allow_nan=False, indent=2)
        f.write('\n')


def peak(stats, name, value):
    stats[name] = max(stats.get(name, ZERO), abs(value))


def fields(values):
    t = list(map(dec, values))
    n = len(t)
    check(n in (16, 32, 64) and min(t) >= 290 and max(t) <= 310, 'T domain')
    mean, v = sum(t) / n, VOL / n
    stress = [D(100000) * (mean - x) for x in t]
    ce = [C - 2 * B * x for x in t]
    strain = ALPHA * (mean - TR)
    mismatch = [ALPHA * (mean - x) for x in t]
    check(min(ce) > 0 and max(map(abs, [strain, *mismatch, *(ALPHA * (x - TR) for x in t)])) <= D('.01'), 'mechanical/ce domain')
    u = [C * (x - TR) + B * (mean - x) * (mean + x) for x in t]
    logs = [(x / TR).ln() for x in t]
    s = [C * l + 2 * B * (mean - x) for x, l in zip(t, logs, strict=True)]
    psi = [C * ((x - TR) - x * l) + B * (mean - x)**2 for x, l in zip(t, logs, strict=True)]
    variance = sum((x - mean)**2 for x in t) / n
    return dict(t=t, n=n, v=v, mean=mean, strain=strain, stress=stress, ce=ce,
                u=u, s=s, psi=psi, variance=variance,
                U=v * sum(u), S=v * sum(s), PSI=v * sum(psi))


def reference():
    def atan_inverse(k):
        x = D(1) / k
        power, total = x, ZERO
        for i in range(1000):
            term = power / (2 * i + 1)
            total += term if i % 2 == 0 else -term
            if abs(term) < D('1e-85'):
                return total
            power *= x * x
        raise ValueError('reference series did not finish')
    pi = 16 * atan_inverse(5) - 4 * atan_inverse(239)
    i0 = 1 / (D(93960)**2 - D(40)**2).sqrt()
    icos = (D(93960) * i0 - 1) / 40
    rate = -(pi / D('.02'))**2 * 2 * icos / (C * i0)
    return pi, rate


PI, CONT_RATE = reference()


def trig(x, cosine=False):
    term = D(1) if cosine else x
    total = term
    for k in range(1, 200):
        term *= -x*x / ((2*k-1)*(2*k) if cosine else (2*k)*(2*k+1))
        total += term
        if abs(term) < D('1e-85'):
            return total
    raise ValueError('trig series did not finish')


def row_audit(row, observation, stresses, initial, stats):
    n = initial['n']
    check(len(row) == 3*n+1 and len(stresses) == n, 'saved state/stress shape')
    y = list(map(dec, row))
    f = fields(y[:n])
    h, w, z = y[n:2*n], y[2*n:3*n], y[-1]
    local = [f['v'] * (u - u0) - heat - work for u, u0, heat, work in zip(f['u'], initial['u'], h, w, strict=True)]
    global_error, entropy_error = f['U'] - initial['U'], f['S'] - initial['S'] - z
    stress_errors = [dec(a) - b for a, b in zip(stresses, f['stress'], strict=True)]
    for name, values in [('local_energy_j', local), ('reported_stress_error_pa', stress_errors)]:
        for value in values:
            peak(stats, name, value)
    for name, value in [('global_energy_j', global_error), ('entropy_j_k', entropy_error),
                        ('heat_sum_j', sum(h)), ('work_sum_j', sum(w)),
                        ('variance_U_identity_j', f['U'] - VOL * (C * (f['mean'] - TR) - B * f['variance']))]:
        peak(stats, name, value)
    stats['T_min_k'] = min(stats.get('T_min_k', min(f['t'])), min(f['t']))
    stats['T_max_k'] = max(stats.get('T_max_k', max(f['t'])), max(f['t']))
    gates = dict(local_energy=max(map(abs, local))/80 <= D('1e-8'),
                 global_energy=abs(global_error)/80 <= D('1e-8'),
                 entropy=abs(entropy_error)/(D(80)/300) <= D('1e-8'))
    check(gates == observation['gates'] and all(gates.values()), 'original per-point ledger gates')
    ledger = observation['ledger']
    check(ledger['external_heat_j'] == ledger['reservoir_entropy_j_k'] == 0, 'adiabatic external ledger')
    for a, b in zip(ledger['local_residual_j'], local, strict=True):
        peak(stats, 'saved_local_residual_minus_decimal_j', dec(a)-b)
    for name, target in [('global_residual_j', global_error), ('entropy_residual_j_k', entropy_error),
                         ('heat_sum_j', sum(h)), ('work_sum_j', sum(w))]:
        peak(stats, 'saved_'+name+'_minus_decimal', dec(ledger[name])-target)
    for name, target in [('mean_temperature_k', f['mean']), ('variance_k2', f['variance']),
                         ('common_strain', f['strain']), ('total_u_j', f['U']),
                         ('total_psi_j', f['PSI']), ('total_entropy_j_k', f['S']),
                         ('min_stress_pa', min(f['stress'])), ('max_stress_pa', max(f['stress']))]:
        peak(stats, 'saved_field_'+name+'_minus_decimal', dec(observation['fields'][name])-target)
    # A saved common rate suffices to inspect total power; it is not a new RHS.
    edot = dec(observation['fields']['common_strain_rate_s'])
    peak(stats, 'saved_total_mechanical_power_w_absolute', dec(observation['fields']['total_mechanical_power_w']))
    production = sum(D(n)/2 * (a-b)**2/(a*b) for a,b in zip(f['t'],f['t'][1:]))
    peak(stats, 'saved_production_minus_decimal_w_k', dec(observation['fields']['production_w_k'])-production)
    check(z >= 0 and observation['fields']['production_w_k'] >= 0, 'entropy production sign')
    check(abs(sum(2*f['v']*stress*edot for stress in f['stress'])) < D('1e-60'), 'exact zero membrane power')
    return dict(U_j=f['U'], S_j_k=f['S'], max_abs_local_residual_j=max(map(abs, local)),
        local_worst_index=max(range(n), key=lambda i: abs(local[i])), global_residual_j=global_error,
        entropy_residual_j_k=entropy_error, heat_sum_j=sum(h), work_sum_j=sum(w),
        max_abs_reported_stress_error_pa=max(map(abs, stress_errors)), original_gates=gates)


def dense_audit(saved, first_interval):
    lo, hi = dec(saved['left_s']), dec(saved['right_s'])
    check(first_interval[0] == saved['left_s'] and first_interval[1] == saved['right_s'], 'worst segment linkage')
    coefficients = [[dec(x) for x in row] for row in saved['D_temperatures']]
    lower, upper = list(coefficients[0]), list(coefficients[0])
    magnitude = [abs(x) for x in coefficients[0]]
    prefix = (D(1), D(1))
    def mul(a,b):
        products = [x*y for x in a for y in b]
        return min(products), max(products)
    for j in range(saved['order']):
        shift, denom = dec(saved['t_shift'][j]), dec(saved['denom'][j])
        check(denom > 0, 'dense denominator')
        prefix = mul(prefix, ((lo-shift)/denom, (hi-shift)/denom))
        for i, coefficient in enumerate(coefficients[j+1]):
            a,b = mul(prefix, (coefficient,coefficient))
            lower[i] += a
            upper[i] += b
            magnitude[i] += max(abs(a),abs(b))
    # This reconstructs the real stored-coefficient interval, then includes the
    # registered 64u evaluation margin. Decimal rounding is <1e-60 here.
    margins = [D(64)*D(2)**-53*x + D('1e-60') for x in magnitude]
    for i in range(len(lower)):
        check(dec(saved['temperature_bounds_k'][0][i]) <= lower[i]-margins[i]
              and dec(saved['temperature_bounds_k'][1][i]) >= upper[i]+margins[i], 'saved outward dense bounds fail enclosure')
    check(saved['within_domain'] is True and min(lower) >= 290 and max(upper) <= 310, 'dense domain')
    return dict(order=saved['order'], left_s=saved['left_s'], right_s=saved['right_s'],
        real_polynomial_lower_k=min(lower), real_polynomial_upper_k=max(upper),
        all_saved_per_cell_bounds_enclose_80_digit_interval_with_64u_margin=True,
        limitation='Only the saved worst polynomial was independently reconstructed; other intervals retain saved scalar bounds.')


def witness_audit(audit, n):
    output = {}
    for group in ('extrema','residuals'):
        for name, witness in audit[group].items():
            t = list(map(dec, witness['temperatures_k']))
            r = list(map(dec, witness['rates_k_s']))
            check(len(t) == len(r) == n and 0 <= witness['time_s'] <= 10, 'witness shape/time')
            f = fields(t)
            mdot = sum(r)/n
            flux = [D(n)/2*(a-b) for a,b in zip(t,t[1:])]
            face = [ZERO,*flux,ZERO]
            heat = [face[i]-face[i+1] for i in range(n)]
            matrix = [(C-2*B*t[i])*r[i]+2*B*t[i]*mdot-heat[i]/f['v'] for i in range(n)]
            power = [2*f['v']*stress*ALPHA*mdot for stress in f['stress']]
            udot = [(C-2*B*x)*rate+2*B*f['mean']*mdot for x,rate in zip(t,r,strict=True)]
            law = [f['v']*udot[i]-heat[i]-power[i] for i in range(n)]
            s_eq = [x*((C/x-2*B)*rate+2*B*mdot)-heat[i]/f['v'] for i,(x,rate) in enumerate(zip(t,r,strict=True))]
            vector = None
            if name in ('thermal_equation_w_m3','entropy_equation_w_m3','local_first_law_w','total_mechanical_power_w'):
                vector = {'thermal_equation_w_m3':matrix,'entropy_equation_w_m3':s_eq,
                          'local_first_law_w':law,'total_mechanical_power_w':[sum(power)]}[name]
            elif group == 'extrema':
                if 'temperature' in name: vector=t
                elif 'ce_' in name: vector=f['ce']
                else: vector=[D('.01')-abs(x) for x in [f['strain'],*(ALPHA*(x-TR) for x in t),*(ALPHA*(f['mean']-x) for x in t)]]
            output[group+'/'+name] = dict(time_s=witness['time_s'], kind=witness['kind'],
                index=witness['index'], stored_value=witness['value'],
                directly_reconstructed_selected_value=None if vector is None else vector[witness['index']],
                discrepancy=None if vector is None else dec(witness['value'])-vector[witness['index']],
                max_matrix_residual_w_m3=max(map(abs,matrix)), max_local_first_law_residual_w=max(map(abs,law)),
                limitation=None if vector is not None else 'Candidate primitive return value was not saved; this residual cannot independently be reproduced from T/r alone.')
    return output


def restrict(values):
    return [[sum(row[i:i+2])/2 for i in range(0,len(row),2)] for row in values]


def subtract(left,right):
    return [[a-b for a,b in zip(x,y,strict=True)] for x,y in zip(left,right,strict=True)]


def norms(values,scale=D(4)):
    flat=[x for row in values for x in row]
    return dict(infinity=max(map(abs,flat))/scale,two=(sum(x*x for x in flat)/len(flat)).sqrt()/scale)


def package_identity():
    package=read(BASE/'SPATIAL_PACKAGE_BEFORE.json')
    freeze=read(BASE/'SOURCE_FREEZE.json')
    installed=read(BASE/'INSTALLED_MATCH.json')
    check(package['source_freeze_sha256']==sha(BASE/'SOURCE_FREEZE.json') and package['issues']==[], 'package precheck')
    for name,entry in freeze['files'].items():
        for root in [Path(freeze['root']),Path(installed['installed_root'])]:
            path=root/name
            check(sha(path)==entry['sha256'] and path.stat().st_size==entry['bytes'],'package identity:'+name)
    check(len(freeze['files'])==package['files']==163,'package count')
    return dict(files_checked_against_source_and_installed=163,
                plate_sha256=freeze['files']['cooling_thermoelastic_plate.py']['sha256'])


def main():
    package=package_identity()
    comparison=read(BASE/'SPATIAL_COMPARISON01.json')
    reports,results,executions,trajectory_audits={},{},{},{}
    point_count=accepted_total=0
    with localcontext():
        for n in (16,32,64):
            directory=BASE/f'spatial-n{n}-01'
            start,execution=read(directory/'START.json'),read(directory/'EXECUTION.json')
            inputs,summary=read(directory/'worker/INPUT.json'),read(directory/'worker/result.json')
            executions[n]=execution;results[n]=summary;reports[n]={}
            check(execution['returncode']==0 and execution['child_reaped'] is True and execution['timed_out'] is False
                  and execution['passed'] is True and execution['within_wall_limit'] is True
                  and execution['inputs_unchanged'] is True and execution['evidence_errors']=={},'supervisor terminal')
            check(start['cells']==execution['cells']==n and start['timeout_s']==execution['timeout_s']==30
                  and execution['elapsed_s']<=30 and execution['input_sha256_before']==execution['input_sha256_after'],'supervisor limits/identity')
            check(start['input_sha256_before']==execution['input_sha256_before'] and start['command']==execution['command'],'START/EXECUTION linkage')
            for filename,expected in execution['input_sha256_before'].items(): check(sha(Path(filename))==expected,'supervised input SHA')
            identity=inputs['identity']
            for entry in [identity['protocol'],identity['driver'],identity['bdf'],*identity['core'].values()]:
                check(sha(Path(entry['path']))==entry['sha256'],'runtime file identity')
            check(identity['protocol']['sha256']=='dfa6363b6e83d0a2de8495153ce81c7a814ee55901d54a43f84f790baa7872fb','frozen protocol')
            check(identity['core']['plate']['sha256']=='33851857946f16b560529ad8a9d3ab1bc4fec6c1a18ae63bb9897d77a03746d7','frozen plate')
            check(summary['status']=='completed' and summary['completed_policies']==['coarse','fine'] and summary['real_time_integration'] is True,'summary completion')
            check(inputs['parameters']==dict(M=1e9,alpha=1e-4,C=1e5,k=1.,Tr=300.,L=.02,A=.01,temperature_bounds_k=[290.,310.],strain_bounds=[-.01,.01],coefficient_classification='manufactured',boundary='adiabatic'),'frozen inputs')
            for name in ('coarse','fine'):
                folder=directory/'worker'/name
                report=read(folder/'policy.json'); reports[n][name]=report
                policy=dict(method='BDF',rtol=1e-9,atol=1e-11,max_step=.05) if name=='coarse' else dict(method='BDF',rtol=1e-11,atol=1e-13,max_step=.025)
                check(report['status']=='completed' and report['failure'] is None and report['gate_failures']==[]
                      and report['cells']==n and report['policy_name']==name and report['policy']==policy,'policy completion/identity')
                check(report['solver_status']=='finished' and report['reached_time_s']==10 and report['real_time_integration'] is True,'actual terminal')
                check(report['state_layout']==dict(T=[0,n,'K'],H=[n,2*n,'J'],W=[2*n,3*n,'J'],Z=[3*n,3*n+1,'J/K'])
                      and report['atol_vector']==[policy['atol']]*(3*n+1),'state/atol layout')
                check(report['material_qualified'] is report['source_material_qualified'] is False,'material scope')
                check(report['times_s']==[i/10 for i in range(101)] and len(report['samples'])==len(report['observations'])==len(report['reported_stress_pa'])==101,'sample shape/grid')
                initial=fields(report['initial_temperatures_k'])
                x=PI/(2*n);sinc=trig(x)/x
                init_error=max(abs(t-(302+2*sinc*trig(PI*(D(i)+D('.5'))/n,True))) for i,t in enumerate(initial['t']))
                check(init_error/4<=ROUND,'independent initial cell averages')
                stats={}; sample_stats={}; accepted_stats={}
                for time,row,observation,stress in zip(report['times_s'],report['samples'],report['observations'],report['reported_stress_pa'],strict=True):
                    check(observation['time_s']==time,'sample time linkage')
                    row_audit(row,observation,stress,initial,sample_stats)
                    point_count+=1
                accepted_path=folder/'accepted.jsonl';HASHES[str(accepted_path)]=sha(accepted_path)
                accepted=[]
                with accepted_path.open() as file:
                    for line in file:
                        check(line.endswith('\n'),'partial accepted line')
                        row=json.loads(line);finite(row);accepted.append(row)
                        row_audit(row['state'],row,row['reported_stress_pa'],initial,accepted_stats)
                accepted_total+=len(accepted)
                check(len(accepted)==report['accepted_count'] and accepted[0]['time_s']==0 and accepted[-1]['time_s']==10,'accepted completeness')
                check(accepted[0]['state']==report['samples'][0],'initial accepted/sample identity')
                endpoint_delta=[abs(dec(a)-dec(b)) for a,b in zip(accepted[-1]['state'],report['samples'][-1],strict=True)]
                check(max(endpoint_delta[:n])/4<=ROUND,'terminal accepted/dense temperature comparison')
                check(accepted[0]['state'][:n]==report['initial_temperatures_k'] and accepted[0]['state'][n:]==[0.]*(2*n+1),'initial cumulative zero')
                margin=D(100);min_lower=D(1000);max_upper=ZERO
                for previous,current in zip(accepted,accepted[1:]):
                    dt=current['time_s']-previous['time_s']
                    check(0<dt<=policy['max_step']+2e-15,'accepted progress/max step')
                    low,high=current['preceding_dense_bounds_k']
                    check(290<=low<=high<=310,'saved dense segment domain')
                    check(low<=min(previous['state'][:n]+current['state'][:n]) and high>=max(previous['state'][:n]+current['state'][:n]),'segment endpoint enclosure')
                    min_lower=min(min_lower,dec(low));max_upper=max(max_upper,dec(high));margin=min(margin,dec(low)-290,310-dec(high))
                check(report['dense_segments']==len(accepted)-1,'dense segment count')
                worst=report['worst_dense_segment']
                check(abs(dec(worst['domain_margin_k'])-margin)<=D('1e-13'),'worst dense margin matches all saved segments')
                calls=report['stage_audit']['calls']
                check(calls==dict(rhs=report['nfev'],jacobian=report['njev'],accepted=len(accepted),sample=101),'actual call counters')
                check(type(report['nlu']) is int and report['nlu']>0,'actual nlu')
                original_gates=dict(completed_interval=True,all_dense_segments_in_domain=True,
                    local_energy=max(sample_stats['local_energy_j'],accepted_stats['local_energy_j'])/80<=D('1e-8'),
                    global_energy=max(sample_stats['global_energy_j'],accepted_stats['global_energy_j'])/80<=D('1e-8'),
                    entropy=max(sample_stats['entropy_j_k'],accepted_stats['entropy_j_k'])/(D(80)/300)<=D('1e-8'))
                check(original_gates==report['gates'],'policy original gates')
                trajectory_audits[f'N{n}_{name}']=dict(samples=101,accepted_states=len(accepted),counts=calls,nlu=report['nlu'],
                    initial_formula_error_k=init_error,initial_U_j=initial['U'],initial_formula_U_j=40-D('.004')*sinc*sinc,
                    initial_projection_j=40-D('.004')*sinc*sinc-D('39.996'),sample=sample_stats,accepted=accepted_stats,
                    accepted_vs_dense_endpoint=dict(max_temperature_k=max(endpoint_delta[:n]),max_heat_j=max(endpoint_delta[n:2*n]),max_work_j=max(endpoint_delta[2*n:3*n]),entropy_j_k=endpoint_delta[-1]),
                    dense_segments=len(accepted)-1,all_saved_dense_minimum_k=min_lower,all_saved_dense_maximum_k=max_upper,
                    worst_dense=dense_audit(worst,(accepted[0]['time_s'],accepted[1]['time_s'])),
                    saved_worst_witnesses=witness_audit(report['stage_audit'],n),original_gates=original_gates)
    check(point_count==606 and accepted_total==2058,'whole-study point counts')
    cross=cross_grid(reports,comparison)
    elapsed=sum(dec(e['elapsed_s']) for e in executions.values())
    span=dec(executions[64]['started_monotonic'])+dec(executions[64]['elapsed_s'])-dec(executions[16]['started_monotonic'])
    check(elapsed<=90 and span<=90 and all(dec(executions[a]['started_monotonic'])+dec(executions[a]['elapsed_s'])<=dec(executions[b]['started_monotonic']) for a,b in ((16,32),(32,64))),'sequential overall resource interval')
    for name,expected in HASHES.items():check(sha(Path(name))==expected,'input changed during audit')
    write('AUDIT01.json',dict(status='passed_saved_arithmetic_audit',decimal_precision=80,
        no_application_scipy_RHS_or_time_integration=True,package=package,
        comparison_count=point_count,accepted_count=accepted_total,trajectories=trajectory_audits,
        cross_grid=cross,supervision_elapsed_s={n:e['elapsed_s'] for n,e in executions.items()},
        supervised_time_sum_s=elapsed,first_start_to_last_completion_span_s=span,source_hashes=HASHES,
        original_files_unchanged=True,material_qualified=False,full_cycle_qualified=False))
    print('saved arithmetic audit passed; 606 samples and 2058 accepted states')


def cross_grid(reports,saved):
    temporal={};spatial={}; rates={}
    for n in (16,32,64):
        t={name:[[dec(x) for x in row[:n]] for row in reports[n][name]['samples']] for name in ('coarse','fine')}
        temporal[n]=norms(subtract(t['coarse'],t['fine']))
        check(temporal[n]['infinity']<=D('1e-7'),'time refinement gate')
        for norm in ('infinity','two'):
            check(abs(temporal[n][norm]-dec(saved['temporal_norms'][str(n)][norm]))<=ROUND,'saved temporal norm')
        rr=list(map(dec,reports[n]['fine']['initial_mean_rate']['temperature_rates_k_s']))
        observed=sum(rr)/n;err=abs(observed-CONT_RATE)
        floor=D(128)*D(2)**-53*max(D(1),max(map(abs,rr)))/D('.4')
        check(observed<0 and err/D('.4')>100*floor,'initial actual rate gates')
        check(reports[n]['coarse']['initial_mean_rate']['temperature_rates_k_s']==reports[n]['fine']['initial_mean_rate']['temperature_rates_k_s'],'same actual initial rates')
        rates[n]=dict(observed_k_s=observed,error_k_s=err,normalized_error=err/D('.4'),normalized_roundoff=floor)
        check(abs(observed-dec(saved['initial_rates'][str(n)]['observed_k_s']))<D('1e-18'),'saved actual mean rate')
    for name in ('coarse','fine'):
        t={n:[[dec(x) for x in row[:n]] for row in reports[n][name]['samples']] for n in (16,32,64)}
        middle=restrict(t[32]);high=restrict(restrict(t[64]))
        diffs={16:subtract(t[16],middle),32:subtract(middle,high)}
        sizes={n:norms(diffs[n]) for n in (16,32)};out={}
        for n in (16,32):
            for a,b in zip(diffs[n],saved['spatial'][name]['temperature_differences_k'][str(n)],strict=True):
                check(max(abs(x-dec(y)) for x,y in zip(a,b,strict=True))/4<=ROUND,'all saved restricted differences')
        for norm in ('infinity','two'):
            low,high=sizes[16][norm],sizes[32][norm]
            order=(low/high).ln()/D(2).ln()
            separated=temporal[16][norm]+temporal[32][norm]<=D('.02')*low and temporal[32][norm]+temporal[64][norm]<=D('.02')*high
            check(min(low,high)>100*ROUND and separated and D('1.8')<=order<=D('2.2') and high/3<=D('1e-4'),'original spatial gates')
            original=saved['spatial'][name]['norms'][norm]
            check(original['resolved'] is original['time_separated'] is True and original['diagnosis']=='second_order','saved spatial diagnosis')
            out[norm]=dict(D16=low,D32=high,order=order,richardson=high/3,
                time_ratio_low=(temporal[16][norm]+temporal[32][norm])/low,
                time_ratio_high=(temporal[32][norm]+temporal[64][norm])/high,
                saved_order_minus_decimal=dec(original['order'])-order)
        check(max(abs(x) for rows in diffs.values() for x in rows[0])/4<=ROUND,'initial restriction')
        stresses={n:[[dec(x) for x in row] for row in reports[n][name]['reported_stress_pa']] for n in (16,32,64)}
        sm=restrict(stresses[32]);sh=restrict(restrict(stresses[64]))
        stress_sizes={16:norms(subtract(stresses[16],sm),D(400000)),32:norms(subtract(sm,sh),D(400000))}
        for n in (16,32):
            for norm in ('infinity','two'):
                check(abs(stress_sizes[n][norm]-dec(saved['spatial'][name]['stress_normalized_differences'][str(n)][norm]))<=ROUND,'actual stress restricted norm')
        spatial[name]=dict(temperature=out,actual_reported_stress=stress_sizes)
    orders=[(rates[a]['error_k_s']/rates[b]['error_k_s']).ln()/D(2).ln() for a,b in ((16,32),(32,64))]
    check(all(D('1.8')<=p<=D('2.2') for p in orders),'initial rate convergence')
    check(saved['status']=='passed' and all(v is True for v in saved['gates'].values()),'saved combined gates')
    check(saved['material_qualified'] is saved['source_material_qualified'] is saved['full_cycle_qualified'] is False,'qualification boundary')
    return dict(temporal=temporal,spatial=spatial,initial_continuous_rate_k_s=CONT_RATE,
                initial_rates=rates,initial_rate_orders=orders,
                saved_gate_count=len(saved['gates']),all_original_numeric_gates_reproduced=True)


if __name__=='__main__':
    try:
        main()
    except Exception:
        failure_name=next(f'ATTEMPT{i:02}_FAILURE.json' for i in range(1,100) if not (OUT/f'ATTEMPT{i:02}_FAILURE.json').exists())
        write(failure_name,dict(status='saved_audit_script_failed',traceback=traceback.format_exc(),
            no_physical_run_or_original_output_modified=True))
        raise
