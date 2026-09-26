"""Use source extent bisection and element balances in every pore record."""
import mpmath as mp

from audit_thermal_spherical_pore import main
from equilibrium_pore_reference import EquilibriumPoreReference


def reference_factory(header):
    p = header['settings']
    initial = {name:header['gas_amount_mol']*fraction for name,fraction in p['gas_feed_fractions'].items()}
    return EquilibriumPoreReference(p,header['sources'],initial)


def source_differences(actual, computed, reference, policy):
    fields = [key for key in policy['source_budgets'] if key not in ['gas_amount_mol','element_mol']]
    errors = {key:float(abs(mp.mpf(actual[key])-computed[key])) for key in fields}
    errors['reaction_gibbs_j_mol'] = max(errors['reaction_gibbs_j_mol'], abs(actual['reaction_gibbs_j_mol']))
    errors['gas_amount_mol'] = float(max(abs(mp.mpf(actual['gas_amounts_mol'][name])-amount) for name,amount in computed['gas_amounts_mol'].items()))
    atoms = reference.gas.p['atoms']
    errors['element_mol'] = float(max(abs(mp.fsum(atoms[name].get(element,0)*(mp.mpf(actual['gas_amounts_mol'][name])-amount) for name,amount in reference.initial.items())) for element in ['C','H','O','N']))
    return errors


if __name__ == '__main__':
    main(reference_factory,source_differences)
