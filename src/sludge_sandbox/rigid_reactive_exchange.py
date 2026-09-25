"""Two gas modes with a declared positive Onsager mobility on a rigid-cell face."""
import math


def rigid_reactive_face(left, right, parameters):
    tl, tr = left['temperature_k'], right['temperature_k']
    inverse_jump = 1 / tr - 1 / tl
    species = ('co2', 'nitrogen')
    potential = ('carbon', 'nitrogen')
    enthalpies = [(left[k + '_partial_enthalpy_j_mol'] + right[k + '_partial_enthalpy_j_mol']) / 2 for k in species]
    forces = [math.fsum((left[k + '_chemical_potential_j_mol'] / tl,
                        -right[k + '_chemical_potential_j_mol'] / tr, h * inverse_jump))
              for k, h in zip(potential, enthalpies, strict=True)]
    fractions = [(left[k + '_mol'] / (left['co2_mol'] + left['nitrogen_mol'])
                  + right[k + '_mol'] / (right['co2_mol'] + right['nitrogen_mol'])) / 2 for k in species]
    bulk_force = math.fsum(x * y for x, y in zip(fractions, forces, strict=True))
    diffusion_force = forces[0] - forces[1]
    bulk = parameters['bulk_mobility_mol2_k_j_s'] * bulk_force
    counter = parameters['counter_mobility_mol2_k_j_s'] * diffusion_force
    flows = [fractions[0] * bulk + counter, fractions[1] * bulk - counter]
    heat = parameters['heat_conductance_w_k'] * (tl - tr)
    energy = math.fsum([heat] + [h * n for h, n in zip(enthalpies, flows, strict=True)])
    return {'carbon_flow_mol_s': flows[0], 'nitrogen_flow_mol_s': flows[1], 'energy_flow_w': energy,
            'conductive_heat_w': heat, 'face_partial_enthalpies_j_mol': enthalpies,
            'face_mole_fractions': fractions, 'species_forces_j_mol_k': forces,
            'bulk_force_j_mol_k': bulk_force, 'counter_force_j_mol_k': diffusion_force,
            'bulk_flow_mol_s': bulk, 'counter_flow_mol_s': counter,
            'entropy_production_w_k': math.fsum((heat * inverse_jump,
                parameters['bulk_mobility_mol2_k_j_s'] * bulk_force**2,
                parameters['counter_mobility_mol2_k_j_s'] * diffusion_force**2))}
