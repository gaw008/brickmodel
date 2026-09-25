"""Fixed printed kinetics under explicit unresolved source-unit hypotheses."""
import argparse
import json
import math
from pathlib import Path

import mpmath as mp

from calcite_affinity_setup import build


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();p=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    mp.mp.dps=p['numerics']['decimal_precision'];c=p['constants'];source=p['printed_parameters']
    r=mp.mpf(c['gas_constant_j_mol_k']);ea=mp.mpf(source['activation_energy_kj_mol'])*mp.mpf(c['joules_per_kilojoule'])
    a,n,peq0,b=map(mp.mpf,[source['preexponential_value'],source['pressure_exponent'],source['equilibrium_pressure_coefficient'],source['equilibrium_temperature_coefficient_k']])
    diameter=mp.mpf(p['material']['mean_diameter_micrometres'])
    usgs,_,_=build(root,json.loads((root/p['usgs_affinity_parameters']).read_text()))
    cases=[];arithmetic=[];anchors=[]
    for tc in p['temperature_cases_c']:
        t=mp.mpf(tc)+mp.mpf(c['celsius_offset_k']);peq=peq0*mp.exp(-b/t)
        hg=usgs.standard(float(t))['reaction']['gibbs_j_mol']
        usgs_peq=usgs.standard_pressure_pa*math.exp(-hg/(usgs.gas_constant_j_mol_k*float(t)))
        for pressure in p['co2_partial_pressure_cases_bar']:
            pressure=mp.mpf(pressure);drive=1-pressure/peq
            prefactor=a*mp.exp(-ea/(r*t))*drive**n
            interpretations=[]
            for hypothesis in p['unit_hypotheses']:
                dp=diameter*mp.mpf(hypothesis['diameter_scale_from_micrometres']);tau=dp/prefactor
                tf,rf,eaf,af,nf,pf,df=map(float,[t,r,ea,a,n,pressure,dp])
                peq_float=float(peq0)*math.exp(-float(b)/tf)
                tau_float=df/(af*math.exp(-eaf/(rf*tf))*(1-pf/peq_float)**nf)
                err=float(abs(mp.mpf(tau_float)/tau-1));ode_error=0.
                for fraction in p['conversion_fractions_for_arithmetic']:
                    fraction=mp.mpf(fraction);at=tau*fraction
                    trajectory=lambda time:1-(1-time/tau)**3
                    alpha=trajectory(at)
                    explicit=3*prefactor/dp*(1-alpha)**(mp.mpf(2)/3)
                    numerical=mp.diff(trajectory,at)
                    ode_error=max(ode_error,float(abs(numerical/explicit-1)))
                interpretations.append({'hypothesis':hypothesis['name'],'completion_time_s':float(tau),'initial_conversion_rate_per_s':float(3/tau),
                    'arithmetic_relative_error':err,'analytic_ode_relative_error':ode_error})
                arithmetic.append(err<=p['numerics']['arithmetic_relative_budget'] and ode_error<=p['numerics']['derivative_relative_budget'])
                for anchor in p['prose_completion_anchors']:
                    if anchor['temperature_c']==tc and mp.mpf(anchor['co2_pressure_bar'])==pressure:
                        anchors.append({'anchor':anchor,'hypothesis':hypothesis['name'],'computed_completion_s':float(tau),
                            'ratio_to_approximate_prose_time':float(tau/anchor['approximately_complete_s']),
                            'comparison_status':'descriptive_only_no_reading_or_measurement_error_interval'})
            cases.append({'temperature_c':tc,'temperature_k':float(t),'pressure_bar':float(pressure),
                'empirical_equilibrium_bar_hypothesis':float(peq),'usgs_equilibrium_bar':usgs_peq/float(c['pa_per_bar']),
                'empirical_relative_difference_from_usgs':float(peq)*float(c['pa_per_bar'])/usgs_peq-1,
                'source_pressure_drive':float(drive),'usgs_forward_affinity_j_mol':-hg-usgs.gas_constant_j_mol_k*float(t)*math.log(float(pressure)*float(c['pa_per_bar'])/usgs.standard_pressure_pa),
                'unit_interpretations':interpretations})
    result={'settings':p,'cases':cases,'prose_anchor_comparisons':anchors,'all_arithmetic_budgets_met':all(arithmetic),
        'all_nominal_source_cases_below_empirical_and_usgs_equilibrium':all(row['source_pressure_drive']>0 and row['usgs_forward_affinity_j_mol']>0 for row in cases),
        'rate_law_admitted':False,'unresolved':['PrintedA0 length/time units and Eq5 pressure units need confirmation or accessible original supporting record',
            'Figures not visually reviewed or digitized in this access attempt; prose anchors have no uncertainty',
            'Same fitted first-cycle curves are not independent validation; no parameter covariance',
            'Noninteger pressure exponent is not a reversible law forp>peq; alpha polynomial must not continue beyondtau',
            'High-steam natural limestone parameters cannot transfer directly to clay/sludge brick'],
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_arithmetic_budgets_met':result['all_arithmetic_budgets_met'],'rate_law_admitted':False,'anchors':anchors},indent=2))


if __name__=='__main__':main()
