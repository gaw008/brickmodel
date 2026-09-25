"""Independent high-precision inversion and native-time review of finite effusion."""
import argparse
from bisect import bisect_left
import json
import math
from pathlib import Path
import time

import mpmath as mp
import numpy as np
from numpy.polynomial.legendre import leggauss


def polynomial(dense, at):
    value = np.array(dense['differences'][0], dtype=float)
    product = 1.
    for shift, denominator, difference in zip(dense['shifts_s'], dense['denominators_s'], dense['differences'][1:], strict=True):
        product *= (at-shift)/denominator
        value += product*np.array(difference)
    return value


def mp_number(value):
    return mp.mpf(str(value))


class Source:
    def __init__(self, header, policy):
        self.header, self.policy = header, policy
        self.settings = header['settings']
        facts, nitrogen = header['reference_facts'], header['nitrogen_source']
        reference = facts['reference_state']
        self.r = mp_number(reference['gas_constant_j_mol_k'])
        self.p0 = mp_number(reference['pressure_pa'])
        co2 = next(row for row in facts['species'] if row['id']=='carbon_dioxide')
        self.coefficients = [[mp_number(co2['cp']['coefficients_nominal'][f'A{i}']) for i in range(1,6)],
                             [mp_number('0' if value is None else value) for value in nitrogen['cp_coefficient_strings']]]
        self.t0 = [mp_number(co2['reference_298']['temperature_k']),mp_number(nitrogen['reference_temperature_k'])]
        self.h0 = [mp_number(co2['reference_298']['hf_kj_mol'])*mp_number(header['affinity_parameters']['joules_per_kilojoule']),mp_number(nitrogen['reference_enthalpy_j_mol'])]
        self.s0 = [mp_number(header['source']['phases']['carbon_dioxide']['entropy_reference_j_mol_k']),mp_number(nitrogen['reference_entropy_j_mol_k'])]
        self.masses = [mp_number(header['aperture']['molar_masses_kg_mol'][name]) for name in ['co2','nitrogen']]
        self.area = mp_number(header['aperture']['area_m2'])
        self.volumes = [mp_number(c['volume_m3']) for c in self.settings['cells']]
        self.bracket = tuple(map(mp_number,self.settings['numerics']['temperature_bracket_k']))
        self.hoffset = [self.h0[i]-self.h_primitive(self.coefficients[i],self.t0[i]) for i in range(2)]
        self.soffset = [self.s0[i]-self.s_primitive(self.coefficients[i],self.t0[i]) for i in range(2)]
        self.normal = mp.quad(lambda q:q*mp.exp(-q*q),[0,mp.inf])
        self.normal_energy = mp.quad(lambda q:q**3*mp.exp(-q*q),[0,mp.inf])
        self.transverse = mp.quad(lambda q:mp.exp(-q*q),[-mp.inf,mp.inf])
        self.transverse_energy = mp.quad(lambda q:q*q*mp.exp(-q*q),[-mp.inf,mp.inf])
        self.kinetic_ratio = self.normal_energy/self.normal+2*self.transverse_energy/self.transverse
        self.cache = {}
        self.inverse_maximum = mp.mpf(0)

    @staticmethod
    def h_primitive(c,t):
        a,b,z,d,e = c
        return a*t+b*t*t/2-z/t+2*d*mp.sqrt(t)+e*t**3/3

    @staticmethod
    def s_primitive(c,t):
        a,b,z,d,e = c
        return a*mp.log(t)+b*t-z/(2*t*t)-2*d/mp.sqrt(t)+e*t*t/2

    def state(self,n,t,v):
        h = [self.hoffset[i]+self.h_primitive(self.coefficients[i],t) for i in range(2)]
        pressures = [amount*self.r*t/v for amount in n]
        entropy = [self.soffset[i]+self.s_primitive(self.coefficients[i],t)-self.r*mp.log(pressures[i]/self.p0) for i in range(2)]
        energy = mp.fsum(n[i]*(h[i]-self.r*t) for i in range(2))
        return {'temperature':t,'pressure':mp.fsum(pressures),'partial':pressures,'h':h,
                'mu':[h[i]-t*entropy[i] for i in range(2)],'U':energy,'S':mp.fsum(n[i]*entropy[i] for i in range(2))}

    def inverse(self,n,u,v):
        coefficients = [mp.fsum(n[i]*self.coefficients[i][j] for i in range(2)) for j in range(5)]
        offset = mp.fsum(n[i]*self.hoffset[i] for i in range(2))-u
        nr = mp.fsum(n)*self.r
        residual = lambda t:offset+self.h_primitive(coefficients,t)-nr*t
        t = mp.findroot(residual,self.bracket,solver=self.policy['root_solver'],tol=mp_number(self.policy['root_tolerance']),maxsteps=self.policy['root_maximum_steps'])
        state = self.state(n,t,v)
        self.inverse_maximum = max(self.inverse_maximum,abs(state['U']-u))
        return state

    def at(self, values):
        key = tuple(float(value) for value in values[:6])
        if key not in self.cache:
            y = [mp.mpf(value) for value in key]
            states = [self.inverse(y[3*s:3*s+2],y[3*s+2],self.volumes[s]) for s in range(2)]
            flux, energy, entropy = [],mp.mpf(0),[mp.mpf(0),mp.mpf(0)]
            for i in range(2):
                gamma,e = [],[]
                for state in states:
                    t = state['temperature']
                    gamma.append(self.area*state['partial'][i]/(self.r*t)*mp.sqrt(2*self.r*t/self.masses[i])*self.normal/self.transverse)
                    e.append(state['h'][i]-mp.mpf('2.5')*self.r*t+self.r*t*self.kinetic_ratio)
                j = gamma[0]-gamma[1];q = gamma[0]*e[0]-gamma[1]*e[1]
                flux.append(j);energy += q
                entropy[0] += (-q+states[0]['mu'][i]*j)/states[0]['temperature']
                entropy[1] += (q-states[1]['mu'][i]*j)/states[1]['temperature']
            current = np.array(list(key)+[float(s['S']) for s in states])
            rates = np.array(list(map(float,[-flux[0],-flux[1],-energy,flux[0],flux[1],energy]+entropy+flux+[energy,mp.fsum(entropy)])))
            info = {'temperature':np.array([float(s['temperature']) for s in states]),
                    'pressure':np.array([float(s['pressure']) for s in states]),
                    'entropy':np.array([float(s['S']) for s in states]),
                    'flux':np.array(list(map(float,flux+[energy]))),
                    'production':float(mp.fsum(entropy))}
            self.cache[key] = current,rates,info
        current,rates,info = self.cache[key]
        return np.concatenate((current,values[6:])),rates,info

    def initial_from_source(self):
        result = []
        for config,v in zip(self.settings['cells'],self.volumes,strict=True):
            t,p,x = [mp_number(config[k]) for k in ['temperature_k','pressure_pa','co2_fraction']]
            total = p*v/(self.r*t);n = [x*total,(1-x)*total]
            result.extend(n+[self.state(n,t,v)['U']])
        return np.array(list(map(float,result)))

    def equilibrium(self,initial):
        n = [mp.mpf(float(initial[i]))+mp.mpf(float(initial[3+i])) for i in range(2)]
        u = mp.mpf(float(initial[2]))+mp.mpf(float(initial[5]))
        state = self.inverse(n,u,mp.fsum(self.volumes))
        amounts = [[float(amount*v/mp.fsum(self.volumes)) for amount in n] for v in self.volumes]
        return {'temperature_k':float(state['temperature']),'pressure_pa':float(state['pressure']),
                'entropy_j_k':float(state['S']),'amounts_mol':amounts}


def read(path):
    with path.open() as stream: rows = [json.loads(line) for line in stream]
    return rows[0], rows[1], [r for r in rows if r['kind']=='accepted'], [r for r in rows if r['kind'] in ['initial','accepted','sample']], rows[-1]


def audit(path,settings):
    header,initial,accepted,recorded,terminal = read(path)
    source = Source(header,settings['numerics']);budget = header['settings']['verification']; extra = settings['verification']
    face_budget,area = header['face_settings']['verification'],float(source.area)
    origin,_,_ = source.at(initial['values']);equilibrium = source.equilibrium(initial['values'])
    expected = source.initial_from_source();initial_error = np.abs(np.array(initial['values'][:6])-expected)
    maximum = {k:0. for k in ['species_ledger_mol','energy_ledger_j','entropy_ledger_j_k','entropy_above_equilibrium_j_k','source_temperature_k','source_pressure_pa','source_entropy_j_k','face_species_mol_s','face_energy_w','face_entropy_w_k']}
    minima = {'species_mol':math.inf,'temperature_k':math.inf,'production_w_k':math.inf};max_temperature = -math.inf
    counts = {'recorded':0,'dense':0};times=set()
    def inspect(at,values,row=None):
        nonlocal max_temperature
        current,rates,info = source.at(values); times.add(float(at))
        n=np.array(values[:6]).reshape(2,3);v0=origin[:6].reshape(2,3)
        residual=n-v0+np.array([values[6:9],-np.array(values[6:9])])
        maximum['species_ledger_mol']=max(maximum['species_ledger_mol'],float(np.max(np.abs(residual[:,:2]))),float(np.max(np.abs((n-v0).sum(axis=0)[:2]))))
        maximum['energy_ledger_j']=max(maximum['energy_ledger_j'],float(np.max(np.abs(residual[:,2]))),float(abs((n-v0).sum(axis=0)[2])))
        maximum['entropy_ledger_j_k']=max(maximum['entropy_ledger_j_k'],float(abs(sum(current[6:8]-origin[6:8])-values[-1])))
        maximum['entropy_above_equilibrium_j_k']=max(maximum['entropy_above_equilibrium_j_k'],float(current[6:8].sum()-equilibrium['entropy_j_k']))
        minima['species_mol']=min(minima['species_mol'],float(n[:,:2].min()));minima['temperature_k']=min(minima['temperature_k'],float(info['temperature'].min()))
        minima['production_w_k']=min(minima['production_w_k'],info['production']);max_temperature=max(max_temperature,float(info['temperature'].max()))
        if row is not None:
            counts['recorded']+=1
            maximum['source_temperature_k']=max(maximum['source_temperature_k'],float(np.max(np.abs(info['temperature']-[s['temperature_k'] for s in row['states']]))))
            maximum['source_pressure_pa']=max(maximum['source_pressure_pa'],float(np.max(np.abs(info['pressure']-[s['pressure_pa'] for s in row['states']]))))
            maximum['source_entropy_j_k']=max(maximum['source_entropy_j_k'],float(np.max(np.abs(info['entropy']-[s['entropy_j_k'] for s in row['states']]))))
            old=row['face'];delta=info['flux']-[old['carbon_flow_mol_s'],old['nitrogen_flow_mol_s'],old['energy_flow_w']]
            maximum['face_species_mol_s']=max(maximum['face_species_mol_s'],float(np.max(np.abs(delta[:2]))))
            maximum['face_energy_w']=max(maximum['face_energy_w'],float(abs(delta[2])))
            maximum['face_entropy_w_k']=max(maximum['face_entropy_w_k'],float(abs(info['production']-old['entropy_production_w_k'])))
        else:counts['dense']+=1
        return current,rates,info
    for row in recorded: inspect(row['time_s'],row['values'],row)
    limits=np.array([budget['species_mol']]*2+[budget['energy_j']]+[budget['species_mol']]*2+[budget['energy_j']]+[budget['entropy_j_k']]*2+[budget['species_mol']]*2+[budget['energy_j'],budget['entropy_j_k']])
    reviews=[];prefixes=[]
    for order in settings['numerics']['quadrature_orders']:
        nodes,weights=leggauss(order);total=np.zeros(12);local=np.zeros(12);cumulative=np.zeros(12);prefix=[];before=origin;minimum_step=math.inf
        for index,row in enumerate(accepted):
            dense=row['dense_output'];left,right=dense['start_time_s'],dense['end_time_s'];interval=np.zeros(12)
            for node,weight in zip(nodes,weights,strict=True):
                at=(left+right)/2+(right-left)*node/2
                _,rates,_=inspect(at,polynomial(dense,at));interval+=(right-left)*weight/2*rates
            current,_,_=source.at(row['values']);total+=interval;prefix.append(total.copy())
            local=np.maximum(local,np.abs(current-before-interval));cumulative=np.maximum(cumulative,np.abs(current-origin-total))
            minimum_step=min(minimum_step,float(sum(current[6:8]-before[6:8])));before=current
            if (index+1)%settings['numerics']['progress_every_steps']==0:
                print(json.dumps({'trajectory':path.name,'order':order,'steps':index+1}),flush=True)
        flags={'local':bool(np.all(local<=limits)),'cumulative':bool(np.all(cumulative<=limits)),'nonnegative_entropy_step':minimum_step>=-budget['negative_step_entropy_j_k']}
        reviews.append({'order':order,'maximum_local_residuals':local.tolist(),'maximum_cumulative_residuals':cumulative.tolist(),'minimum_entropy_step_j_k':minimum_step,'within_budgets':flags});prefixes.append(np.array(prefix))
    quadrature=np.max(np.abs(prefixes[-1]-prefixes[0]),axis=0)
    final,_,final_info=source.at(terminal['final']['values'])
    differences={'temperature_k':float(np.max(np.abs(final_info['temperature']-equilibrium['temperature_k']))),'pressure_pa':float(np.max(np.abs(final_info['pressure']-equilibrium['pressure_pa']))),'species_mol':float(np.max(np.abs(final[:6].reshape(2,3)[:,:2]-equilibrium['amounts_mol'])))}
    flags={k:maximum[k]<=extra[k] for k in ['source_temperature_k','source_pressure_pa','source_entropy_j_k']}
    flags.update({'initial_species':float(initial_error.reshape(2,3)[:,:2].max())<=extra['source_initial_species_mol'],
        'initial_energy':float(initial_error[[2,5]].max())<=extra['source_initial_energy_j'],
        'initial_temperature':float(np.max(np.abs(source.at(initial['values'])[2]['temperature']-[c['temperature_k'] for c in header['settings']['cells']])))<=extra['source_initial_temperature_k'],
        'species_ledger':maximum['species_ledger_mol']<=budget['species_mol'],'energy_ledger':maximum['energy_ledger_j']<=budget['energy_j'],
        'entropy_ledger':maximum['entropy_ledger_j_k']<=budget['entropy_j_k'],'entropy_upper_bound':maximum['entropy_above_equilibrium_j_k']<=budget['entropy_j_k'],
        'source_inverse_energy':float(source.inverse_maximum)<=extra['source_energy_inverse_j'],
        'face_species':maximum['face_species_mol_s']/area<=face_budget['species_flux_absolute_mol_m2_s'],
        'face_energy':maximum['face_energy_w']/area<=face_budget['energy_flux_absolute_w_m2'],
        'face_entropy':maximum['face_entropy_w_k']/area<=face_budget['entropy_flux_absolute_w_m2_k'],
        'positive_species':minima['species_mol']>0,'source_temperature_domain':float(source.bracket[0])<=minima['temperature_k'] and max_temperature<=float(source.bracket[1]),
        'nonnegative_production':minima['production_w_k']/area>=-face_budget['negative_entropy_flux_allowance_w_m2_k'],
        'local_cumulative_integrals':all(all(r['within_budgets'].values()) for r in reviews),'quadrature':bool(np.all(quadrature<=limits)),
        'final_equilibrium':all(differences[k]<=budget['equilibrium_'+k] for k in differences),
        'completed':terminal['kind']=='summary' and terminal['status']=='completed' and terminal['time_s']==header['settings']['time_interval_s'][1]})
    report={'trajectory':str(path),'counts':counts,'maximum_residuals':maximum,'minima':minima,'maximum_temperature_k':max_temperature,
        'source_inverse_maximum_energy_residual_j':float(source.inverse_maximum),'initial_C_N_U_differences':initial_error.tolist(),
        'independent_equilibrium':equilibrium,'final_equilibrium_differences':differences,'balance_component_order':['CL','NL','UL','CR','NR','UR','SL','SR','integral_JC','integral_JN','integral_E','integral_Pi'],
        'balance_budgets':limits.tolist(),'integral_reviews':reviews,'quadrature_maximum_prefix_difference':quadrature.tolist(),
        'within_budgets':flags,'all_requested_budgets_met':all(flags.values())}
    return report,(source,initial,accepted,times)


def compare(first,second):
    references=[first,second];ends=[[r['time_s'] for r in item[2]] for item in references]
    times=sorted(first[3]|second[3]);maximum={'temperature_k':0.,'pressure_pa':0.,'species_mol':0.}
    for at in times:
        evaluated=[]
        for (source,initial,accepted,_),end in zip(references,ends,strict=True):
            values=initial['values'] if at==initial['time_s'] else polynomial(accepted[bisect_left(end,at)]['dense_output'],at)
            current,_,info=source.at(values);evaluated.append((current,info))
        maximum['temperature_k']=max(maximum['temperature_k'],float(np.max(np.abs(evaluated[0][1]['temperature']-evaluated[1][1]['temperature']))))
        maximum['pressure_pa']=max(maximum['pressure_pa'],float(np.max(np.abs(evaluated[0][1]['pressure']-evaluated[1][1]['pressure']))))
        maximum['species_mol']=max(maximum['species_mol'],float(np.max(np.abs((evaluated[0][0][:6]-evaluated[1][0][:6]).reshape(2,3)[:,:2]))))
    budget=first[0].settings['verification'];flags={k:value<=budget['time_'+k] for k,value in maximum.items()}
    return {'times_compared':len(times),'maximum_differences':maximum,'within_budgets':flags,'all_requested_budgets_met':all(flags.values()),'scope':'Both accepted,2and4Gauss and observed nodes; independent source inventory inverse at each time, native BDF polynomials; no continuous-time supremum.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    mp.mp.dps=settings['numerics']['decimal_precision'];started=time.monotonic();reviews={};records={}
    for name,relative in settings['trajectories'].items():
        reviews[name],records[name]=audit(root/relative,settings)
        print(json.dumps({'trajectory':name,'all_requested_budgets_met':reviews[name]['all_requested_budgets_met'],'elapsed_s':time.monotonic()-started}),flush=True)
    comparison=compare(records['base'],records['refined'])
    result={'settings':settings,'trajectory_reviews':reviews,'time_comparison':comparison,'elapsed_s':time.monotonic()-started,
        'all_requested_budgets_met':all(r['all_requested_budgets_met'] for r in reviews.values()) and comparison['all_requested_budgets_met'],
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_budgets_met':result['all_requested_budgets_met'],'elapsed_s':result['elapsed_s']}),flush=True)


if __name__=='__main__':main()
