"""Source-standard reaction functions, with dimensionless equilibrium constants."""
import math


def standard_reaction(phases, stoichiometry, temperature_k, gas_constant_j_mol_k):
    states={name:phases[name].standard(temperature_k) for name in stoichiometry}
    totals={quantity:math.fsum(coefficient*states[name][quantity] for name,coefficient in stoichiometry.items())
            for quantity in ['enthalpy_j_mol','entropy_j_mol_k','cp_j_mol_k']}
    gibbs=totals['enthalpy_j_mol']-temperature_k*totals['entropy_j_mol_k']
    return {**totals,'gibbs_j_mol':gibbs,
            'log_equilibrium':-gibbs/(gas_constant_j_mol_k*temperature_k),
            'gibbs_temperature_derivative_j_mol_k':-totals['entropy_j_mol_k'],
            'vant_hoff_derivative_per_k':totals['enthalpy_j_mol']/(gas_constant_j_mol_k*temperature_k**2)}
