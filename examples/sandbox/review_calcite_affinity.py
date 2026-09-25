"""Same-source reaction free energy, printed-table and thermodynamic review."""
import argparse
from decimal import Decimal
import json
import math
from pathlib import Path
import re

from scipy.integrate import quad
from scipy.optimize import brentq

from calcite_affinity_setup import build


def half_printed_unit(value):
    return float(Decimal(5).scaleb(Decimal(value).as_tuple().exponent-1))


def rounding_gibbs(phase, source, t, tref, kj):
    # Independent coefficients multiply H increment - T*S increment.
    dh=[t-tref,(t*t-tref*tref)/2,1/tref-1/t,2*(math.sqrt(t)-math.sqrt(tref)),(t**3-tref**3)/3]
    ds=[math.log(t/tref),t-tref,(1/tref**2-1/t**2)/2,2*(1/math.sqrt(tref)-1/math.sqrt(t)),(t*t-tref*tref)/2]
    coefficients=phase['cp']['coefficients_printed']
    radius=half_printed_unit(phase['reference_298']['hf_kj_mol'])*kj
    radius+=t*half_printed_unit(source['entropy_reference_j_mol_k'])
    for key,h,s in zip(('A1','A2','A3','A4','A5'),dh,ds,strict=True):
        if coefficients[key] is not None:
            radius+=half_printed_unit(coefficients[key])*abs(h-t*s)
    return radius


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    reaction,source,facts=build(root,settings);review=settings['verification'];budget=review['budgets']
    source_rows=[];arithmetic=[];tref=float(facts['reference_state']['temperature_k'])
    r=reaction.gas_constant_j_mol_k;kj=settings['joules_per_kilojoule']
    phases={p['id']:p for p in facts['species']};nu=reaction.stoichiometry
    composition={k:{element:int(count) if count else 1 for element,count in re.findall(r'([A-Z][a-z]?)([0-9]*)',p['formula'])}
                 for k,p in phases.items()}
    elements=sorted({element for counts in composition.values() for element in counts})
    element_balance={element:math.fsum(nu[k]*counts[element] for k,counts in composition.items() if element in counts) for element in elements}
    mass_balance=sum(Decimal(facts['reaction']['stoichiometry_mol_per_mol_extent'][k])*Decimal(p['molar_mass_g_mol']) for k,p in phases.items())
    options={'epsabs':review['quadrature_absolute_tolerance'],'epsrel':review['quadrature_relative_tolerance'],
             'limit':review['quadrature_maximum_subintervals']}
    for i,text_t in enumerate(source['temperature_points_k']):
        t=float(text_t);state=reaction.standard(t);g=state['reaction']['gibbs_j_mol']
        source_g=math.fsum(nu[k]*float(p['formation_gibbs_kj_mol'][i])*kj for k,p in source['phases'].items())
        logk=math.fsum(nu[k]*float(p['formation_log10_k'][i]) for k,p in source['phases'].items())
        model_radius=math.fsum(abs(nu[k])*rounding_gibbs(phases[k],source['phases'][k],t,tref,kj) for k in phases)
        g_radius=math.fsum(abs(nu[k])*half_printed_unit(p['formation_gibbs_kj_mol'][i])*kj for k,p in source['phases'].items())
        log_radius=math.fsum(abs(nu[k])*half_printed_unit(p['formation_log10_k'][i]) for k,p in source['phases'].items())
        r_radius=half_printed_unit(facts['reference_state']['gas_constant_j_mol_k'])
        log_model=-g/(r*t*math.log(10))
        log_envelope=log_radius+model_radius/(r*t*math.log(10))+abs(log_model)*r_radius/(r-r_radius)
        source_rows.append({'temperature_k':t,'model_reaction_gibbs_j_mol':g,'table_reaction_gibbs_j_mol':source_g,
            'difference_j_mol':g-source_g,'printed_gibbs_combined_envelope_j_mol':model_radius+g_radius,
            'model_log10_equilibrium_pressure_ratio':log_model,'table_reaction_log10_k':logk,
            'log10_difference':log_model-logk,'printed_log10_combined_envelope':log_envelope,
            'within_printed_arithmetic_envelopes':{'gibbs':abs(g-source_g)<=model_radius+g_radius,'log10_k':abs(log_model-logk)<=log_envelope}})
        for name,p in phases.items():
            a,b,c,d,e=(float(p['cp']['coefficients_nominal'][key]) for key in ('A1','A2','A3','A4','A5'))
            cp=lambda u:a+b*u+c/(u*u)+d/u**0.5+e*u*u
            dh=quad(cp,tref,t,**options)[0];ds=quad(lambda u:cp(u)/u,tref,t,**options)[0]
            nominal=state['phases'][name]
            h=abs(nominal['sensible_enthalpy_j_mol']-dh)
            s=abs(nominal['entropy_j_mol_k']-float(source['phases'][name]['entropy_reference_j_mol_k'])-ds)
            arithmetic.append({'phase':name,'temperature_k':t,'enthalpy_quadrature_difference_j_mol':h,
                'entropy_quadrature_difference_j_mol_k':s,
                'within_budgets':h<=budget['enthalpy_quadrature_j_mol'] and s<=budget['entropy_quadrature_j_mol_k']})
    entropy_rows=[]
    for name,p in phases.items():
        for point in p['check_points']:
            t=float(point['temperature_k']);nominal=reaction.phases[name].standard(t)['entropy_j_mol_k']
            coefficients=[math.log(t/tref),t-tref,(1/tref**2-1/t**2)/2,
                          2*(1/math.sqrt(tref)-1/math.sqrt(t)),(t*t-tref*tref)/2]
            radius=half_printed_unit(source['phases'][name]['entropy_reference_j_mol_k'])+half_printed_unit(point['entropy_j_mol_k'])
            radius+=math.fsum(half_printed_unit(value)*abs(coefficient) for value,coefficient in
                zip(p['cp']['coefficients_printed'].values(),coefficients,strict=True) if value is not None)
            difference=nominal-float(point['entropy_j_mol_k'])
            entropy_rows.append({'phase':name,'temperature_k':t,'entropy_difference_j_mol_k':difference,
                'printed_combined_envelope_j_mol_k':radius,'within_printed_envelope':abs(difference)<=radius})
    derivatives=[];step=review['derivative_step_k']
    for t in review['derivative_temperatures_k']:
        center=reaction.standard(t)['reaction'];lower=reaction.standard(t-step)['reaction'];upper=reaction.standard(t+step)['reaction']
        dg=(upper['gibbs_j_mol']-lower['gibbs_j_mol'])/(2*step)
        dln=(-upper['gibbs_j_mol']/(r*(t+step))+lower['gibbs_j_mol']/(r*(t-step)))/(2*step)
        a=abs(dg+center['entropy_j_mol_k']);b=abs(dln-center['enthalpy_j_mol']/(r*t*t))
        derivatives.append({'temperature_k':t,'dG_plus_S_j_mol_k':a,'vanthoff_difference_per_k':b,
            'within_budgets':a<=budget['gibbs_derivative_j_mol_k'] and b<=budget['vanthoff_derivative_per_k']})
    roots=[];policy=settings['root']
    for p in settings['gas_partial_pressures_pa']:
        t=brentq(lambda t:reaction.affinity(t,p)['affinity_j_mol_extent'],*policy['bracket_k'],
            xtol=policy['absolute_tolerance_k'],rtol=policy['relative_tolerance'],maxiter=policy['maximum_iterations'])
        point=reaction.affinity(t,p)
        roots.append({'pressure_pa':p,'equilibrium_temperature_k':t,'affinity_residual_j_mol':point['affinity_j_mol_extent'],
            'within_budget':abs(point['affinity_j_mol_extent'])<=budget['equilibrium_affinity_j_mol']})
    scenarios=[reaction.affinity(float(t),p) for t in source['temperature_points_k'] for p in settings['gas_partial_pressures_pa']]
    result={'settings':settings,'source':source,'reference_facts':facts,'source_table_review':source_rows,
        'entropy_table_review':entropy_rows,
        'stoichiometry_review':{'atoms':composition,'element_residuals_mol_per_mol_extent':element_balance,
            'printed_molar_mass_residual_g_mol_extent':str(mass_balance),
            'balanced':all(value==0 for value in element_balance.values()) and mass_balance==0},
        'quadrature_review':arithmetic,'thermodynamic_derivatives':derivatives,'equilibrium_temperature_cases':roots,
        'scenarios':scenarios,
        'numerical_identities_met':all(x['within_budgets'] for x in arithmetic+derivatives) and all(x['within_budget'] for x in roots),
        'printed_source_envelopes_met':all(all(x['within_printed_arithmetic_envelopes'].values()) for x in source_rows) and all(x['within_printed_envelope'] for x in entropy_rows),
        'material_qualified':False,'training_eligible':False,
        'scope':'Nominal same-source pure-solid/ideal-CO2 reaction at 1 bar total. No kinetics, experimental decomposition onset or target-brick inventory.'}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({k:result[k] for k in ('numerical_identities_met','printed_source_envelopes_met','equilibrium_temperature_cases')},indent=2))


if __name__=='__main__':
    main()
