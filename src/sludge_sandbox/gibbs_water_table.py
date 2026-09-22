"""Offline, bounded Chebyshev approximation of pure-liquid Gibbs energy.

All caloric and volumetric properties derive from one fitted potential. This is
an explicitly approximate IAPWS representation, never a measured material law.
"""
from dataclasses import dataclass

import numpy as np
from numpy.polynomial.chebyshev import chebder, chebval2d


@dataclass(frozen=True)
class LiquidFromGibbs:
    molar_mass_kg_mol: float
    density_kg_m3: float
    enthalpy_j_mol: float
    internal_energy_j_mol: float
    native_entropy_j_kg_k: float


class GibbsWaterTable:
    def __init__(self, direct_water, table):
        self.direct_water = direct_water
        self.reference = direct_water.reference
        self.table = table
        self.source_record = {**direct_water.source_record, 'liquid_representation': table}
        self.bounds = np.array([table['temperature_domain_k'], table['pressure_domain_pa']], dtype=float)
        self.centers = self.bounds.mean(axis=1)
        self.scales = (self.bounds[:, 1]-self.bounds[:, 0])/2
        self.coefficients = np.array(table['gibbs_coefficients_j_mol'])
        self.dt = chebder(self.coefficients, axis=0)/self.scales[0]
        self.dp = chebder(self.coefficients, axis=1)/self.scales[1]
        self.dtt = chebder(self.dt, axis=0)/self.scales[0]
        self.dtp = chebder(self.dt, axis=1)/self.scales[1]
        self.dpp = chebder(self.dp, axis=1)/self.scales[1]

    def ideal_vapor(self, temperature_k):
        return self.direct_water.ideal_vapor(temperature_k)

    def gibbs_properties(self, temperature_k, pressure_pa):
        values = np.array([temperature_k, pressure_pa])
        if np.any(values < self.bounds[:, 0]) or np.any(values > self.bounds[:, 1]):
            raise ValueError('state outside the declared liquid Gibbs-table domain')
        x, y = (values-self.centers)/self.scales
        g = float(chebval2d(x, y, self.coefficients))+self.table['native_gibbs_offset_j_mol']
        gt, gp = float(chebval2d(x, y, self.dt)), float(chebval2d(x, y, self.dp))
        gtt = float(chebval2d(x, y, self.dtt))
        gtp, gpp = float(chebval2d(x, y, self.dtp)), float(chebval2d(x, y, self.dpp))
        enthalpy = g-temperature_k*gt+self.reference.energy_offset_j_mol
        return {'native_gibbs_j_mol': g, 'molar_volume_m3_mol': gp, 'entropy_j_mol_k': -gt,
                'enthalpy_j_mol': enthalpy, 'internal_energy_j_mol': enthalpy-pressure_pa*gp,
                'cp_j_mol_k': -temperature_k*gtt,
                'cv_j_mol_k': -temperature_k*gtt+temperature_k*gtp*gtp/gpp,
                'isothermal_compressibility_pa_inverse': -gpp/gp,
                'thermal_expansion_k_inverse': gtp/gp}

    def state_tp(self, temperature_k, pressure_pa, *, phase):
        if phase != 'liquid':
            raise ValueError('Gibbs table represents only stable pure liquid')
        p = self.gibbs_properties(temperature_k, pressure_pa)
        mass = self.reference.molar_mass_kg_mol
        return LiquidFromGibbs(mass, mass/p['molar_volume_m3_mol'], p['enthalpy_j_mol'],
                              p['internal_energy_j_mol'], p['entropy_j_mol_k']/mass)
