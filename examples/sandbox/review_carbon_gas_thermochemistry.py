"""Caloric source arithmetic and exact-rational Cp positivity for C/O gases."""
import argparse
from fractions import Fraction
import json
from math import comb
from pathlib import Path
import sys

from mpmath import mp

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_reaction_affinity import RecordedThermalPhase


def cp_certificate(coefficients,policy):
    a,b,c,d,e=map(Fraction,coefficients)
    power=[c,Fraction(0),Fraction(0),d,a,Fraction(0),b,Fraction(0),e]
    lo,hi=map(Fraction,policy['sqrt_temperature_cover']);count=policy['equal_subintervals'];degree=policy['polynomial_degree'];records=[]
    for i in range(count):
        left=lo+(hi-lo)*i/count;right=lo+(hi-lo)*(i+1)/count;width=right-left
        q=[sum(power[j]*comb(j,k)*left**(j-k)*width**k for j in range(k,degree+1)) for k in range(degree+1)]
        beta=[sum(q[j]*Fraction(comb(k,j),comb(degree,j)) for j in range(k+1)) for k in range(degree+1)]
        lower=min(beta)/right**4
        records.append({'sqrt_temperature_interval':[str(left),str(right)],'cp_lower_bound_j_mol_k':float(lower),'exact_lower_bound':str(lower),'strictly_positive':lower>0})
    return {'method':'z=sqrt(T), z^4 Cp is an eighth-degree polynomial. Exact rational runtime coefficients expanded in Bernstein form on each rational interval; divide its positive minimum coefficient by right^4. The cover contains the whole selected T domain.','intervals':records,'whole_cover_positive':all(r['strictly_positive'] for r in records),'minimum_lower_bound_j_mol_k':min(r['cp_lower_bound_j_mol_k'] for r in records)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    source=json.loads((root/settings['source_file']).read_text());mp.dps=settings['decimal_digits'];records={}
    for name,data in source['phases'].items():
        coefficients=tuple(float(c) for c in data['cp_coefficient_strings']);t0=float(source['reference_temperature_k'])
        phase=RecordedThermalPhase(coefficients,t0,float(data['reference_enthalpy_j_mol']),float(data['reference_entropy_j_mol_k']),tuple(settings['selected_temperature_domain_k']))
        a,b,c,d,e=map(mp.mpf,coefficients)
        def cp(t):return a+b*t+c/t**2+d/mp.sqrt(t)+e*t*t
        maxima={k:0. for k in settings['numerical_budgets']};points=[]
        for t in settings['review_temperatures_k']:
            state=phase.standard(t);start,end=mp.mpf(t0),mp.mpf(t)
            h=mp.mpf(phase.reference_enthalpy_j_mol)+mp.quad(cp,[start,end])
            s=mp.mpf(phase.reference_entropy_j_mol_k)+mp.quad(lambda value:cp(value)/value,[start,end])
            errors={'cp_j_mol_k':float(abs(cp(end)-mp.mpf(state['cp_j_mol_k']))),'enthalpy_j_mol':float(abs(h-mp.mpf(state['enthalpy_j_mol']))),'entropy_j_mol_k':float(abs(s-mp.mpf(state['entropy_j_mol_k'])))}
            maxima={k:max(v,errors[k]) for k,v in maxima.items()};points.append({'temperature_k':t,'source_formula':state,'independent_integral_errors':errors})
        printed=[]
        for point in data['source_table']:
            t=float(point['temperature_k']);state=phase.standard(t)
            values={k:state[k] for k in ['cp_j_mol_k','entropy_j_mol_k']};values['sensible_enthalpy_over_t_j_mol_k']=state['sensible_enthalpy_j_mol']/t
            difference={k:values[k]-float(point[k]) for k in settings['source_print_half_units']}
            printed.append({'printed':point,'nominal_minus_printed':difference,'inside_table_print_half_units':{k:abs(v)<=settings['source_print_half_units'][k] for k,v in difference.items()}})
        certificate=cp_certificate(coefficients,settings['cp_certificate'])
        flags={k:v<=settings['numerical_budgets'][k] for k,v in maxima.items()};flags['whole_domain_positive_cp']=certificate['whole_cover_positive']
        records[name]={'points':points,'maximum_integral_errors':maxima,'within_numerical_budgets':flags,'cp_certificate':certificate,'table_comparisons':printed,
            'maximum_nominal_table_differences':{k:max(abs(r['nominal_minus_printed'][k]) for r in printed) for k in settings['source_print_half_units']},
            'all_table_print_half_units_met':all(all(r['inside_table_print_half_units'].values()) for r in printed)}
    other=source['nist_co_cross_source_comparison'];co=source['phases']['CO'];co_at_reference=records['CO']['points'][0]['source_formula']
    comparison={'nist_minus_usgs_entropy_j_mol_k':float(other['entropy_j_mol_k'])-float(co['reference_entropy_j_mol_k']),
        'nist_minus_usgs_reference_enthalpy_j_mol':float(other['enthalpy_j_mol'])-float(co['reference_enthalpy_j_mol']),
        'nist_minus_usgs_formula_cp_j_mol_k':float(other['cp_j_mol_k'])-co_at_reference['cp_j_mol_k'],
        'scope':'Different published nominal compilations; no pooled uncertainty or source replacement.'}
    result={'settings':settings,'source':source,'records':records,'nist_co_comparison':comparison,
        'all_requested_numerical_relations_met':all(all(r['within_numerical_budgets'].values()) for r in records.values()),
        'all_table_print_half_units_met':all(r['all_table_print_half_units_met'] for r in records.values()),
        'material_qualified':False,'training_eligible':False,'scope':'Positive nominal Cp and thermodynamic integration arithmetic, separate from source fit accuracy and real-char chemistry. No equilibrium composition or time process run in this review.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_relations_met':result['all_requested_numerical_relations_met'],'all_table_print_half_units_met':result['all_table_print_half_units_met'],'nist_co_comparison':comparison}))


if __name__=='__main__':main()
