"""Trace NIST fit back to both procedures of its cited original diffusion paper."""
import argparse
import json
import math
from pathlib import Path
import sys

import mpmath as mp

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.nonpolar_gas_transport import NonpolarGasTransport


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();p=json.loads(args.parameters.read_text());c=p['constants'];fit=p['nist_fit']
    mp.mp.dps=c['decimal_precision'];r=mp.mpf(c['boltzmann_j_k'])*mp.mpf(c['avogadro_mol_inverse']);pressure=mp.mpf(c['standard_pressure_pa'])
    source=NonpolarGasTransport(json.loads((args.parameters.resolve().parent/p['approximation_parameters']).read_text()))
    records=[]
    for row in p['vogel_rows']:
        t=mp.mpf(row['temperature_k'])
        first=mp.mpf(row['first_procedure_table5_scaled_rhoD'])*mp.mpf(c['table_rhoD_scale_mol_m_s'])*r*t/pressure
        second=mp.mpf(row['second_procedure_table7_scaled_rhoD'])*mp.mpf(c['table_rhoD_scale_mol_m_s'])*r*t/pressure
        nist=mp.exp(mp.mpf(fit['A'])+mp.mpf(fit['B_k'])/t+mp.mpf(fit['C'])*mp.log(t))*mp.mpf(c['cm2_to_m2'])
        tf=float(t); ordinary=math.exp(float(fit['A'])+float(fit['B_k'])/tf+float(fit['C'])*math.log(tf))*float(c['cm2_to_m2'])
        within_fit=fit['temperature_range_k'][0]<=tf<=fit['temperature_range_k'][1]
        admitted=p['approximation_admitted_temperature_range_k'][0]<=tf<=p['approximation_admitted_temperature_range_k'][1]
        out={**row,'first_procedure_diffusivity_m2_s_decimal':str(first),'second_procedure_diffusivity_m2_s_decimal':str(second),
            'nist_fit_diffusivity_m2_s_decimal':str(nist),'within_nist_published_temperature_range':within_fit,
            'nist_minus_first_relative_percent':float(100*(nist/first-1)),
            'nist_minus_second_relative_percent':float(100*(nist/second-1)),
            'nist_fit_binary64_relative_arithmetic_error':float(abs(mp.mpf(ordinary)/nist-1)),
            'approximation_within_existing_temperature_scope':admitted}
        if admitted:
            approximate=source.binary_diffusivity_m2_s(tf,float(pressure),'CO2','N2')
            out.update(existing_approximation_m2_s=approximate,approximation_minus_first_relative_percent=float(100*(mp.mpf(approximate)/first-1)))
        records.append(out)
    selected=[row for row in records if row['within_nist_published_temperature_range']]
    result={'settings':p,'records':records,'all_arithmetic_budgets_met':all(row['nist_fit_binary64_relative_arithmetic_error']<=float(c['arithmetic_relative_budget']) for row in records),
        'nist_fit_matches_first_procedure_within_published_upper_uncertainty':all(abs(row['nist_minus_first_relative_percent'])<=fit['published_uncertainty_percent_range'][1] for row in selected),
        'source_selection_issue':'NIST fit is markedly above Table5 accepted first procedure and closer to Table7 rejected second procedure. Similarity is evidence for investigation, not proof of which data the compiler used.',
        'production_properties_changed':False,'material_qualified':False,'training_eligible':False}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'all_arithmetic_budgets_met':result['all_arithmetic_budgets_met'],'nist_fit_matches_first_procedure_within_published_upper_uncertainty':result['nist_fit_matches_first_procedure_within_published_upper_uncertainty'],'records':[{k:v for k,v in row.items() if k.endswith('percent') or k=='temperature_k'} for row in records]}))


if __name__=='__main__':main()
