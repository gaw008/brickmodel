"""Wilke low-density mixture viscosity, with caller-supplied pure properties.

Formula/reciprocity follow Cantera 3.2 GasTransport.cpp lines 60--101 and its
Poling (2001) reference. Retained source/license: gas-transport-source-v1/source.
Positive viscosities/molar masses and nonnegative normalized mole fractions
define the input domain. This mixing rule does not add experimental accuracy
to the supplied pure-gas properties.
"""
import math

import numpy as np


def wilke_viscosity_pa_s(mole_fractions, pure_viscosities_pa_s, molar_masses_kg_mol):
    fractions = np.asarray(mole_fractions)
    viscosities = np.asarray(pure_viscosities_pa_s)
    masses = np.asarray(molar_masses_kg_mol)
    weights = np.zeros((len(fractions), len(fractions)))
    for j in range(len(fractions)):
        for k in range(j, len(fractions)):
            viscosity_ratio = viscosities[k]/viscosities[j]
            mass_ratio = masses[j]/masses[k]
            numerator = (1+math.sqrt(viscosity_ratio)*mass_ratio**0.25)**2
            weights[k, j] = numerator/math.sqrt(8*(1+1/mass_ratio))
            weights[j, k] = weights[k, j]/(viscosity_ratio*mass_ratio)
    mixture = float(np.sum(fractions*viscosities/(weights@fractions)))
    return {'viscosity_pa_s': mixture, 'weighting_factors': weights}
