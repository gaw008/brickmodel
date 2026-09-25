"""Scientific comparison of the conditional free/sorbed-water potential.

Reintegrates source nodes and numerically minimizes their continued potential;
the production provider is used only as the quantity being compared.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize_scalar, brentq

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_sorption import RecordedSourceSorption
from sludge_sandbox.recorded_sorption_free_water import RecordedSorptionFreeWater


class IntegratedReference:
    def __init__(self, record, policy):
        self.record, self.policy = record, policy
        self.t0 = record['reference_temperature_k']
        self.r, self.mass = record['gas_constant_j_mol_k'], record['water_molar_mass_kg_mol']
        self.end = record['reference_moisture_kg_kg']
        self.join = record['join']['moisture_kg_kg']
        a, q = (record['source_curves'][name] for name in ('activity', 'heat'))
        self.ax = np.array([p['moisture_kg_kg'] for p in a])
        self.ay = self.r/self.mass*self.t0*np.log([p['value'] for p in a])
        self.qx = np.array([p['moisture_kg_kg'] for p in q])
        self.by = record['reference_ideal_vapor_minus_liquid_enthalpy_j_kg']-np.array([p['value'] for p in q])
        self.breaks = sorted(set([0., *self.ax, *self.qx]))

    @staticmethod
    def end_line(w, x, y):
        return y[-1]+(w-x[-1])*(y[-1]-y[-2])/(x[-1]-x[-2])

    def m(self, w):
        if w < self.join:
            return self.ay[0]+self.r/self.mass*self.t0*math.log(w/self.join)
        return float(np.interp(w, self.ax, self.ay)) if w <= self.end else self.end_line(w, self.ax, self.ay)

    def b(self, w):
        return float(np.interp(w, self.qx, self.by)) if w <= self.end else self.end_line(w, self.qx, self.by)

    def raw(self, t, w):
        q = self.policy['quadrature']
        lo, hi = sorted([self.end, w])
        points = [x for x in self.breaks if lo < x < hi]
        integrate = lambda f: quad(f, self.end, w, points=points,
            epsabs=q['absolute_tolerance'], epsrel=q['relative_tolerance'], limit=q['maximum_subintervals'])[0]
        h, g = integrate(self.b), integrate(self.m)
        s = (h-g)/self.t0
        return h, s, h-t*s

    def chemical_potential(self, t, w):
        return self.mass*(self.b(w)-t*(self.b(w)-self.m(w))/self.t0)

    def saturation(self, t):
        return brentq(lambda w: self.chemical_potential(t, w), self.end,
                      self.record['model_domain']['moisture_kg_kg'][1],
                      xtol=self.policy['minimization']['moisture_absolute_tolerance'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    settings = json.loads(args.parameters.read_text()); root = args.parameters.resolve().parent
    record = json.loads((root/settings['source_record_file']).read_text())
    provider = RecordedSorptionFreeWater(record)
    old = RecordedSourceSorption(json.loads((root/settings['previous_source_record_file']).read_text()))
    ref = IntegratedReference(record, settings)
    dt, dw = settings['temperature_difference_step_k'], settings['moisture_difference_step_kg_kg']
    states, boundaries, domains = [], [], []
    for t in settings['temperatures_k']+settings['endpoint_temperatures_k']:
        saturation = provider.saturation(t)
        domains.append({'temperature_k':t, **saturation,
            'independent_saturation_kg_kg':ref.saturation(t)})
    for t in settings['temperatures_k']:
        ws = ref.saturation(t)
        eps = settings['phase_boundary_offset_kg_kg']
        lower, upper = (provider.evaluate(t, ws+d) for d in [-eps, eps])
        boundaries.append({'temperature_k':t,'saturation_moisture_kg_kg':ws,
            'energy_jump_comparison_j_kg_dry':upper['h_j_kg_dry']-lower['h_j_kg_dry'],
            'entropy_jump_comparison_j_kg_dry_k':upper['s_j_kg_dry_k']-lower['s_j_kg_dry_k'],
            'mu_jump_comparison_j_mol':upper['mu_j_mol']-lower['mu_j_mol']})
        for w in settings['moistures_kg_kg']:
            actual = provider.evaluate(t,w)
            wb = min(w, ws)
            h,s,f = ref.raw(t,wb)
            mu = 0. if w >= ws else ref.chemical_potential(t,w)
            options = settings['minimization']
            minimum = minimize_scalar(lambda x:ref.raw(t,x)[2],bounds=(0.,w),method='bounded',
                options={'xatol':options['moisture_absolute_tolerance'],'maxiter':options['maximum_iterations']})
            candidates = [(0.,ref.raw(t,0.)[2]),(w,ref.raw(t,w)[2]),(float(minimum.x),float(minimum.fun))]
            minimum_w, minimum_f = min(candidates,key=lambda p:p[1])
            tl,th = (provider.evaluate(t+d,w) for d in [-dt,dt])
            wl,wh = (provider.evaluate(t,w+d) for d in [-dw,dw])
            item = {'temperature_k':t,'total_moisture_kg_kg':w,'branch':actual['branch'],
                'sorbed_moisture_kg_kg':actual['sorbed_moisture_kg_kg'],
                'free_moisture_kg_kg':actual['free_moisture_kg_kg'],
                'energy_difference_j_kg_dry':actual['h_j_kg_dry']-h,
                'entropy_difference_j_kg_dry_k':actual['s_j_kg_dry_k']-s,
                'mu_difference_j_mol':actual['mu_j_mol']-mu,
                'minus_df_dt_minus_s_j_kg_dry_k':-(th['f_j_kg_dry']-tl['f_j_kg_dry'])/(2*dt)-actual['s_j_kg_dry_k'],
                'mass_df_dw_minus_mu_j_mol':ref.mass*(wh['f_j_kg_dry']-wl['f_j_kg_dry'])/(2*dw)-actual['mu_j_mol'],
                'dh_dt_minus_cp_j_kg_dry_k':(th['h_j_kg_dry']-tl['h_j_kg_dry'])/(2*dt)-actual['equilibrium_excess_heat_capacity_j_kg_dry_k'],
                'equilibrium_excess_heat_capacity_j_kg_dry_k':actual['equilibrium_excess_heat_capacity_j_kg_dry_k'],
                'minimum_potential_difference_j_kg_dry':actual['f_j_kg_dry']-minimum_f,
                'minimum_moisture_kg_kg':minimum_w,'minimizer_converged':bool(minimum.success)}
            if w <= ref.end:
                previous = old.evaluate(t,w)
                item['previous_domain_differences']={key:actual[key]-previous[key]
                    for key in ('h_j_kg_dry','s_j_kg_dry_k','f_j_kg_dry','mu_j_mol','activity')}
            states.append(item)
    budget=settings['budgets']
    fields={'energy_difference_j_kg_dry':'energy_j_kg_dry','entropy_difference_j_kg_dry_k':'entropy_j_kg_dry_k',
        'mu_difference_j_mol':'chemical_potential_j_mol','minus_df_dt_minus_s_j_kg_dry_k':'temperature_entropy_derivative_j_kg_dry_k',
        'mass_df_dw_minus_mu_j_mol':'moisture_chemical_potential_derivative_j_mol',
        'dh_dt_minus_cp_j_kg_dry_k':'heat_capacity_j_kg_dry_k',
        'minimum_potential_difference_j_kg_dry':'minimum_potential_difference_j_kg_dry'}
    maxima={key:max(abs(p[key]) for p in states) for key in fields}
    conditions={key:bool(maxima[key]<=budget[name]) for key,name in fields.items()}
    conditions['minimizers_converged']=all(p['minimizer_converged'] for p in states)
    conditions['positive_end_curvature']=all(p['curvature_j_kg_dry']>0 for p in domains)
    conditions['saturation_beyond_source_and_within_calculation_domain']=all(ref.end<p['moisture_kg_kg']<record['model_domain']['moisture_kg_kg'][1] for p in domains)
    conditions['independent_saturation']=all(abs(p['moisture_kg_kg']-p['independent_saturation_kg_kg'])<=budget['saturation_moisture_difference_kg_kg'] for p in domains)
    conditions['nonnegative_equilibrium_excess_capacity']=all(p['equilibrium_excess_heat_capacity_j_kg_dry_k']>=0 for p in states)
    conditions['previous_domain_unchanged']=all(all(v==0 for v in p['previous_domain_differences'].values()) for p in states if 'previous_domain_differences' in p)
    for key,name in {'energy_jump_comparison_j_kg_dry':'phase_boundary_energy_j_kg_dry',
                     'entropy_jump_comparison_j_kg_dry_k':'phase_boundary_entropy_j_kg_dry_k',
                     'mu_jump_comparison_j_mol':'phase_boundary_mu_j_mol'}.items():
        conditions[key]=all(abs(p[key])<=budget[name] for p in boundaries)
    result={'parameters':settings,'source_record':record,'states':states,'phase_boundaries':boundaries,
        'temperature_domain_points':domains,'maxima':maxima,'within_budgets':conditions,
        'qualification':'Conditional potential arithmetic and sampled derivatives only; tail and instantaneous partition are material assumptions.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'states':len(states),'maxima':maxima,'within_budgets':conditions},indent=2))


if __name__ == '__main__':
    main()
