"""Independent MP source formula, temperature derivative, and cited-data comparison."""
import argparse
import json
from pathlib import Path
import sys

import mpmath as mp
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.co2_n2_diffusion import CarbonDioxideNitrogenDiffusion


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();p=json.loads(args.parameters.read_text());q=p['review'];mp.mp.dps=q['decimal_precision']
    model=CarbonDioxideNitrogenDiffusion(p); c=p['constants'];a=p['coefficients']
    r=mp.mpf(c['boltzmann_j_k'])*mp.mpf(c['avogadro_mol_inverse'])
    def source_density_product(temperature):
        t=temperature/mp.mpf(c['kelvin_scale'])
        s=mp.mpf(a['constant'])+mp.mpf(a['inverse_sixth_power'])*t**(-mp.mpf(1)/6)+mp.mpf(a['sixth_power_exponential'])*t**(mp.mpf(1)/6)*mp.exp(-mp.root(t,3))
        return mp.mpf(c['rho_diffusivity_scale_mol_m_s'])*mp.sqrt(t)/s
    records=[]
    for t in q['temperatures_k']:
        for pressure in q['pressure_pa']:
            f=lambda temp:source_density_product(temp)*r*temp/mp.mpf(pressure)
            value=f(mp.mpf(t));derivative=mp.diff(f,mp.mpf(t))
            observed=model.diffusivity_m2_s(t,pressure);observed_derivative=model.temperature_derivative_m2_s_k(t,pressure)
            error=float(abs(mp.mpf(observed)/value-1));de=float(abs(mp.mpf(observed_derivative)/derivative-1))
            records.append({'temperature_k':t,'pressure_pa':pressure,'diffusivity_m2_s':observed,'source_diffusivity_decimal':str(value),
                'temperature_derivative_m2_s_k':observed_derivative,'source_derivative_decimal':str(derivative),
                'relative_error':error,'derivative_relative_error':de,'within_budgets':error<=q['arithmetic_relative_budget'] and de<=q['derivative_relative_budget']})
    reference=json.loads((args.parameters.resolve().parent/q['vogel_source_parameters']).read_text())
    comparisons=[]
    for row in reference['vogel_rows']:
        t=mp.mpf(row['temperature_k']);value=source_density_product(t)
        measured=mp.mpf(row['first_procedure_table5_scaled_rhoD'])*mp.mpf(reference['constants']['table_rhoD_scale_mol_m_s'])
        error=float(value/measured-1)
        comparisons.append({'temperature_k':row['temperature_k'],'source_rhoD_mol_m_s_decimal':str(value),
            'vogel_first_procedure_rhoD_mol_m_s_decimal':str(measured),'signed_relative_difference':error,
            'within_declared_comparison_screen':abs(error)<=q['vogel_comparison_relative_screen_budget']})
    result={'settings':p,'formula_reviews':records,'all_arithmetic_budgets_met':all(row['within_budgets'] for row in records),
        'vogel_first_procedure_comparisons':comparisons,'all_comparison_screen_budgets_met':all(row['within_declared_comparison_screen'] for row in comparisons),
        'scope':'Arithmetic verification and viscosity-derived literature consistency. Source standard uncertainty is not a guaranteed bound; model remains dilute, equimolar-fit approximation. Existing trajectories unchanged.',
        'material_qualified':False,'training_eligible':False}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'all_arithmetic_budgets_met':result['all_arithmetic_budgets_met'],'all_comparison_screen_budgets_met':result['all_comparison_screen_budgets_met'],'comparisons':comparisons}))


if __name__=='__main__':main()
