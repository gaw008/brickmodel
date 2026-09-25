"""First-order dilute binary viscosity, Vogel/Bich/Hellmann2023 Eqs13/15/17.

Inputs are positive pure/interaction viscosities, positive molar masses,
the cross-section ratio A*, and the mole fraction of component1 in[0,1].
No temperature interpolation or interaction-property fit is implicit here.
The common x1*x2 factor is canceled analytically, retaining pure endpoints.
"""


def binary_viscosity_pa_s(x1, pure_viscosities_pa_s, molar_masses_kg_mol,
                          interaction_viscosity_pa_s, cross_section_ratio):
    x2 = 1 - x1
    eta1, eta2 = pure_viscosities_pa_s
    mass1, mass2 = molar_masses_kg_mol
    ratio = mass2 / mass1
    t = 5 / (3 * cross_section_ratio)
    k = 2 * mass1 * mass2 / ((mass1 + mass2)**2 * interaction_viscosity_pa_s)
    a, b, c = t + ratio, t + 1 / ratio, t - 1
    numerator = x1*x2*(1/eta1 + 1/eta2 + 2*k*c) + x1*x1*k*b + x2*x2*k*a
    denominator = (x1*x2/(eta1*eta2) + x1*x1*k*b/eta1 + x2*x2*k*a/eta2
                   + x1*x2*k*k*t*(ratio + 1/ratio + 2))
    return numerator / denominator


def interaction_viscosity_from_molar_diffusion(rho_diffusivity_mol_m_s,
                                               molar_masses_kg_mol,
                                               cross_section_ratio):
    """Eq31 rearranged using molar rather than single-molecule masses."""
    mass1, mass2 = molar_masses_kg_mol
    return (5/3 * mass1*mass2/(mass1 + mass2)
            * rho_diffusivity_mol_m_s / cross_section_ratio)
