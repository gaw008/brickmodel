"""Recorded low-moisture excess potential with explicitly limited source scope.

The source join is prepared from published activity/desorption-heat curves.
Below that join the existing ideal-dilution extension is a declared model,
not a new measurement. Its finite dry-end energy/entropy references are retained.
"""
from dataclasses import dataclass
import math


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
        cp = self.record['dry_caloric_relation']
        offset = self.record['celsius_zero_k']
        a, b = reference_k-offset, temperature_k-offset
        return cp['intercept']*(b-a)+cp['slope_per_degC']*(b*b-a*a)/2

    def dry_entropy_difference_j_kg_k(self, temperature_k, reference_k):
        cp = self.record['dry_caloric_relation']
        a = cp['intercept']-cp['slope_per_degC']*self.record['celsius_zero_k']
        return a*math.log(temperature_k/reference_k)+cp['slope_per_degC']*(temperature_k-reference_k)
