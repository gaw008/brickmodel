"""Reference-only source sensitivity, distinct from total predictive uncertainty."""
import argparse
from dataclasses import replace
from itertools import product
import json
import math
from pathlib import Path

from scipy.optimize import brentq,linprog

from calcite_rigid_setup import build_rigid
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    config=json.loads((root/settings['model_parameters']).read_text());comparison=json.loads((root/settings['frozen_comparison']).read_text())
    reaction,nitrogen,affinity,source,facts,nsource,volume=build_rigid(root,config);model=RigidCalciteMixture(reaction,nitrogen,volume,config,config['cell'])
    refs={s['id']:s['reference_298'] for s in facts['species']};cp=comparison['settings']['comparison'];conditions=comparison['settings']['conditions']
    total_pressure=conditions['total_pressure_atm']*cp['pressure_pa_per_atm'];r=reaction.gas_constant_j_mol_k
    widths={phase:{'enthalpy_j_mol':float(refs[phase][settings['reference_field_names']['enthalpy']])*affinity['joules_per_kilojoule'],
                   'entropy_j_mol_k':float(refs[phase][settings['reference_field_names']['entropy']]),'source_locator':refs[phase]['locator']}
            for phase in settings['enthalpy_sensitivity_phases']}
    def potential(t,p,dh,ds):return reaction.standard(t)['reaction']['gibbs_j_mol']-(total_pressure-model.p0)*model.dv+r*t*math.log(p/model.p0)+dh-t*ds
    groups=[]
    for group in settings['case_groups']:
        hphases=settings['enthalpy_sensitivity_phases'];sphases=settings['entropy_sensitivity_phases'] if group=='enthalpy_and_reported_nonzero_entropy' else []
        scenarios=[]
        for signs in product(settings['factor_levels'],repeat=len(hphases)+len(sphases)):
            shifts={k:{'enthalpy_j_mol':0.,'entropy_j_mol_k':0.} for k in reaction.phases}
            for sign,phase in zip(signs[:len(hphases)],hphases,strict=True):shifts[phase]['enthalpy_j_mol']=sign*widths[phase]['enthalpy_j_mol']
            for sign,phase in zip(signs[len(hphases):],sphases,strict=True):shifts[phase]['entropy_j_mol_k']=sign*widths[phase]['entropy_j_mol_k']
            dh=sum(reaction.stoichiometry[k]*v['enthalpy_j_mol'] for k,v in shifts.items());ds=sum(reaction.stoichiometry[k]*v['entropy_j_mol_k'] for k,v in shifts.items())
            shifted=replace(reaction,phases={k:replace(v,reference_enthalpy_j_mol=v.reference_enthalpy_j_mol+shifts[k]['enthalpy_j_mol'],
                reference_entropy_j_mol_k=v.reference_entropy_j_mol_k+shifts[k]['entropy_j_mol_k']) for k,v in reaction.phases.items()})
            temperatures=[];max_recomposition=0.
            for row in comparison['records']:
                p=row['pressure_pa'];t=brentq(lambda t:potential(t,p,dh,ds),*cp['evaluation_temperature_interval_k'],xtol=cp['root_temperature_absolute_k'],rtol=cp['root_temperature_relative'],maxiter=cp['root_iterations'])
                temperatures.append(t);direct=shifted.standard(t)['reaction']['gibbs_j_mol']-(total_pressure-model.p0)*model.dv+r*t*math.log(p/model.p0)
                max_recomposition=max(max_recomposition,abs(direct))
            scenarios.append({'phase_shifts':shifts,'reaction_reference_enthalpy_shift_j_mol':dh,'reaction_reference_entropy_shift_j_mol_k':ds,
                'equilibrium_temperatures_k':temperatures,'direct_shifted_source_root_residual_j_mol':max_recomposition})
        summaries=[]
        for i,row in enumerate(comparison['records']):
            values=[s['equilibrium_temperatures_k'][i] for s in scenarios];bounds=[min(values),max(values)];lo,hi=row['onset_pixel_reading_interval_k']
            summaries.append({'pressure_atm':row['pressure_atm'],'nominal_equilibrium_k':row['equilibrium_temperature_k'],
                'reference_scenario_temperature_range_k':bounds,'experimental_onset_pixel_interval_k':[lo,hi],
                'scenario_range_overlaps_reading':max(lo,bounds[0])<=min(hi,bounds[1]),
                'gibbs_offset_required_at_central_onset_j_mol':-potential(row['digitized_onset_temperature_k'],row['pressure_pa'],0.,0.)})
        hwidth=sum(abs(reaction.stoichiometry[k])*widths[k]['enthalpy_j_mol'] for k in hphases)
        swidth=sum(abs(reaction.stoichiometry[k])*widths[k]['entropy_j_mol_k'] for k in sphases)
        a=[];b=[]
        for row in comparison['records']:
            lo,hi=row['onset_pixel_reading_interval_k'];p=row['pressure_pa']
            a.extend([[-1.,lo],[1.,-hi]]);b.extend([potential(lo,p,0.,0.),-potential(hi,p,0.,0.)])
        lp=settings['common_reference_feasibility'];result=linprog([0.,0.],A_ub=a,b_ub=b,bounds=[(-hwidth,hwidth),(-swidth,swidth)],
            method=lp['method'],options={k:lp[k] for k in ('primal_feasibility_tolerance','dual_feasibility_tolerance')})
        lower_lines=[(-hwidth,0.,'enthalpy lower bound')];upper_lines=[(hwidth,0.,'enthalpy upper bound')]
        for i,row in enumerate(comparison['records']):
            lo,hi=row['onset_pixel_reading_interval_k'];p=row['pressure_pa']
            lower_lines.append((-potential(lo,p,0.,0.),lo,f'point {i+1} lower reading'))
            upper_lines.append((-potential(hi,p,0.,0.),hi,f'point {i+1} upper reading'))
        slo,shi=-swidth,swidth;lower_reason=upper_reason='source entropy box';constant_conflicts=[]
        for lower in lower_lines:
            for upper in upper_lines:
                coefficient=lower[1]-upper[1];rhs=upper[0]-lower[0];reason=[lower[2],upper[2]]
                if coefficient>0 and rhs/coefficient<shi:shi=rhs/coefficient;upper_reason=reason
                elif coefficient<0 and rhs/coefficient>slo:slo=rhs/coefficient;lower_reason=reason
                elif coefficient==0 and rhs<0:constant_conflicts.append(reason)
        elimination={'entropy_shift_lower_j_mol_k':slo,'entropy_shift_upper_j_mol_k':shi,'lower_bound_reason':lower_reason,
            'upper_bound_reason':upper_reason,'constant_conflicts':constant_conflicts,'feasible':slo<=shi and not constant_conflicts}
        groups.append({'name':group,'scenarios':scenarios,'pointwise_ranges':summaries,
            'independent_linear_elimination':elimination,
            'common_reference_feasibility':{'status':int(result.status),'message':result.message,'feasible':bool(result.success),
                'witness_dh_ds':result.x.tolist() if result.success else None,'adopted_as_material_parameters':False}})
    result={'settings':settings,'source_reference_widths':widths,'groups':groups,'nominal_model_changed':False,
        'formal_material_pass':None,'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps([{'group':g['name'],'scenarios':len(g['scenarios']),'pointwise_overlaps':sum(x['scenario_range_overlaps_reading'] for x in g['pointwise_ranges']),
        'common_offset_feasible':g['common_reference_feasibility']['feasible']} for g in groups]))


if __name__=='__main__':main()
