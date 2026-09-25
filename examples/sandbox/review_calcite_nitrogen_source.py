"""Compare source nitrogen polynomials against printed data and independent integrals."""
import argparse
from decimal import Decimal
import json
import math
from pathlib import Path

from scipy.integrate import quad

from calcite_closed_setup import nitrogen_from_record


def half_unit(value):
    return 0. if value is None else float(Decimal(10)**Decimal(value).as_tuple().exponent/2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    source=json.loads((root/settings['source_file']).read_text());phase=nitrogen_from_record(source)
    t0=phase.reference_temperature_k;uncertainty=[half_unit(x) for x in source['cp_coefficient_strings']]
    records=[]
    for row in source['source_table']:
        t=float(row['temperature_k']);state=phase.standard(t)
        cp_basis=[1.,t,1/t**2,1/math.sqrt(t),t**2]
        h_basis=[t-t0,(t*t-t0*t0)/2,1/t0-1/t,2*(math.sqrt(t)-math.sqrt(t0)),(t**3-t0**3)/3]
        s_basis=[math.log(t/t0),t-t0,(1/t0**2-1/t**2)/2,2*(1/math.sqrt(t0)-1/math.sqrt(t)),(t*t-t0*t0)/2]
        comparisons={}
        for key,value,basis,reference_half in (
            ('cp_j_mol_k',state['cp_j_mol_k'],cp_basis,0.),
            ('entropy_j_mol_k',state['entropy_j_mol_k'],s_basis,half_unit(source['reference_entropy_j_mol_k'])),
            ('sensible_enthalpy_over_t_j_mol_k',state['sensible_enthalpy_j_mol']/t,[v/t for v in h_basis],0.)):
            envelope=half_unit(row[key])+reference_half+sum(abs(a)*b for a,b in zip(basis,uncertainty,strict=True))
            error=abs(value-float(row[key]))
            comparisons[key]={'calculated':value,'printed':row[key],'difference':error,'printing_arithmetic_envelope':envelope,'within_printing_envelope':error<=envelope}
        options={'epsabs':settings['quadrature_absolute_tolerance'],'epsrel':settings['quadrature_relative_tolerance'],
            'limit':settings['quadrature_maximum_subintervals']}
        cp=lambda x:sum(a*b for a,b in zip(phase.coefficients,[1,x,1/x**2,1/math.sqrt(x),x*x],strict=True))
        h=quad(cp,t0,t,**options)[0];s=quad(lambda x:cp(x)/x,t0,t,**options)[0]
        dh=abs(h-state['sensible_enthalpy_j_mol']);ds=abs(s-(state['entropy_j_mol_k']-phase.reference_entropy_j_mol_k))
        records.append({'temperature_k':t,'source_comparisons':comparisons,'quadrature_enthalpy_difference_j_mol':dh,
            'quadrature_entropy_difference_j_mol_k':ds,'within_budgets':all(x['within_printing_envelope'] for x in comparisons.values())
                and dh<=settings['quadrature_enthalpy_budget_j_mol'] and ds<=settings['quadrature_entropy_budget_j_mol_k']})
    result={'settings':settings,'source':source,'records':records,'all_requested_numerical_budgets_met':all(r['within_budgets'] for r in records),
        'material_qualified':False,'training_eligible':False,'scope':'Same-source nominal standard nitrogen; printing envelopes are not physical uncertainty.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],'records':len(records)}))


if __name__=='__main__':main()
