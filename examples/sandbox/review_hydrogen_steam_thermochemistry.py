"""USGS hydrogen/steam Cp, Cv, source tables, formation and C/H/O reactions."""
import argparse
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import sys

import mpmath as mp

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_reaction_affinity import RecordedThermalPhase
from sludge_sandbox.recorded_gas_reactions import standard_reaction
from review_carbon_gas_thermochemistry import cp_certificate


def half_printed(value):
    return mp.mpf(10)**Decimal(value).as_tuple().exponent/2


def h_basis(t,t0):
    return [t-t0,(t*t-t0*t0)/2,1/t0-1/t,2*(mp.sqrt(t)-mp.sqrt(t0)),(t**3-t0**3)/3]


def s_basis(t,t0):
    return [mp.log(t/t0),t-t0,(1/t0**2-1/t**2)/2,2*(1/mp.sqrt(t0)-1/mp.sqrt(t)),(t*t-t0*t0)/2]


def thermal(data,t,t0):
    coefficients=list(map(mp.mpf,data['cp_coefficient_strings']))
    a,b,c,d,e=coefficients
    cp=lambda v:a+b*v+c/v**2+d/mp.sqrt(v)+e*v*v
    h=mp.mpf(data['reference_enthalpy_j_mol'])+mp.quad(cp,[t0,t])
    s=mp.mpf(data['reference_entropy_j_mol_k'])+mp.quad(lambda v:cp(v)/v,[t0,t])
    return {'cp_j_mol_k':cp(t),'enthalpy_j_mol':h,'entropy_j_mol_k':s,'gibbs_j_mol':h-t*s}


def rounding(data,t,t0):
    errors=[mp.mpf(0) if value=='0' else half_printed(value) for value in data['cp_coefficient_strings']]
    basis=[1,t,1/t**2,1/mp.sqrt(t),t*t]
    h=mp.fsum(error*abs(value) for error,value in zip(errors,h_basis(t,t0),strict=True))
    s=half_printed(data['reference_entropy_j_mol_k'])+mp.fsum(error*abs(value) for error,value in zip(errors,s_basis(t,t0),strict=True))
    return {'cp_j_mol_k':mp.fsum(error*abs(value) for error,value in zip(errors,basis,strict=True)),
            'sensible_enthalpy_j_mol':h,'entropy_j_mol_k':s}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();p=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    source=json.loads((root/p['source_file']).read_text());old=json.loads((root/p['carbon_oxygen_source_file']).read_text())
    mp.mp.dps=p['decimal_digits'];t0=mp.mpf(source['reference_temperature_k']);r=mp.mpf(source['gas_constant_j_mol_k'])
    data={**old['phases'],**source['phases']}
    phases={name:RecordedThermalPhase(tuple(map(float,item['cp_coefficient_strings'])),float(t0),float(item['reference_enthalpy_j_mol']),float(item['reference_entropy_j_mol_k']),tuple(p['selected_temperature_domain_k'])) for name,item in data.items()}
    records={}
    for name,item in source['phases'].items():
        points=[];maximum={k:0. for k in p['numerical_budgets']}
        for temperature in p['review_temperatures_k']:
            t=mp.mpf(str(temperature));reference=thermal(item,t,t0);state=phases[name].standard(temperature)
            errors={k:float(abs(mp.mpf(state[k])-reference[k])) for k in maximum}
            maximum={k:max(v,errors[k]) for k,v in maximum.items()}
            points.append({'temperature_k':temperature,'state':state,'independent_integral_errors':errors})
        coefficients=[Fraction(float(value)) for value in item['cp_coefficient_strings']]
        coefficients[0]-=Fraction(float(r));certificate=cp_certificate(coefficients,p['cp_certificate'])
        certificate['quantity']='Cv=Cp-R';certificate['method']=certificate['method'].replace('Cp','Cv')
        comparisons=[]
        for row in item['source_table']:
            t=mp.mpf(row['temperature_k']);state=thermal(item,t,t0);error=rounding(item,t,t0)
            values={k:state[k] for k in ['cp_j_mol_k','entropy_j_mol_k']}
            values['sensible_enthalpy_over_t_j_mol_k']=(state['enthalpy_j_mol']-mp.mpf(item['reference_enthalpy_j_mol']))/t
            error['sensible_enthalpy_over_t_j_mol_k']=error['sensible_enthalpy_j_mol']/t
            differences={k:values[k]-mp.mpf(row[k]) for k in values}
            envelopes={k:error[k]+half_printed(row[k]) for k in values}
            comparisons.append({'printed':row,'nominal_minus_printed':{k:float(v) for k,v in differences.items()},
                'coefficient_reference_and_table_rounding_enclosures':{k:float(v) for k,v in envelopes.items()},
                'within_printed_table_half_unit_only':{k:bool(abs(v)<=half_printed(row[k])) for k,v in differences.items()},
                'within_complete_arithmetic_enclosure':{k:bool(abs(v)<=envelopes[k]+p['source_arithmetic_enclosure_allowance']) for k,v in differences.items()}})
        flags={k:v<=p['numerical_budgets'][k] for k,v in maximum.items()};flags['whole_domain_positive_cv']=certificate['whole_cover_positive']
        records[name]={'points':points,'maximum_integral_errors':maximum,'cv_certificate':certificate,'within_numerical_budgets':flags,'table_comparisons':comparisons,
            'all_table_half_units_met':all(all(v['within_printed_table_half_unit_only'].values()) for v in comparisons),
            'all_complete_arithmetic_enclosures_met':all(all(v['within_complete_arithmetic_enclosure'].values()) for v in comparisons)}
    reactions={}
    for name,nu in p['reactions'].items():
        points=[];maximum={k:0. for k in p['reaction_budgets']};balance={element:sum(Fraction(value)*p['atoms'][species].get(element,0) for species,value in nu.items()) for element in ['C','H','O','N']}
        for temperature in p['review_temperatures_k']:
            t=mp.mpf(str(temperature));runtime=standard_reaction(phases,nu,temperature,float(r))
            refstates={species:thermal(data[species],t,t0) for species in nu}
            reference={k:mp.fsum(mp.mpf(coefficient)*refstates[species][k] for species,coefficient in nu.items()) for k in ['enthalpy_j_mol','entropy_j_mol_k','gibbs_j_mol']}
            reference['log_equilibrium']=-reference['gibbs_j_mol']/(r*t)
            gibbs=lambda v:mp.fsum(mp.mpf(coefficient)*thermal(data[species],v,t0)['gibbs_j_mol'] for species,coefficient in nu.items())
            reference['gibbs_temperature_derivative_j_mol_k']=mp.diff(gibbs,t)
            reference['vant_hoff_derivative_per_k']=mp.diff(lambda v:-gibbs(v)/(r*v),t)
            errors={k:float(abs(mp.mpf(runtime[k])-reference[k])) for k in maximum};maximum={k:max(v,errors[k]) for k,v in maximum.items()}
            points.append({'temperature_k':temperature,'state':runtime,'independent_errors':errors})
        flags={k:v<=p['reaction_budgets'][k] for k,v in maximum.items()};flags['exact_element_balance']=all(value==0 for value in balance.values())
        reactions[name]={'stoichiometry':nu,'atom_balance':{k:str(v) for k,v in balance.items()},'points':points,'maximum_errors':maximum,'within_budgets':flags}
    formation=[];nu=p['reactions']['hydrogen_oxidation']
    for row in source['phases']['H2O']['source_table']:
        t=mp.mpf(row['temperature_k']);states={name:thermal(data[name],t,t0) for name in nu};errors={name:rounding(data[name],t,t0) for name in nu}
        dh=mp.fsum(coefficient*states[name]['enthalpy_j_mol'] for name,coefficient in nu.items())
        ds=mp.fsum(coefficient*states[name]['entropy_j_mol_k'] for name,coefficient in nu.items());dg=dh-t*ds
        eh=half_printed(source['phases']['H2O']['reference_enthalpy_printed_kj_mol'])*p['joules_per_kilojoule']+mp.fsum(abs(coefficient)*errors[name]['sensible_enthalpy_j_mol'] for name,coefficient in nu.items())
        es=mp.fsum(abs(coefficient)*errors[name]['entropy_j_mol_k'] for name,coefficient in nu.items());eg=eh+t*es
        values={'formation_enthalpy_kj_mol':dh/p['joules_per_kilojoule'],'formation_gibbs_kj_mol':dg/p['joules_per_kilojoule'],'formation_log10_k':-dg/(r*t*mp.log(10))}
        envelopes={'formation_enthalpy_kj_mol':eh/p['joules_per_kilojoule'],'formation_gibbs_kj_mol':eg/p['joules_per_kilojoule'],'formation_log10_k':eg/(r*t*mp.log(10))}
        differences={k:values[k]-mp.mpf(row[k]) for k in values};total={k:envelopes[k]+half_printed(row[k]) for k in values}
        formation.append({'temperature_k':float(t),'nominal_values':{k:float(v) for k,v in values.items()},'nominal_minus_printed':{k:float(v) for k,v in differences.items()},'rounding_enclosures':{k:float(v) for k,v in total.items()},'within_arithmetic_enclosures':{k:bool(abs(v)<=total[k]+p['source_arithmetic_enclosure_allowance']) for k,v in differences.items()}})
    result={'settings':p,'source':source,'records':records,'reactions':reactions,'steam_formation_table':formation,
        'all_numerical_relations_met':all(all(v['within_numerical_budgets'].values()) for v in records.values()) and all(all(v['within_budgets'].values()) for v in reactions.values()),
        'all_source_arithmetic_enclosures_met':all(v['all_complete_arithmetic_enclosures_met'] for v in records.values()) and all(all(v['within_arithmetic_enclosures'].values()) for v in formation),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k.startswith('all_')}),flush=True)


if __name__=='__main__':main()
