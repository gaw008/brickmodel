"""Separate pure-property and Wilke mixing differences against source intercepts."""
import argparse
import json
from pathlib import Path

import mpmath as mp

from run_co2_n2_reference_dusty_gas import reference_properties
from sludge_sandbox.wilke_gas_mixture import wilke_viscosity_pa_s


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();p=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    column=json.loads((root/p['property_parameters']).read_text());q=p['review'];mp.mp.dps=q['decimal_precision']
    unit=mp.mpf(p['micro_pa_s_to_pa_s']);records=[]
    for row in p['rows']:
        properties=reference_properties(dict(column,temperature_k=float(row['temperature_k'])),root)
        masses=list(map(mp.mpf,properties['molar_masses_kg_mol']))
        pure_sources={'reference_correlations':properties['pure_viscosities_pa_s'],
            'same_table_pure_intercepts':[float(mp.mpf(row['pure_CO2_micro_pa_s'])*unit),float(mp.mpf(row['pure_N2_micro_pa_s'])*unit)]}
        for index,nitrogen in enumerate(p['nitrogen_mole_fractions']):
            fractions=[1-mp.mpf(nitrogen),mp.mpf(nitrogen)]
            target=mp.mpf(row['mixture_micro_pa_s'][index])*unit
            budget=target*mp.mpf(q['experimental_intercept_relative_screen'])+mp.mpf(q['printed_rounding_half_unit_micro_pa_s'])*unit
            for label,values in pure_sources.items():
                mu=list(map(mp.mpf,values))
                weights=[[((1+mp.sqrt(mu[i]/mu[j])*(masses[j]/masses[i])**mp.mpf('.25'))**2)
                    /mp.sqrt(8*(1+masses[i]/masses[j])) for j in range(2)] for i in range(2)]
                source=mp.fsum(fractions[i]*mu[i]/mp.fsum(fractions[j]*weights[i][j] for j in range(2)) for i in range(2))
                actual=wilke_viscosity_pa_s(list(map(float,fractions)),values,list(map(float,masses)))['viscosity_pa_s']
                error=float(abs(mp.mpf(actual)/source-1))
                records.append({'temperature_k':row['temperature_k'],'nitrogen_mole_fraction':nitrogen,'pure_viscosity_input':label,
                    'source_intercept_pa_s_decimal':str(target),'mixture_pa_s':actual,'independent_wilke_decimal':str(source),
                    'arithmetic_relative_error':error,'arithmetic_within_budget':error<=q['arithmetic_relative_budget'],
                    'signed_relative_source_difference':float(source/target-1),'source_screen_budget_pa_s':float(budget),
                    'source_screen_within_budget':abs(source-target)<=budget})
    result={'settings':p,'records':records,'all_arithmetic_budgets_met':all(r['arithmetic_within_budget'] for r in records),
        'source_screen_results':{label:{'rows':len(group),'passing':sum(r['source_screen_within_budget'] for r in group),
            'maximum_absolute_relative_difference':max(abs(r['signed_relative_source_difference']) for r in group)}
            for label in pure_sources for group in [[r for r in records if r['pure_viscosity_input']==label]]},
        'scope':'Source zero-density intercept screen at253.17-473.30K. No refitting, no600K mixture measurement claim, no pressure-dependent validation.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_arithmetic_budgets_met':result['all_arithmetic_budgets_met'],'source_screen_results':result['source_screen_results']}))


if __name__=='__main__':main()
