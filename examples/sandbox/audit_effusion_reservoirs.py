"""Analytic finite-reservoir solution and full source N/U/S/thermostat ledgers."""
import argparse
from bisect import bisect_left
import json
from pathlib import Path

import mpmath as mp
import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_maxwell_stefan_binary_column import polynomial
from review_molecular_effusion import mp_state


class Reference:
    def __init__(self, header):
        self.p = header['settings']
        source, pack = header['source_settings'], header['thermochemistry']
        self.names = source['species_order']; self.count = len(self.names)
        self.r = mp.mpf(str(pack['gas_constant']['value_j_mol_k']))
        self.t = list(map(mp.mpf,self.p['temperatures_k']))
        self.v = [mp.mpf(str(v)) for v in self.p['volumes_m3']]
        self.p0 = mp.mpf(str(source['reference_pressure_pa']))
        molecular = header['molecular_settings']
        masses = [mp.mpf(molecular['species'][name]['molar_mass_g_mol'])*mp.mpf(molecular['constants']['gram_kg']) for name in self.names]
        self.a = [[mp.mpf(str(self.p['area_m2']))/v*mp.sqrt(self.r*t/(2*mp.pi*m)) for m in masses]
                  for t,v in zip(self.t,self.v,strict=True)]
        self.n0 = [[mp.mpf(str(pressure))*v/(self.r*t) for pressure in pressures]
            for pressures,t,v in zip(self.p['initial_partial_pressures_pa'],self.t,self.v,strict=True)]
        self.total = [self.n0[0][i]+self.n0[1][i] for i in range(self.count)]
        self.k = [self.a[0][i]+self.a[1][i] for i in range(self.count)]
        self.limit = [self.a[1][i]*self.total[i]/self.k[i] for i in range(self.count)]
        self.offset = [self.n0[0][i]-self.limit[i] for i in range(self.count)]
        thermo = [mp_state(t,[self.p0]*self.count,pack,self.names,self.p0) for t in self.t]
        self.h = [row['h'] for row in thermo]
        self.s0 = [row['s'] for row in thermo]
        self.u = [[h-self.r*t for h in row] for row,t in zip(self.h,self.t,strict=True)]
        self.e = [[h-self.r*t/2 for h in row] for row,t in zip(self.h,self.t,strict=True)]
        self.steady_e = [self.a[0][i]*self.limit[i]*(self.e[0][i]-self.e[1][i]) for i in range(self.count)]

    def thermo(self, n):
        pressure = [[n[s][i]*self.r*self.t[s]/self.v[s] for i in range(self.count)] for s in range(2)]
        entropy = [[self.s0[s][i]-self.r*mp.log(pressure[s][i]/self.p0) for i in range(self.count)] for s in range(2)]
        energy = [mp.fsum(n[s][i]*self.u[s][i] for i in range(self.count)) for s in range(2)]
        whole_s = [mp.fsum(n[s][i]*entropy[s][i] for i in range(self.count)) for s in range(2)]
        return pressure, entropy, energy, whole_s

    def state(self, values):
        n = [[mp.mpf(float(v)) for v in values[s*self.count:(s+1)*self.count]] for s in range(2)]
        pressure,species_s,energy,entropy = self.thermo(n)
        gamma = [[self.a[s][i]*n[s][i] for i in range(self.count)] for s in range(2)]
        flow = [gamma[0][i]-gamma[1][i] for i in range(self.count)]
        flux_e = mp.fsum(gamma[0][i]*self.e[0][i]-gamma[1][i]*self.e[1][i] for i in range(self.count))
        udot = [-mp.fsum(flow[i]*self.u[0][i] for i in range(self.count)),
                 mp.fsum(flow[i]*self.u[1][i] for i in range(self.count))]
        sdot = [-mp.fsum(flow[i]*(species_s[0][i]-self.r) for i in range(self.count)),
                 mp.fsum(flow[i]*(species_s[1][i]-self.r) for i in range(self.count))]
        heat = [udot[0]+flux_e,udot[1]-flux_e]
        production = mp.fsum(sdot)-mp.fsum(heat[s]/self.t[s] for s in range(2))
        current = np.array(list(values[:2*self.count])+list(map(float,energy))+list(map(float,entropy))+list(values[-3:]))
        rates = np.array(list(map(float,[-v for v in flow]+flow+udot+sdot+heat+[production])))
        return current,rates,{'pressure':np.array(pressure,dtype=float),'flux':np.array(flow,dtype=float),
            'energy_flux':float(flux_e),'production':float(production),'heat':np.array(heat,dtype=float)}

    def analytic(self, at):
        at = mp.mpf(float(at))
        decay = [mp.exp(-k*at) for k in self.k]
        nleft = [self.limit[i]+self.offset[i]*decay[i] for i in range(self.count)]
        n = [nleft,[self.total[i]-nleft[i] for i in range(self.count)]]
        pressure,_,energy,entropy = self.thermo(n)
        heat = [mp.mpf(0),mp.mpf(0)]
        for i in range(self.count):
            integrated_offset = self.offset[i]*(-mp.expm1(-self.k[i]*at))/self.k[i]
            energy_coefficient = self.a[0][i]*self.e[0][i]+self.a[1][i]*self.e[1][i]
            heat[0] += self.steady_e[i]*at+(energy_coefficient-self.u[0][i]*self.k[i])*integrated_offset
            heat[1] += -self.steady_e[i]*at+(self.u[1][i]*self.k[i]-energy_coefficient)*integrated_offset
        s_initial = mp.fsum(self.thermo(self.n0)[3])
        production = mp.fsum(entropy)-s_initial-mp.fsum(heat[s]/self.t[s] for s in range(2))
        return np.array([*n[0],*n[1],*energy,*entropy,*heat,production],dtype=float)


def audit(path, state_budgets):
    with path.open() as stream: rows = [json.loads(line) for line in stream]
    header,initial = rows[:2]
    budget = header['settings']['verification']
    mp.mp.dps = budget['source_decimal_precision']
    reference = Reference(header); ns = reference.count; width = 2*ns
    limits = np.array([budget['local_species_mol']]*width+[budget['local_energy_j']]*2
        +[budget['local_entropy_j_k']]*2+[budget['local_energy_j']]*2+[budget['local_entropy_j_k']])
    analytic_limits = np.array([budget['analytic_inventory_mol']]*width+[budget['local_energy_j']]*2
        +[budget['local_entropy_j_k']]*2+[budget['analytic_heat_j']]*2+[budget['analytic_entropy_j_k']])
    maxima = dict.fromkeys(['global_species_mol','global_energy_j','global_entropy_j_k','source_flux_mol_s',
        'source_energy_w','source_entropy_w_k','source_pressure_pa','source_state_energy_j','source_state_entropy_j_k'],0.)
    analytic_error = np.zeros_like(limits); counts = {'recorded':0,'dense':0}
    minimum = {'inventory_mol':float('inf'),'production_w_k':float('inf')}
    origin = reference.state(initial['values'])[0]

    def review(at, values, category, recorded=None):
        nonlocal analytic_error
        counts[category] += 1
        current,rates,flux = reference.state(values)
        analytic_error = np.maximum(analytic_error,np.abs(current-reference.analytic(at)))
        n = current[:width].reshape(2,ns)
        minimum['inventory_mol'] = min(minimum['inventory_mol'],float(n.min()))
        minimum['production_w_k'] = min(minimum['production_w_k'],flux['production'])
        maxima['global_species_mol'] = max(maxima['global_species_mol'],float(np.max(np.abs(n.sum(axis=0)-np.array(reference.total,dtype=float)))))
        maxima['global_energy_j'] = max(maxima['global_energy_j'],float(abs(sum(current[width:width+2]-origin[width:width+2])-sum(values[-3:-1]))))
        maxima['global_entropy_j_k'] = max(maxima['global_entropy_j_k'],float(abs(sum(current[width+2:width+4]-origin[width+2:width+4])
            -np.dot(values[-3:-1],1/np.array(reference.t,dtype=float))-values[-1])))
        if recorded is not None:
            errors = {'source_flux_mol_s':np.max(np.abs(flux['flux']-recorded['exchange']['species_mol_s'])),
                'source_energy_w':max(abs(flux['energy_flux']-recorded['exchange']['energy_w']),np.max(np.abs(flux['heat']-recorded['heat_inputs_w']))),
                'source_entropy_w_k':abs(flux['production']-recorded['exchange']['entropy_production_w_k']),
                'source_pressure_pa':np.max(np.abs(flux['pressure']-np.array([s['partial_pressures_pa'] for s in recorded['states']]))),
                'source_state_energy_j':np.max(np.abs(current[width:width+2]-[s['internal_energy_j'] for s in recorded['states']])),
                'source_state_entropy_j_k':np.max(np.abs(current[width+2:width+4]-[s['entropy_j_k'] for s in recorded['states']]))}
            for key,value in errors.items(): maxima[key] = max(maxima[key],float(value))
        return current,rates

    for row in rows:
        if row['kind'] in ['initial','accepted','sample']:
            review(row['time_s'],row['values'],'recorded',row)
    integrals, reports = [], []
    for order in budget['entropy_quadrature_orders']:
        nodes,weights = leggauss(order)
        previous,cumulative = origin,np.zeros_like(origin)
        local,cumulative_error = np.zeros_like(origin),np.zeros_like(origin)
        increments = []; minimum_step = float('inf')
        for row in rows:
            if row['kind'] != 'accepted': continue
            left,right = [row['dense_output'][k] for k in ['start_time_s','end_time_s']]
            increment = np.zeros_like(origin)
            for node,weight in zip(nodes,weights,strict=True):
                at = (left+right)/2+(right-left)*node/2
                increment += weight*(right-left)/2*review(at,polynomial(row,at),'dense')[1]
            current = reference.state(row['values'])[0]
            cumulative += increment; increments.append(increment)
            local = np.maximum(local,np.abs(current-previous-increment))
            cumulative_error = np.maximum(cumulative_error,np.abs(current-origin-cumulative))
            minimum_step = min(minimum_step,float(sum(current[width+2:width+4]-previous[width+2:width+4])
                -np.dot(current[-3:-1]-previous[-3:-1],1/np.array(reference.t,dtype=float))))
            previous = current
        integrals.append(np.array(increments))
        flags = {'local':bool(np.all(local<=limits)),'cumulative':bool(np.all(cumulative_error<=limits)),
                 'nonnegative_step':minimum_step>=-budget['nonnegative_step_entropy_j_k']}
        reports.append({'order':order,'maximum_local_residuals':local.tolist(),'maximum_cumulative_residuals':cumulative_error.tolist(),
                        'minimum_combined_entropy_step_j_k':minimum_step,'within_budgets':flags})
        print(json.dumps({'trajectory':str(path),'order':order,'within_budgets':flags}),flush=True)
    difference = integrals[1]-integrals[0]
    quadrature = np.maximum(np.max(abs(difference),axis=0),np.max(abs(np.cumsum(difference,axis=0)),axis=0))
    final = reference.state(rows[-1]['final']['values'])[2]
    ratio_error = float(np.max(np.abs(final['pressure'][0]/final['pressure'][1]/float(mp.sqrt(reference.t[0]/reference.t[1]))-1)))
    source_limits = {**state_budgets,**{k:budget[k] for k in ['source_flux_mol_s','source_energy_w','source_entropy_w_k','global_species_mol']},
                     'global_energy_j':budget['local_energy_j'],'global_entropy_j_k':budget['local_entropy_j_k']}
    flags = {key:value<=source_limits[key] for key,value in maxima.items()}
    flags.update(completed=rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        positive_inventory=minimum['inventory_mol']>0,nonnegative_production=minimum['production_w_k']>=-budget['nonnegative_entropy_w_k'],
        analytic_solution=bool(np.all(analytic_error<=analytic_limits)),full_integrals=all(all(r['within_budgets'].values()) for r in reports),
        quadrature=bool(np.all(quadrature<=limits)),steady_thermal_pressure_ratio=ratio_error<=budget['final_pressure_ratio_relative'])
    return {'trajectory':str(path),'counts':counts,'maxima':maxima,'minima':minimum,'analytic_maximum_errors':analytic_error.tolist(),
        'analytic_budgets':analytic_limits.tolist(),'integral_reviews':reports,'quadrature_maximum_differences':quadrature.tolist(),
        'final_thermal_pressure_ratio_relative_error':ratio_error,'within_budgets':flags,'all_requested_budgets_met':all(flags.values())},rows


def compare(base, refined):
    settings = base[0]['settings']; source = base[0]['source_settings']; ns = len(source['species_order']); width = 2*ns
    accepted = [[r for r in rows if r['kind']=='accepted'] for rows in [base,refined]]
    ends = [[r['time_s'] for r in rows] for rows in accepted]; times = {0.}
    for rows,steps in zip([base,refined],accepted,strict=True):
        times.update(r['time_s'] for r in rows if r['kind'] in ['sample','accepted'])
        for order in settings['verification']['entropy_quadrature_orders']:
            nodes,_ = leggauss(order)
            for row in steps:
                left,right = [row['dense_output'][k] for k in ['start_time_s','end_time_s']]
                times.update(float((left+right)/2+(right-left)*node/2) for node in nodes)
    maximum = np.zeros(len(base[1]['values'])); pressure = 0.
    rt_over_volume = base[0]['thermochemistry']['gas_constant']['value_j_mol_k']*np.asarray(settings['temperatures_k'])/settings['volumes_m3']
    for at in sorted(times):
        values = [np.asarray(rows[1]['values']) if at==0 else polynomial(steps[bisect_left(end,at)],at)
            for rows,steps,end in zip([base,refined],accepted,ends,strict=True)]
        delta = values[0]-values[1]; maximum = np.maximum(maximum,np.abs(delta))
        pressure = max(pressure,float(np.max(np.abs(delta[:width].reshape(2,ns).sum(axis=1)*rt_over_volume))))
    q = settings['verification']
    return {'times_compared':len(times),'maximum_inventory_difference_mol':float(maximum[:width].max()),
        'maximum_heat_difference_j':float(maximum[-3:-1].max()),'maximum_pressure_difference_pa':pressure,
        'within_budget':bool(maximum[:width].max()<=q['time_inventory_mol'] and maximum[-3:-1].max()<=q['time_heat_j'] and pressure<=q['time_pressure_pa']),
        'scope':'Native accepted/2and4Gauss/observed node union; analytic source review separately covers the same nodes. No continuous numerical-error supremum claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();root=args.parameters.resolve().parent;p=json.loads(args.parameters.read_text())
    reports,rows = {},{}
    for name,path in p['trajectories'].items(): reports[name],rows[name]=audit(root/path,p['source_state_budgets'])
    time = compare(rows['base'],rows['refined'])
    result = {'settings':p,'trajectory_reviews':reports,'time_comparison':time,
        'all_requested_budgets_met':all(r['all_requested_budgets_met'] for r in reports.values()) and time['within_budget'],
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_budgets_met':result['all_requested_budgets_met'],'time_comparison':time}),flush=True)


if __name__ == '__main__':
    main()
