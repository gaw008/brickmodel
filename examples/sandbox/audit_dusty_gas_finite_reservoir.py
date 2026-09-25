"""Pure Darcy-Knudsen reference with full vessel/pore N, U and entropy accounting."""
import argparse
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_maxwell_stefan_binary_column import polynomial
from audit_dusty_gas_open_pure_column import time_comparison


def audit(path):
    with path.open() as stream: rows=[json.loads(line) for line in stream]
    header,initial=rows[:2]
    p,count=header['settings'],header['cell_count']
    b=p['verification']
    r,t=header['gas_constant_j_mol_k'],p['temperature_k']
    rt=r*t
    area,width=p['geometry']['area_m2'],p['geometry']['length_m']/count
    volume=np.concatenate(([p['reservoir_volumes_m3']['left']],np.full(count,p['pore']['porosity']*area*width),[p['reservoir_volumes_m3']['right']]))
    cref=p['entropy_reference_pressure_pa']/rt
    u=p['fixed_temperature_molar_internal_energy_reference_j_mol'][0]
    dk=2/3*p['pore']['mean_pore_radius_m']*p['pore']['porosity']/p['pore']['tortuosity']*np.sqrt(8*rt/(np.pi*header['molar_masses_kg_mol'][0]))
    alpha=p['pore']['permeability_m2']*rt/header['pure_viscosities_pa_s'][0]
    distance=np.full(count+1,width); distance[[0,-1]]=width/2
    maxima=dict.fromkeys(['concentration_encoding_mol_m3','inventory_encoding_mol','energy_encoding_j','entropy_encoding_j_k',
        'pressure_encoding_pa','source_flux_mol_m2_s','source_entropy_rate_w_k','recorded_inventory_rate_mol_s',
        'recorded_energy_rate_w','recorded_entropy_rate_w_k','energy_identity_w','entropy_identity_w_k',
        'total_inventory_mol','total_energy_j','net_inventory_rate_mol_s','net_bath_heat_w'],0.)
    minima={'concentration_mol_m3':float('inf'),'face_entropy_rate_w_k':float('inf')}
    counts={'recorded':0,'dense':0}
    n0=volume*np.asarray(initial['values'])
    s0=-r*n0*np.log(np.asarray(initial['values'])/cref)
    u0=u*n0

    def reference(values,category):
        counts[category]+=1
        c=np.asarray(values)
        jump=np.diff(np.log(c/cref))
        diffusive=-dk*np.diff(c)/distance
        darcy=-alpha*np.diff(c*c)/(2*distance)
        flux=diffusive+darcy
        extended=np.concatenate(([0.],flux,[0.]))
        nr=-area*np.diff(extended)
        stream_u=area*(u+rt)*extended
        bath_u=-rt*nr
        sr=-r*(np.log(c/cref)+1)*nr
        n=volume*c; entropy=-r*n*np.log(c/cref)
        pi=-r*area*flux*jump
        errors={'energy_identity_w':np.max(np.abs(u*nr+np.diff(stream_u)-bath_u)),
            'entropy_identity_w_k':abs(float(sr.sum()-bath_u.sum()/t-pi.sum())),
            'total_inventory_mol':abs(float(np.sum(n-n0))), 'total_energy_j':abs(float(np.sum(u*n-u0))),
            'net_inventory_rate_mol_s':abs(float(nr.sum())), 'net_bath_heat_w':abs(float(bath_u.sum()))}
        for k,value in errors.items(): maxima[k]=max(maxima[k],float(value))
        minima['concentration_mol_m3']=min(minima['concentration_mol_m3'],float(c.min()))
        minima['face_entropy_rate_w_k']=min(minima['face_entropy_rate_w_k'],float(pi.min()))
        return dict(c=c,n=n,s=entropy,u=u*n,nr=nr,sr=sr,stream_u=stream_u,bath_u=bath_u,pi=pi,
            flux=flux,diffusive=diffusive,darcy=darcy,wall=-r*area*diffusive*jump,darcy_s=-r*area*darcy*jump)

    for row in [row for row in rows if row['kind'] in ('initial','accepted','sample')]+[rows[-1]['final']]:
        q=reference(row['values'],'recorded'); rates=row['rates']
        errors={'concentration_encoding_mol_m3':np.max(np.abs(q['c']-np.asarray(row['partial_concentrations_mol_m3'])[:,0])),
            'inventory_encoding_mol':np.max(np.abs(q['n']-np.asarray(row['inventories_mol'])[:,0])),
            'energy_encoding_j':np.max(np.abs(q['u']-row['internal_energy_j'])),
            'entropy_encoding_j_k':np.max(np.abs(q['s']-row['relative_ideal_entropy_j_k'])),
            'pressure_encoding_pa':max(np.max(np.abs(rt*q['c']-row['pressure_pa'])),np.max(np.abs(rt*q['c']-np.asarray(row['partial_pressures_pa'])[:,0]))),
            'source_flux_mol_m2_s':max(np.max(np.abs(q[k]-[f[field][0] for f in row['faces']])) for k,field in [
                ('flux','molar_fluxes_mol_m2_s'),('diffusive','diffusive_fluxes_mol_m2_s'),('darcy','darcy_fluxes_mol_m2_s')]),
            'source_entropy_rate_w_k':max(np.max(np.abs(q[k]-area*np.array([f[field] for f in row['faces']]))) for k,field in [
                ('pi','entropy_from_jump_w_m2_k'),('pi','entropy_from_path_w_m2_k'),('wall','entropy_wall_w_m2_k'),('darcy_s','entropy_darcy_w_m2_k')]),
            'recorded_inventory_rate_mol_s':np.max(np.abs(q['nr']-np.asarray(rates['inventory_rates_mol_s'])[:,0])),
            'recorded_energy_rate_w':max(np.max(np.abs(q['stream_u']-rates['stream_energy_fluxes_w'])),
                np.max(np.abs(q['bath_u']-rates['bath_heat_into_cells_w'])),np.max(np.abs(u*q['nr']-rates['internal_energy_rates_w']))),
            'recorded_entropy_rate_w_k':max(np.max(np.abs(q['sr']-rates['cell_entropy_rates_w_k'])),
                abs(float(-q['bath_u'].sum()/t)-rates['bath_entropy_rate_w_k']),abs(float(q['pi'].sum())-rates['all_faces_entropy_production_w_k']))}
        for k,value in errors.items(): maxima[k]=max(maxima[k],float(value))
    limits={'local_species_mol':b['local_species_budget_mol'],'cumulative_species_mol':b['local_species_budget_mol'],
        'local_cell_entropy_j_k':b['local_entropy_budget_j_k'],'cumulative_cell_entropy_j_k':b['cumulative_entropy_budget_j_k'],
        'local_combined_entropy_j_k':b['local_entropy_budget_j_k'],'cumulative_combined_entropy_j_k':b['cumulative_entropy_budget_j_k'],
        'local_energy_j':b['local_energy_budget_j'],'cumulative_energy_j':b['cumulative_energy_budget_j'],
        'closed_bath_heat_integral_j':b['cumulative_energy_budget_j']}
    reviews,finals=[],[]
    for order in b['entropy_quadrature_orders']:
        nodes,weights=leggauss(order)
        cumulative={key:np.zeros(count+2) for key in ['n','s','stream_u','bath_u']}; cumulative['pi']=0.
        previous_n,previous_s,previous_u=n0,s0,u0
        errors=dict.fromkeys(limits,0.); minimum_step=float('inf')
        for row in rows:
            if row['kind']!='accepted':continue
            dense=row['dense_output']; left,right=dense['start_time_s'],dense['end_time_s']
            integral={key:np.zeros(count+2) for key in ['n','s','stream_u','bath_u']}; integral['pi']=0.
            for node,weight in zip(nodes,weights,strict=True):
                q=reference(polynomial(row,(left+right)/2+(right-left)*node/2),'dense')
                factor=weight*(right-left)/2
                integral['n']+=factor*q['nr']; integral['s']+=factor*q['sr']
                integral['stream_u']-=factor*np.diff(q['stream_u']); integral['bath_u']+=factor*q['bath_u']
                integral['pi']+=factor*float(q['pi'].sum())
            for k,value in integral.items():cumulative[k]+=value
            n,s,energy=np.asarray(row['inventories_mol'])[:,0],np.asarray(row['relative_ideal_entropy_j_k']),np.asarray(row['internal_energy_j'])
            ds=float(np.sum(s-previous_s)-integral['bath_u'].sum()/t)
            values={'local_species_mol':np.max(np.abs(n-previous_n-integral['n'])),
                'cumulative_species_mol':np.max(np.abs(n-n0-cumulative['n'])),
                'local_cell_entropy_j_k':np.max(np.abs(s-previous_s-integral['s'])),
                'cumulative_cell_entropy_j_k':np.max(np.abs(s-s0-cumulative['s'])),
                'local_combined_entropy_j_k':abs(ds-integral['pi']),
                'cumulative_combined_entropy_j_k':abs(float(np.sum(s-s0)-cumulative['bath_u'].sum()/t)-cumulative['pi']),
                'local_energy_j':np.max(np.abs(energy-previous_u-integral['stream_u']-integral['bath_u'])),
                'cumulative_energy_j':np.max(np.abs(energy-u0-cumulative['stream_u']-cumulative['bath_u'])),
                'closed_bath_heat_integral_j':abs(float(cumulative['bath_u'].sum()))}
            for k,value in values.items():errors[k]=max(errors[k],float(value))
            minimum_step=min(minimum_step,ds)
            previous_n,previous_s,previous_u=n,s,energy
        flags={k:value<=limits[k] for k,value in errors.items()}
        flags['nonnegative_combined_step_entropy']=minimum_step>=-b['negative_step_entropy_budget_j_k']
        finals.append(cumulative)
        reviews.append({'order':order,'maximum_residuals':errors,'minimum_combined_step_entropy_j_k':minimum_step,
            'production_integral_j_k':float(cumulative['pi']),'bath_heat_into_storage_j':cumulative['bath_u'].tolist(),
            'within_budgets':flags})
    differences={k:float(np.max(np.abs(finals[0][k]-finals[-1][k]))) for k in finals[0]}
    source_limits={'concentration_encoding_mol_m3':b['source_concentration_budget_mol_m3'],
        'inventory_encoding_mol':b['global_species_budget_mol'],'energy_encoding_j':b['local_energy_budget_j'],
        'entropy_encoding_j_k':b['local_entropy_budget_j_k'],'pressure_encoding_pa':rt*b['source_concentration_budget_mol_m3'],
        'source_flux_mol_m2_s':b['source_flux_absolute_budget_mol_m2_s'],'source_entropy_rate_w_k':b['source_entropy_rate_budget_w_k'],
        'recorded_inventory_rate_mol_s':area*b['source_flux_absolute_budget_mol_m2_s'],'recorded_energy_rate_w':b['source_energy_rate_budget_w'],
        'recorded_entropy_rate_w_k':b['source_entropy_rate_budget_w_k'],'energy_identity_w':b['source_energy_rate_budget_w'],
        'entropy_identity_w_k':b['source_entropy_rate_budget_w_k'],'total_inventory_mol':b['global_species_budget_mol'],
        'total_energy_j':b['cumulative_energy_budget_j'],'net_inventory_rate_mol_s':area*b['source_flux_absolute_budget_mol_m2_s'],
        'net_bath_heat_w':b['source_energy_rate_budget_w']}
    flags={k:value<=source_limits[k] for k,value in maxima.items()}
    flags.update(completed=rows[-1]['status']=='completed',positive_concentrations=minima['concentration_mol_m3']>0,
        nonnegative_face_entropy=minima['face_entropy_rate_w_k']>=0,
        whole_trajectory_balances=all(all(row['within_budgets'].values()) for row in reviews),
        quadrature_species=differences['n']<=b['local_species_budget_mol'],
        quadrature_entropy=max(differences['s'],differences['pi'])<=b['cumulative_entropy_budget_j_k'],
        quadrature_energy=max(differences['stream_u'],differences['bath_u'])<=b['cumulative_energy_budget_j'])
    ceq=float(n0.sum()/volume.sum()); peq=rt*ceq
    seq=float(-r*n0.sum()*np.log(ceq/cref))
    final=rows[-1]['final']
    equilibrium={'pressure_pa':peq,'maximum_pressure_difference_pa':float(np.max(np.abs(np.asarray(final['pressure_pa'])-peq))),
        'entropy_increase_at_equilibrium_j_k':seq-float(s0.sum()),
        'entropy_deficit_at_final_j_k':seq-float(np.sum(final['relative_ideal_entropy_j_k']))}
    equilibrium['within_budget']=equilibrium['maximum_pressure_difference_pa']<=b['equilibrium_pressure_budget_pa'] and abs(equilibrium['entropy_deficit_at_final_j_k'])<=b['equilibrium_entropy_budget_j_k']
    return {'trajectory':str(path),'cell_count':count,'accepted_steps':rows[-1]['steps'],'counts':counts,
        'maxima':maxima,'minima':minima,'integral_reviews':reviews,'quadrature_differences':differences,
        'equilibrium':equilibrium,'within_budgets':flags,'all_trajectory_budgets_met':all(flags.values())},rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); settings=json.loads(args.parameters.read_text()); root=args.parameters.resolve().parent
    reports,records={},{}
    for name,path in settings['trajectories'].items():
        reports[name],records[name]=audit(root/path)
        print(json.dumps({'trajectory':name,'all_trajectory_budgets_met':reports[name]['all_trajectory_budgets_met']}),flush=True)
    comparison=time_comparison(records['base'],records['refined'])
    result={'settings':settings,'reports':reports,'time_comparison':comparison,
        'all_trajectory_and_time_budgets_met':all(row['all_trajectory_budgets_met'] for row in reports.values()) and comparison['within_budget'],
        'equilibrium_budgets_met':all(row['equilibrium']['within_budget'] for row in reports.values()),
        'scope':'Pure analytic face source, full finite reservoirs and pore storage balances, union-node time comparison, exact closed equilibrium. Transient spatial qualification requires a separate mesh comparison.',
        'material_qualified':False,'training_eligible':False}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({key:result[key] for key in ['all_trajectory_and_time_budgets_met','equilibrium_budgets_met','time_comparison']}),flush=True)


if __name__=='__main__':main()
