"""Independent coupled phase boundaries and one-sided source calorimetry."""
import argparse
import json
from pathlib import Path

from mpmath import mp
from scipy.optimize import brentq

from carbon_calcium_setup import build
from carbon_calcium_decimal_reference import reconstruct
from carbon_gas_decimal_reference import source_thermal


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());policy=json.loads((root/settings['model_parameters']).read_text())
    model,_=build(root,policy);mp.dps=settings['decimal_digits'];budget=settings['budgets'];records=[]
    for case in settings['boundaries']:
        inventory=next(i for i in policy['inventories'] if i['name']==case['inventory_name'])
        inputs=[inventory[name] for name in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
        ca,ct,ot,nn=inputs;kind=case['kind'];r=mp.mpf(model.r)
        def endpoint(t):
            if kind=='graphite_exhaustion':
                state=model.at_temperature(t,*inputs);a=state['amounts_mol']['calcite']
                gas=model.carbon.at_temperature(t,ct-a,ot-ca-2*a,nn)
                return ct-a-gas['graphite_branch_required_carbon_mol']
            a=ca if kind=='calcite_onset' else 0.;gas=model.carbon.at_temperature(t,ct-a,ot-ca-2*a,nn)
            return model.phases['lime'].standard(t)['gibbs_j_mol']+gas['chemical_potentials_j_mol']['CO2']-model.phases['calcite'].standard(t)['gibbs_j_mol']
        boundary=brentq(endpoint,*case['temperature_bracket_k'],xtol=settings['temperature_root_absolute_tolerance_k'],
            rtol=settings['temperature_root_relative_tolerance'],maxiter=settings['maximum_root_iterations'])
        candidate=model.at_temperature(boundary,*inputs);mca,mct,mot,mnn=map(mp.mpf,inputs);names=['CO','CO2','O2']
        graphite_endpoint=kind=='graphite_exhaustion';variable_a=graphite_endpoint and case['left_phases'][0]=='coexistence'
        graphite_present=case['left_phases'][1]=='graphite_present'
        fixed_a=mca if kind=='calcite_onset' or (graphite_endpoint and case['left_phases'][0]=='calcite') else mp.mpf(0)
        def decode(*coordinates):
            t=coordinates[0];gas=dict(zip(names,map(mp.exp,coordinates[1:4])));gas['N2']=mnn;ng=mp.fsum(gas.values())
            a=mca*coordinates[4] if variable_a else fixed_a
            carbon=mp.mpf(0) if graphite_endpoint or not graphite_present else mct-a-gas['CO']-gas['CO2']
            thermal=source_thermal(model,t);mu={name:thermal[name][2]+r*t*mp.log(value/ng) for name,value in gas.items()}
            mu.update({name:thermal[name][2] for name in ['calcite','lime','C']})
            return {'calcite':a,'lime':mca-a,'C':carbon,**gas},mu,thermal
        def equations(*coordinates):
            t=coordinates[0];n,mu,_=decode(*coordinates);oxygen=(3*n['calcite']+n['lime']+n['CO']+2*n['CO2']+2*n['O2'])/mot-1
            carbon=(n['calcite']+n['C']+n['CO']+n['CO2'])/mct-1
            first=(mu['CO']-mu['C']-mu['O2']/2)/(r*t);second=(mu['CO2']-mu['C']-mu['O2'])/(r*t)
            calcination=(mu['lime']+mu['CO2']-mu['calcite'])/(r*t)
            if graphite_endpoint:
                result=[carbon,oxygen,first,second]
                if variable_a:result.append(calcination)
            elif graphite_present:result=[oxygen,first,second,calcination]
            else:result=[carbon,oxygen,(mu['CO2']-mu['CO']-mu['O2']/2)/(r*t),calcination]
            return tuple(result)
        initial=[mp.mpf(boundary),*(mp.log(mp.mpf(candidate['amounts_mol'][name])) for name in names)]
        if variable_a:initial.append(mp.mpf(candidate['calcite_fraction']))
        solution=mp.findroot(equations,tuple(initial),tol=mp.mpf(settings['root_tolerance']),maxsteps=settings['maximum_root_iterations'])
        target=solution[0];amounts,mu,thermal=decode(*solution);ng=mp.fsum(amounts[name] for name in ['CO','CO2','O2','N2'])
        h=mp.fsum(value*thermal[name][0] for name,value in amounts.items())
        s=mp.fsum(amounts[name]*thermal[name][1] for name in ['calcite','lime','C'])+mp.fsum(amounts[name]*(thermal[name][1]-r*mp.log(amounts[name]/ng)) for name in ['CO','CO2','O2','N2'])
        key={'calcite_onset':'lime','calcite_exhaustion':'calcite','graphite_exhaustion':'C'}[kind]
        errors={'boundary_temperature_k':float(abs(mp.mpf(boundary)-target)),'source_enthalpy_j':float(abs(mp.mpf(candidate['enthalpy_j'])-h)),
            'source_entropy_j_k':float(abs(mp.mpf(candidate['entropy_j_k'])-s)),
            'phase_endpoint_mol':float(abs(mp.mpf(candidate['amounts_mol'][key])-amounts[key]))}
        sides=[]
        for offset in settings['one_sided_offsets_k']:
            for sign,expected in [(-1,case['left_phases']),(1,case['right_phases'])]:
                at=target+sign*mp.mpf(offset);seed=model.at_temperature(float(at),*inputs);current=reconstruct(model,at,inventory,seed,settings)
                step=mp.mpf(offset)*mp.mpf(settings['one_sided_derivative_step_fraction'])
                left=reconstruct(model,at-step,inventory,seed,settings);right=reconstruct(model,at+step,inventory,seed,settings)
                cp=(right['enthalpy']-left['enthalpy'])/(2*step);hp=current['enthalpy']+cp*(target-at);sp=current['entropy']+cp/at*(target-at)
                he=float(abs(hp-h));se=float(abs(sp-s));ce=float(abs(mp.mpf(seed['equilibrium_cp_j_k'])-cp))
                source_mu=current['mu'];a=current['amounts'];cal=source_mu['lime']+source_mu['CO2']-source_mu['calcite'];constraints=all(n>=0 for n in a.values())
                if expected[0]=='calcite':constraints=constraints and cal>=0
                if expected[0]=='lime':constraints=constraints and cal<=0
                if expected[1]=='graphite_exhausted':constraints=constraints and source_mu['CO']-source_mu['C']-source_mu['O2']/2<=0 and source_mu['CO2']-source_mu['C']-source_mu['O2']<=0
                flags={'expected_phases':[seed['calcium_phase'],seed['carbon_phase']]==expected,'reference_phase_constraints':bool(constraints),
                    'enthalpy_continuity':he<=budget['projected_enthalpy_continuity_j'],'entropy_continuity':se<=budget['projected_entropy_continuity_j_k'],
                    'one_sided_cp':ce<=budget['one_sided_cp_j_k']}
                sides.append({'direction':sign,'offset_k':offset,'phases':expected,'source_cp_j_k':str(cp),'candidate_cp_j_k':seed['equilibrium_cp_j_k'],
                    'source_cp_error_j_k':ce,'projected_enthalpy_error_j':he,'projected_entropy_error_j_k':se,'within_budgets':flags})
        flags={key:value<=budget[key] for key,value in errors.items()}
        record={'case':case,'inventory':inventory,'candidate_temperature_k':boundary,'reference_temperature_k':str(target),
            'reference_amounts_mol':{name:str(value) for name,value in amounts.items()},'reference_enthalpy_j':str(h),'reference_entropy_j_k':str(s),
            'boundary_errors':errors,'boundary_within_budgets':flags,'one_sided_records':sides,
            'all_requested_boundary_budgets_met':all(flags.values()) and all(all(row['within_budgets'].values()) for row in sides)}
        records.append(record);print(json.dumps({'name':case['name'],'temperature_k':boundary,'all_requested_boundary_budgets_met':record['all_requested_boundary_budgets_met']}),flush=True)
    result={'settings':settings,'records':records,'all_requested_phase_boundary_budgets_met':all(r['all_requested_boundary_budgets_met'] for r in records),
        'material_qualified':False,'training_eligible':False,'scope':settings['scope']}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
