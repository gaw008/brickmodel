"""Independent fixed-volume phase boundaries and one-sided source identities."""
import argparse
import json
from pathlib import Path

from mpmath import mp
from scipy.optimize import brentq

from carbon_calcium_pressure_setup import build
from carbon_calcium_rigid_decimal_reference import reconstruct
from carbon_gas_decimal_reference import source_thermal


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent
    settings=json.loads(args.parameters.read_text())
    rigid=json.loads((root/settings['model_parameters']).read_text())
    policy=json.loads((root/rigid['pressure_parameters']).read_text())
    model,_,_=build(root,policy)
    mp.dps=settings['decimal_digits'];budget=settings['budgets'];records=[]
    volume=rigid['virtual_volume_m3'];numerics=rigid['numerics']
    for case in settings['boundaries']:
        inventory=next(i for i in policy['inventories'] if i['name']==case['inventory_name'])
        inputs=[inventory[k] for k in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
        ca,ct,ot,nn=inputs;kind=case['kind'];r,p0=mp.mpf(model.r),mp.mpf(model.p0)
        def endpoint(t):
            state=model.at_temperature_volume(t,volume,*inputs,numerics)
            n,mu=state['amounts_mol'],state['chemical_potentials_j_mol']
            # Complementarity gives a continuous signed indicator at a phase
            # boundary: missing-phase affinity on one side, amount on the other.
            if kind=='graphite_exhaustion':
                return n['C']/ct*model.r*t if state['carbon_phase']=='graphite_present' else mu['CO']-mu['C']-mu['O2']/2
            if kind=='calcite_onset':
                return state['calcination_gibbs_j_mol'] if state['calcium_phase']=='calcite' else -n['lime']/ca*model.r*t
            return state['calcination_gibbs_j_mol'] if state['calcium_phase']=='lime' else n['calcite']/ca*model.r*t
        boundary=brentq(endpoint,*case['temperature_bracket_k'],xtol=settings['temperature_root_absolute_tolerance_k'],
            rtol=settings['temperature_root_relative_tolerance'],maxiter=settings['maximum_root_iterations'])
        candidate=model.at_temperature_volume(boundary,volume,*inputs,numerics)
        mca,mct,mot,mnn=map(mp.mpf,inputs);names=['CO','CO2','O2']
        volumes={name:mp.mpf(v) for name,v in model.volumes.items()}
        graphite_endpoint=kind=='graphite_exhaustion'
        variable_a=graphite_endpoint and case['left_phases'][0]=='coexistence'
        graphite_present=case['left_phases'][1]=='graphite_present'
        fixed_a=mca if kind=='calcite_onset' or (graphite_endpoint and case['left_phases'][0]=='calcite') else mp.mpf(0)
        def decode(*coordinates):
            t=coordinates[0];p=mp.exp(coordinates[-1]);gas=dict(zip(names,map(mp.exp,coordinates[1:4]),strict=True));gas['N2']=mnn
            ng=mp.fsum(gas.values());a=mca*coordinates[4] if variable_a else fixed_a
            carbon=mp.mpf(0) if graphite_endpoint or not graphite_present else mct-a-gas['CO']-gas['CO2']
            n={'calcite':a,'lime':mca-a,'C':carbon,**gas};thermal=source_thermal(model,t)
            mu={name:thermal[name][2]+r*t*mp.log(p/p0*value/ng) for name,value in gas.items()}
            mu.update({name:thermal[name][2]+(p-p0)*v for name,v in volumes.items()})
            v=mp.fsum(n[name]*v for name,v in volumes.items())+ng*r*t/p
            return n,mu,thermal,p,v
        def equations(*coordinates):
            t=coordinates[0];n,mu,_,_,v=decode(*coordinates)
            oxygen=(3*n['calcite']+n['lime']+n['CO']+2*n['CO2']+2*n['O2'])/mot-1
            carbon=(n['calcite']+n['C']+n['CO']+n['CO2'])/mct-1
            first=(mu['CO']-mu['C']-mu['O2']/2)/(r*t);second=(mu['CO2']-mu['C']-mu['O2'])/(r*t)
            calcination=(mu['lime']+mu['CO2']-mu['calcite'])/(r*t)
            if graphite_endpoint:
                result=[carbon,oxygen,first,second]
                if variable_a:result.append(calcination)
            elif graphite_present:result=[oxygen,first,second,calcination]
            else:result=[carbon,oxygen,(mu['CO2']-mu['CO']-mu['O2']/2)/(r*t),calcination]
            result.append(v/mp.mpf(volume)-1)
            return tuple(result)
        initial=[mp.mpf(boundary),*(mp.log(mp.mpf(candidate['amounts_mol'][name])) for name in names)]
        if variable_a:initial.append(mp.mpf(candidate['calcite_fraction']))
        initial.append(mp.log(mp.mpf(candidate['pressure_pa'])))
        solution=mp.findroot(equations,tuple(initial),tol=mp.mpf(settings['root_tolerance']),maxsteps=settings['maximum_root_iterations'])
        target=solution[0];n,mu,thermal,p,v=decode(*solution);ng=mp.fsum(n[name] for name in ['CO','CO2','O2','N2'])
        # Internal energy is recomposed directly from solid h0-p0*v and gas h0-RT.
        u=mp.fsum(n[name]*(thermal[name][0]-p0*volumes[name]) for name in volumes)
        u+=mp.fsum(n[name]*(thermal[name][0]-r*target) for name in ['CO','CO2','O2','N2'])
        s=mp.fsum(value*thermal[name][1] for name,value in n.items())
        s-=r*mp.fsum(n[name]*mp.log(p/p0*n[name]/ng) for name in ['CO','CO2','O2','N2'])
        key={'calcite_onset':'lime','calcite_exhaustion':'calcite','graphite_exhaustion':'C'}[kind]
        errors={'boundary_temperature_k':float(abs(mp.mpf(boundary)-target)),
            'boundary_pressure_pa':float(abs(mp.mpf(candidate['pressure_pa'])-p)),
            'source_internal_energy_j':float(abs(mp.mpf(candidate['internal_energy_j'])-u)),
            'source_entropy_j_k':float(abs(mp.mpf(candidate['entropy_j_k'])-s)),
            'volume_m3':float(abs(v-mp.mpf(volume))),
            'phase_endpoint_mol':float(abs(mp.mpf(candidate['amounts_mol'][key])-n[key]))}
        sides=[]
        for offset in settings['one_sided_offsets_k']:
            for sign,expected in [(-1,case['left_phases']),(1,case['right_phases'])]:
                at=target+sign*mp.mpf(offset);seed=model.at_temperature_volume(float(at),volume,*inputs,numerics)
                current=reconstruct(model,at,volume,inventory,seed,settings)
                step=mp.mpf(offset)*mp.mpf(settings['one_sided_derivative_step_fraction'])
                left=reconstruct(model,at-step,volume,inventory,seed,settings)
                right=reconstruct(model,at+step,volume,inventory,seed,settings)
                cv=(right['internal_energy']-left['internal_energy'])/(2*step)
                dp=(right['pressure']-left['pressure'])/(2*step)
                ue=float(abs(current['internal_energy']+cv*(target-at)-u))
                se=float(abs(current['entropy']+cv/at*(target-at)-s))
                pe=float(abs(current['pressure']+dp*(target-at)-p))
                ce=float(abs(mp.mpf(seed['equilibrium_cv_j_k'])-cv))
                sm=current['mu'];a=current['amounts'];ac=sm['lime']+sm['CO2']-sm['calcite']
                constraints=all(value>=0 for value in a.values())
                if expected[0]=='calcite':constraints=constraints and ac>=0
                if expected[0]=='lime':constraints=constraints and ac<=0
                if expected[1]=='graphite_exhausted':constraints=constraints and sm['CO']-sm['C']-sm['O2']/2<=0 and sm['CO2']-sm['C']-sm['O2']<=0
                flags={'expected_phases':[seed['calcium_phase'],seed['carbon_phase']]==expected,'phase_constraints':bool(constraints),
                    'internal_energy_continuity':ue<=budget['projected_internal_energy_continuity_j'],
                    'entropy_continuity':se<=budget['projected_entropy_continuity_j_k'],
                    'pressure_continuity':pe<=budget['projected_pressure_continuity_pa'],
                    'one_sided_cv':ce<=budget['one_sided_cv_j_k'],'positive_cv':bool(cv>0)}
                sides.append({'direction':sign,'offset_k':offset,'phases':expected,'source_cv_j_k':str(cv),
                    'source_cv_error_j_k':ce,'projected_internal_energy_error_j':ue,'projected_entropy_error_j_k':se,
                    'projected_pressure_error_pa':pe,'within_budgets':flags})
        flags={key:value<=budget[key] for key,value in errors.items()}
        record={'case':case,'inventory':inventory,'candidate_temperature_k':boundary,
            'reference_temperature_k':str(target),'reference_pressure_pa':str(p),
            'reference_internal_energy_j':str(u),'reference_entropy_j_k':str(s),
            'reference_amounts_mol':{name:str(value) for name,value in n.items()},'boundary_errors':errors,
            'boundary_within_budgets':flags,'one_sided_records':sides,
            'all_requested_boundary_budgets_met':all(flags.values()) and all(all(row['within_budgets'].values()) for row in sides)}
        records.append(record);print(json.dumps({'name':case['name'],'temperature_k':boundary,'pressure_pa':float(p),
            'all_requested_boundary_budgets_met':record['all_requested_boundary_budgets_met']}),flush=True)
    result={'settings':settings,'records':records,'all_requested_phase_boundary_budgets_met':all(r['all_requested_boundary_budgets_met'] for r in records),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
