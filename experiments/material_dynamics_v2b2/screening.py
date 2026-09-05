"""Discrete paired decisions only; a guard is not a proven global error bound."""
from scenarios import matrix

GUARD=.005


def paired_status(values,labels):
    if 'failed' in labels: return 'unknown_numerical'
    if len(values)!=2 or labels!=['passed_frozen_suite']*2: return 'unresolved_in_assumption_envelope'
    if all(f+GUARD<=.01 for f in values): return 'sampled_candidate_under_assumptions'
    if all(f-GUARD>.01 for f in values): return 'not_reached_in_sampled_domain'
    return 'unresolved_in_assumption_envelope'


def evaluate(frozen_manifest,diagnostics,verification):
    m=frozen_manifest['scenario_manifest']; config={r['scenario_id']:r for r in m['runs']}
    diag={d['scenario_id']:d for d in diagnostics}; pair_keys={i:p[0] for p in m['uncertainty_pairs'] for i in p}
    statuses={}
    for pair in m['uncertainty_pairs']:
        ds=[diag[i] for i in pair if i in diag]
        status=paired_status([d['at_end']['f_max'] for d in ds],[d['numerical_validation'] for d in ds])
        for i in pair: statuses[i]=status
    rows=[]
    for d in diagnostics:
        s=d['input']; sid=d['scenario_id']; r=d['at_end']; known=config.get(sid,{})
        frozen=d['verification_scope']=='frozen_suite'
        out=dict(scenario_id=sid,condition_key=pair_keys.get(sid,sid) if frozen else sid,
                 base_context_id=s['base_context_id'],program_id=known.get('program_id') if frozen else 'custom',
                 bundle_id=known.get('bundle_id') if frozen else 'custom',
                 Gamma=s['reaction']['Gamma'],length_ratio=s['geometry']['length_ratio'],
                 **s['transport'],K_ref=s['reaction']['K_ref'],theta=s['reaction']['theta'],
                 boundary_mode=s['boundary']['mode'],reservoir_ratio=s['boundary']['reservoir_ratio'],
                 tau_eval=r['tau'],H=r['H'],S_D=r['S_D'],S_B=r['S_B'],Da_O2_at_eval=r['Da_O2'],
                 **{k:r[k] for k in ('f_mean','f_max','u_core','u_surface','co2_body','co2_generated','co2_net_out')},
                 conversion_upper_bound=d['conversion_upper_bound'],
                 **{k+'_status':v['status'] for k,v in d['events'].items()},screening_guard_f=GUARD,
                 verification_scope=d['verification_scope'],numerical_validation=d['numerical_validation'],
                 screening_status=statuses.get(sid,'diagnostic_only') if frozen else 'diagnostic_only',mapping_status='unknown_real_material')
        if sid[:1] in 'RLC': out['screening_status']='diagnostic_only'
        rows.append(out)
    return rows
