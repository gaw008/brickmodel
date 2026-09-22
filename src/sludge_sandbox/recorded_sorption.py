"""Recorded low-moisture excess potential with explicitly limited source scope.

The source join is prepared from published activity/desorption-heat curves.
Below that join the existing ideal-dilution extension is a declared model,
not a new measurement. Its finite dry-end energy/entropy references are retained.
"""
from dataclasses import dataclass
from functools import cached_property
import math
from bisect import bisect_right


@dataclass(frozen=True)
class RecordedLowMoisture:
    record: dict

    def evaluate(self, temperature_k, moisture_kg_kg):
        domain = self.record['model_domain']
        join = self.record['join']
        wj = join['moisture_kg_kg']
        if not domain['temperature_k'][0] <= temperature_k <= domain['temperature_k'][1]:
            raise ValueError('temperature outside declared sorption extension domain')
        if not 0 <= moisture_kg_kg <= wj:
            raise ValueError('moisture outside the selected low-moisture branch')
        w, t = moisture_kg_kg, temperature_k
        r, mass = self.record['gas_constant_j_mol_k'], self.record['water_molar_mass_kg_mol']
        delta = w-wj
        psi = w*math.log(w/wj)-delta if w else wj
        h = join['h_j_kg_dry']+join['partial_h_j_kg_water']*delta
        s = join['s_j_kg_dry_k']+join['partial_s_j_kg_water_k']*delta-r/mass*psi
        mu_join = mass*(join['partial_h_j_kg_water']-t*join['partial_s_j_kg_water_k'])
        activity_join = math.exp(mu_join/(r*t))
        return {'h_j_kg_dry': h, 's_j_kg_dry_k': s, 'f_j_kg_dry': h-t*s,
                'partial_h_j_mol': mass*join['partial_h_j_kg_water'],
                'mu_j_mol': mu_join+r*t*math.log(w/wj) if w else None,
                'mu_limit': 'negative_infinity' if w == 0 else None,
                'activity': activity_join*w/wj, 'activity_at_join': activity_join}

    def dry_energy_difference_j_kg(self, temperature_k, reference_k):
        """Use source Cp as a fixed-volume dry-storage coefficient.

        This is the declared incompressible/nonexpanding dry-phase model,
        not a measured sludge Cv or an absolute formation-energy reference.
        See parameters.sorptive_caloric_interpretation.json.
        """
        cp = self.record['dry_caloric_relation']
        offset = self.record['celsius_zero_k']
        a, b = reference_k-offset, temperature_k-offset
        return cp['intercept']*(b-a)+cp['slope_per_degC']*(b*b-a*a)/2

    def dry_entropy_difference_j_kg_k(self, temperature_k, reference_k):
        cp = self.record['dry_caloric_relation']
        a = cp['intercept']-cp['slope_per_degC']*self.record['celsius_zero_k']
        return a*math.log(temperature_k/reference_k)+cp['slope_per_degC']*(temperature_k-reference_k)


@dataclass(frozen=True)
class RecordedSourceSorption(RecordedLowMoisture):
    """The same recorded wet-source branch joined to ideal dilution below Wj.

    Interpolation and integration are on represented binary64 source values.
    Their physical/model uncertainty is not an integration tolerance.
    """

    @cached_property
    def curves(self):
        record = self.record
        scale = record['gas_constant_j_mol_k']/record['water_molar_mass_kg_mol']*record['reference_temperature_k']
        latent = record['reference_ideal_vapor_minus_liquid_enthalpy_j_kg']
        return {
            'm': [(p['moisture_kg_kg'], scale*math.log(p['value'])) for p in record['source_curves']['activity']],
            'b': [(p['moisture_kg_kg'], latent-p['value']) for p in record['source_curves']['heat']]}

    @staticmethod
    def interpolate(nodes, w):
        index = min(bisect_right([p[0] for p in nodes], w)-1, len(nodes)-2)
        (left, a), (right, b) = nodes[index:index+2]
        return a+(w-left)/(right-left)*(b-a)

    @classmethod
    def integral_to_reference(cls, nodes, w):
        points = [(w, cls.interpolate(nodes, w))]+[p for p in nodes if p[0]>w]
        return -math.fsum((right-left)*(a+b)/2 for (left,a),(right,b) in zip(points[:-1],points[1:],strict=True))

    def evaluate(self, temperature_k, moisture_kg_kg):
        w, t = moisture_kg_kg, temperature_k
        if w <= self.record['join']['moisture_kg_kg']:
            return super().evaluate(t,w)
        domain = self.record['model_domain']
        if not domain['temperature_k'][0] <= t <= domain['temperature_k'][1]:
            raise ValueError('temperature outside declared sorption extension domain')
        if not domain['moisture_kg_kg'][0] <= w <= domain['moisture_kg_kg'][1]:
            raise ValueError('moisture outside recorded sorption source branch')
        t0 = self.record['reference_temperature_k']
        h = self.integral_to_reference(self.curves['b'],w)
        g0 = self.integral_to_reference(self.curves['m'],w)
        s = (h-g0)/t0
        b0, m0 = (self.interpolate(self.curves[k],w) for k in ('b','m'))
        mass, r = self.record['water_molar_mass_kg_mol'], self.record['gas_constant_j_mol_k']
        mu = mass*(t/t0*m0+(1-t/t0)*b0)
        return {'h_j_kg_dry':h, 's_j_kg_dry_k':s, 'f_j_kg_dry':h-t*s,
                'partial_h_j_mol':mass*b0, 'mu_j_mol':mu, 'mu_limit':None,
                'activity':math.exp(mu/(r*t)),
                'activity_at_join':super().evaluate(t,self.record['join']['moisture_kg_kg'])['activity']}
