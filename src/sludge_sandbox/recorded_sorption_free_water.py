"""Explicit end-slope sorption continuation with free-water coexistence.

The continuation is a declared material approximation. Its equilibrium
partition follows one excess potential; it is not a new measured isotherm.
"""
from dataclasses import dataclass
from functools import cached_property
import math

from .recorded_sorption import RecordedSourceSorption


@dataclass(frozen=True)
class RecordedSorptionFreeWater(RecordedSourceSorption):
    @cached_property
    def end_slopes(self):
        slopes = {}
        for key, nodes in self.curves.items():
            (wl, vl), (wr, vr) = nodes[-2:]
            slopes[key] = (vr-vl)/(wr-wl)
        return slopes

    def saturation(self, temperature_k):
        t0 = self.record['reference_temperature_k']
        we = self.record['reference_moisture_kg_kg']
        fraction = temperature_k/t0
        m, b = (self.curves[key][-1][1] for key in ('m', 'b'))
        slope = fraction*self.end_slopes['m']+(1-fraction)*self.end_slopes['b']
        offset = fraction*m+(1-fraction)*b
        ws = we-offset/slope
        partial_h = b+self.end_slopes['b']*(ws-we)
        return {'moisture_kg_kg': ws, 'curvature_j_kg_dry': slope,
                'temperature_derivative_kg_kg_k': partial_h/(temperature_k*slope),
                'excess_heat_capacity_j_kg_dry_k': partial_h**2/(temperature_k*slope)}

    def evaluate(self, temperature_k, moisture_kg_kg):
        t, w = temperature_k, moisture_kg_kg
        domain = self.record['model_domain']
        if not domain['temperature_k'][0] <= t <= domain['temperature_k'][1]:
            raise ValueError('temperature outside declared sorption/free-water domain')
        if not domain['moisture_kg_kg'][0] <= w <= domain['moisture_kg_kg'][1]:
            raise ValueError('total condensed moisture outside declared sorption/free-water domain')
        saturation = self.saturation(t)
        ws = saturation['moisture_kg_kg']
        wb = min(w, ws)
        we = self.record['reference_moisture_kg_kg']
        if wb <= we:
            result = super().evaluate(t, wb)
            branch = 'low' if wb <= self.record['join']['moisture_kg_kg'] else 'source'
        else:
            delta = wb-we
            m, b = (self.curves[key][-1][1] for key in ('m', 'b'))
            h = b*delta+self.end_slopes['b']*delta**2/2
            g0 = m*delta+self.end_slopes['m']*delta**2/2
            t0 = self.record['reference_temperature_k']
            s = (h-g0)/t0
            partial_b = b+self.end_slopes['b']*delta
            partial_m = m+self.end_slopes['m']*delta
            mass = self.record['water_molar_mass_kg_mol']
            r = self.record['gas_constant_j_mol_k']
            # At coexistence the total-water derivative is exactly zero.
            # H_ex and S_ex at the minimizing sorbed inventory remain stored.
            saturated = w >= ws
            mu = 0. if saturated else mass*(t/t0*partial_m+(1-t/t0)*partial_b)
            result = {'h_j_kg_dry': h, 's_j_kg_dry_k': s, 'f_j_kg_dry': h-t*s,
                      'partial_h_j_mol': 0. if saturated else mass*partial_b,
                      'mu_j_mol': mu, 'mu_limit': None, 'activity': math.exp(mu/(r*t)),
                      'activity_at_join': super().evaluate(t, self.record['join']['moisture_kg_kg'])['activity']}
            branch = 'free_water' if saturated else 'end_slope_continuation'
        return {**result, 'branch': branch, 'sorbed_moisture_kg_kg': wb,
                'free_moisture_kg_kg': w-wb, 'saturation': saturation,
                'equilibrium_excess_heat_capacity_j_kg_dry_k':
                    None if w == ws else (saturation['excess_heat_capacity_j_kg_dry_k'] if w > ws else 0.)}
