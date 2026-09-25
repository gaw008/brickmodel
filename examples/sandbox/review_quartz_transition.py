"""Independent source quadrature, latent-heat and reference-join review."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import sys

from mpmath import mp

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_quartz_transition import RecordedQuartzTransition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text()); p = json.loads((root/settings['model_parameters']).read_text())
    source = json.loads((root/p['source_facts_file']).read_text()); model = RecordedQuartzTransition(source,p)
    mp.dps = settings['decimal_digits']; scale = mp.mpf(model.scale); tt = mp.mpf(model.tt)
    def cp(phase,t):
        a,b,c,d,e,*_ = map(mp.mpf,model.coefficients[phase]); x=t/scale
        return a+b*x+c*x*x+d*x*x*x+e/(x*x)
    def standard(phase,t):
        h,s = mp.mpf(model.h0),mp.mpf(model.s0); t0 = mp.mpf(model.t0)
        end = t if phase==0 else tt
        h += mp.quad(lambda v:cp(0,v),[t0,end]); s += mp.quad(lambda v:cp(0,v)/v,[t0,end])
        if phase:
            h += mp.mpf(model.latent)+mp.quad(lambda v:cp(1,v),[tt,t])
            s += mp.mpf(model.latent)/tt+mp.quad(lambda v:cp(1,v)/v,[tt,t])
        return h,s
    records=[]; budget=p['verification']
    for t in settings['temperatures_k']:
        phase=int(t>=model.tt); state=model.pure_state(phase,t); h,s=standard(phase,mp.mpf(t))
        dh,ds=float(abs(mp.mpf(state['enthalpy_j_mol'])-h)),float(abs(mp.mpf(state['entropy_j_mol_k'])-s))
        records.append({'phase':state['phase'],'temperature_k':t,'enthalpy_difference_j_mol':dh,
            'entropy_difference_j_mol_k':ds,'cp_j_mol_k':state['cp_j_mol_k'],
            'within_budget':dh<=budget['source_quadrature_h_j_mol'] and ds<=budget['source_quadrature_s_j_mol_k']})
    transition=[]
    for f in settings['transition_high_phase_fractions']:
        h=model.ha+f*model.latent; state=model.from_enthalpy(h)
        expected_s=model.sa+(h-model.ha)/model.tt
        transition.append({'input_beta_fraction':f,'state':state,'entropy_difference_j_mol_k':state['entropy_j_mol_k']-expected_s,
                           'gibbs_j_mol':h-model.tt*state['entropy_j_mol_k']})
    fitted=[]
    for phase in (0,1):
        t=model.tt; x=t/model.scale; a,b,c,d,e,ff,g,_=model.coefficients[phase]
        hfit=model.scale*(a*x+b*x*x/2+c*x**3/3+d*x**4/4-e/x+ff)
        sfit=float(a*mp.log(x)+b*x+c*x*x/2+d*x**3/3-e/(2*x*x)+g)
        state=model.pure_state(phase,t)
        fitted.append({'phase':state['phase'],'temperature_k':t,'source_fitted_enthalpy_j_mol':hfit,
            'source_fitted_entropy_j_mol_k':sfit,'derived_enthalpy_shift_j_mol':state['enthalpy_j_mol']-hfit,
            'derived_entropy_shift_j_mol_k':state['entropy_j_mol_k']-sfit})
    table=[]
    for row in settings['source_table_rows']:
        state=model.pure_state(int(row['temperature_k']>=model.tt),row['temperature_k'])
        differences={'cp_j_mol_k':state['cp_j_mol_k']-row['cp_j_mol_k'],
            's_j_mol_k':state['entropy_j_mol_k']-row['s_j_mol_k'],
            'h_increment_j_mol':state['enthalpy_j_mol']-model.h0-row['h_increment_j_mol']}
        table.append({'source':row,'differences':differences,
            'within_printing_intervals_only':{k:abs(v)<=settings['printed_intervals_only'][k] for k,v in differences.items()}})
    ha,sa=standard(0,tt); hb,sb=standard(1,tt)
    gap=float(abs((hb-ha)-tt*(sb-sa)))
    gspread=max(r['gibbs_j_mol'] for r in transition)-min(r['gibbs_j_mol'] for r in transition)
    capacity_bounds=[]
    for phase,interval in enumerate(((model.domain[0],model.tt),(model.tt,model.domain[1]))):
        a,b,c,d,e,*_=map(Fraction,model.coefficients[phase]);x,y=(Fraction(t)/Fraction(model.scale) for t in interval)
        candidates=[x,y];vertex=-c/(3*d)
        if x<vertex<y:candidates.append(vertex)
        # Both recorded sources have d>0 and e>0. This is a direct bound
        # on their dCp/dx quadratic minus 2E/x^3, without grid sampling.
        derivative_lower=min(b+2*c*t+3*d*t*t for t in candidates)-2*e/x**3
        cp_at_low=a+b*x+c*x*x+d*x**3+e/x**2
        capacity_bounds.append({'phase':phase,'temperature_interval_k':interval,
            'source_D_positive':d>0,'source_E_positive':e>0,
            'dcp_dx_lower_bound':math.nextafter(float(derivative_lower),-math.inf),
            'cp_lower_bound_j_mol_k':math.nextafter(float(cp_at_low),-math.inf),
            'monotonic_positive_capacity_proved_for_recorded_coefficients':d>0 and e>0 and derivative_lower>0 and cp_at_low>0})
    result={'settings':settings,'model_parameters':p,'source_facts':source,'source_quadrature':records,
        'transition_states':transition,'independent_gibbs_gap_j_mol':gap,'mixture_gibbs_spread_j_mol':gspread,
        'capacity_domain_bounds':capacity_bounds,
        'original_fit_constant_shifts':fitted,'original_janaf_table_comparisons':table,
        'all_declared_thermodynamic_arithmetic_budgets_met':all(r['within_budget'] for r in records) and gap<=budget['equal_gibbs_j_mol'] and gspread<=budget['equal_gibbs_j_mol'] and all(r['monotonic_positive_capacity_proved_for_recorded_coefficients'] for r in capacity_bounds),
        'scope':'Source-derived thermodynamically consistent join. Original fitted h/S and JANAF differences remain visible; arithmetic agreement is not empirical error certification.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'arithmetic_passed':result['all_declared_thermodynamic_arithmetic_budgets_met'],'original_fit_constant_shifts':fitted,
        'source_table_maxima':{k:max(abs(row['differences'][k]) for row in table) for k in settings['printed_intervals_only']}}))


if __name__=='__main__':main()
