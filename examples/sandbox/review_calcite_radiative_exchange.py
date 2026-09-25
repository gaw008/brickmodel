"""Rational heat-flux arithmetic and NIST constant representation review."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path

from calcite_affinity_setup import build
from sludge_sandbox.equilibrium_calcite_calorimeter import EquilibriumCalciteCalorimeter


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    config=json.loads((root/settings['model_parameters']).read_text());affinity=json.loads((root/config['affinity_parameters']).read_text())
    reaction,_,_=build(root,affinity);model=EquilibriumCalciteCalorimeter(reaction,config,affinity['root'])
    p=config['radiation'];source=p['source'];records=[]
    derived=2*math.pi**5*source['boltzmann_j_k']**4/(15*source['planck_j_s']**3*source['light_speed_m_s']**2)
    sigma_difference=abs(derived-p['stefan_boltzmann_w_m2_k4'])
    for t,wall in settings['cases_k']:
        tf,wf=Fraction(t),Fraction(wall)
        rational=Fraction(config['heat_conductance_w_k'])*(wf-tf)+Fraction(p['area_m2'])*Fraction(p['emissivity'])*Fraction(p['stefan_boltzmann_w_m2_k4'])*(wf**4-tf**4)
        actual=model.heat_rate(t,wall);h=settings['temperature_derivative_step_k']
        derivative=(model.heat_rate(t+h,wall)-model.heat_rate(t-h,wall))/(2*h)
        derivative_difference=abs(derivative-model.heat_temperature_derivative(t))
        difference=abs(actual-float(rational));production=actual*(1/t-1/wall)
        records.append({'temperature_k':t,'wall_temperature_k':wall,'heat_in_w':actual,'rational_reference_w':float(rational),
            'absolute_heat_difference_w':difference,'derivative_difference_w_k':derivative_difference,'combined_entropy_production_w_k':production,
            'within_budgets':difference<=settings['heat_absolute_budget_w'] and derivative_difference<=settings['heat_derivative_budget_w_k'] and
                production>=-settings['entropy_production_allowance_w_k']})
    result={'settings':settings,'source':source,'derived_sigma_w_m2_k4':derived,'sigma_representation_difference_w_m2_k4':sigma_difference,
        'records':records,'all_requested_numerical_budgets_met':all(x['within_budgets'] for x in records) and sigma_difference<=settings['sigma_representation_absolute_budget_w_m2_k4'],
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
