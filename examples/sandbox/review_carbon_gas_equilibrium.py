"""Independent element-potential reconstruction of the C/O mixture at60digits."""
import argparse
import json
from pathlib import Path

from mpmath import mp

from carbon_gas_setup import build


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    policy=json.loads((root/settings['model_parameters']).read_text());model,source=build(root,policy);mp.dps=settings['decimal_digits'];budget=settings['budgets'];records=[]
    r=mp.mpf(model.r);p0=mp.mpf(model.p0)
    for t_binary in policy['temperature_points_k']:
        t=mp.mpf(t_binary);thermal={}
        for name,phase in model.phases.items():
            a,b,c,d,e=map(mp.mpf,phase.coefficients);t0=mp.mpf(phase.reference_temperature_k)
            def cp(value):return a+b*value+c/value**2+d/mp.sqrt(value)+e*value**2
            h=mp.mpf(phase.reference_enthalpy_j_mol)+mp.quad(cp,[t0,t])
            s=mp.mpf(phase.reference_entropy_j_mol_k)+mp.quad(lambda value:cp(value)/value,[t0,t])
            thermal[name]=(h,s,h-t*s)
        for inventory in policy['inventories']:
            cb,ob,nb=[inventory[k] for k in ['carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
            candidate=model.at_temperature(t_binary,cb,ob,nb);ct,ot,nn=map(mp.mpf,(cb,ob,nb));names=['CO','CO2','O2']
            def decode(*logarithms):
                gases=dict(zip(names,map(mp.exp,logarithms)));gases['N2']=nn;ng=mp.fsum(gases.values())
                mu={name:thermal[name][2]+r*t*mp.log(value/ng) for name,value in gases.items()};mu['C']=thermal['C'][2]
                return gases,mu
            def equations(*logarithms):
                gas,mu=decode(*logarithms);oxygen=(gas['CO']+2*gas['CO2']+2*gas['O2'])/ot-1
                if candidate['phase']=='graphite_present':
                    return ((mu['CO']-mu['C']-mu['O2']/2)/(r*t),(mu['CO2']-mu['C']-mu['O2'])/(r*t),oxygen)
                return ((gas['CO']+gas['CO2'])/ct-1,oxygen,(mu['CO2']-mu['CO']-mu['O2']/2)/(r*t))
            initial=tuple(mp.log(mp.mpf(candidate['amounts_mol'][name])) for name in names)
            solution=mp.findroot(equations,initial,tol=mp.mpf(settings['root_tolerance']),maxsteps=settings['maximum_root_iterations'])
            gas,mu=decode(*solution);carbon=ct-gas['CO']-gas['CO2'] if candidate['phase']=='graphite_present' else mp.mpf(0)
            amounts={'C':carbon,**gas};ng=mp.fsum(gas.values());enthalpy=mp.fsum(value*thermal[name][0] for name,value in amounts.items())
            entropy=carbon*thermal['C'][1]+mp.fsum(value*(thermal[name][1]-r*mp.log(value/ng)) for name,value in gas.items())
            gibbs=enthalpy-t*entropy;nominal=candidate['amounts_mol'];element_errors={k:abs(candidate['element_amounts_mol'][k]-v) for k,v in [('C',cb),('O',ob),('N',2*nb)]}
            absolute={name:float(abs(mp.mpf(nominal[name])-value)) for name,value in amounts.items()}
            relative={name:float(abs(mp.mpf(nominal[name])/value-1)) for name,value in gas.items()}
            heat_error=float(abs(mp.mpf(candidate['enthalpy_j'])-enthalpy));entropy_error=float(abs(mp.mpf(candidate['entropy_j_k'])-entropy));g_error=float(abs(mp.mpf(candidate['gibbs_j'])-gibbs))
            affinity=candidate['reaction_gibbs_j_mol_extent'];pressure_error=abs(sum(candidate['partial_pressures_pa'].values())-model.p0)
            if candidate['phase']=='graphite_present':
                phase_condition=abs(affinity['C_halfO2_to_CO'])<=budget['reaction_gibbs_j_mol'] and abs(affinity['C_O2_to_CO2'])<=budget['reaction_gibbs_j_mol'] and carbon>=0
            else:
                phase_condition=affinity['C_halfO2_to_CO']<=budget['reaction_gibbs_j_mol'] and affinity['C_O2_to_CO2']<=budget['reaction_gibbs_j_mol']
            flags={'elements':max(element_errors.values())<=budget['element_mol'],'pressure':pressure_error<=budget['pressure_pa'],
                'gas_reaction_equilibrium':abs(affinity['CO_halfO2_to_CO2'])<=budget['reaction_gibbs_j_mol'],'solid_KKT':bool(phase_condition),
                'positive_gases':all(v>0 for v in gas.values()),'source_enthalpy':heat_error<=budget['source_enthalpy_j'],
                'source_entropy':entropy_error<=budget['source_entropy_j_k'],'gibbs':g_error<=budget['gibbs_j'],
                'amounts':max(absolute.values())<=budget['amount_absolute_mol'],'trace_relative':max(relative.values())<=budget['trace_amount_relative']}
            records.append({'inventory':inventory,'candidate':candidate,'reference_amounts_mol':{name:str(value) for name,value in amounts.items()},
                'absolute_amount_errors_mol':absolute,'positive_gas_relative_errors':relative,'element_errors_mol':element_errors,'pressure_error_pa':pressure_error,
                'source_enthalpy_error_j':heat_error,'source_entropy_error_j_k':entropy_error,'gibbs_error_j':g_error,'within_budgets':flags})
    result={'settings':settings,'model_parameters':policy,'source_file':policy['source_file'],'records':records,
        'all_requested_static_budgets_met':all(all(r['within_budgets'].values()) for r in records),'material_qualified':False,'training_eligible':False,
        'scope':'Independent source quadrature and simultaneous log-mole elemental/chemical-potential equations for selected states. Model decoder and scalar/quadratic roots are not reused in the reference. No rate law or time trajectory.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'records':len(records),'all_requested_static_budgets_met':result['all_requested_static_budgets_met']}))


if __name__=='__main__':main()
