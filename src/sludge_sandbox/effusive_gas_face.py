"""Collisionless, zero-thickness aperture between ideal equilibrium gases.

Maxwell half-space flux carries h - RT/2 per mole, including formation
energy and internal degrees of freedom. This is a molecular-flow limit,
not a porous-medium law or a pressure-regime interpolation.
"""
import math


def effusive_gas_face(left, right, parameters, gas_constant_j_mol_k):
    r = gas_constant_j_mol_k
    tl, tr = left['temperature_k'], right['temperature_k']
    area = parameters['area_m2']
    species = {}
    for name, potential in [('co2', 'carbon'), ('nitrogen', 'nitrogen')]:
        mass = parameters['molar_masses_kg_mol'][name]
        jl = left[name+'_partial_pressure_pa']/math.sqrt(2*math.pi*mass*r*tl)
        jr = right[name+'_partial_pressure_pa']/math.sqrt(2*math.pi*mass*r*tr)
        el = left[name+'_partial_enthalpy_j_mol']-r*tl/2
        er = right[name+'_partial_enthalpy_j_mol']-r*tr/2
        flow = area*(jl-jr)
        energy = area*(jl*el-jr*er)
        force = left[potential+'_chemical_potential_j_mol']/tl-right[potential+'_chemical_potential_j_mol']/tr
        entropy = math.fsum((flow*force, energy*(1/tr-1/tl)))
        species[name] = {
            'left_incident_mol_m2_s': jl, 'right_incident_mol_m2_s': jr,
            'left_carried_energy_j_mol': el, 'right_carried_energy_j_mol': er,
            'flow_mol_s': flow, 'energy_flow_w': energy,
            'entropy_production_w_k': entropy,
        }
    return {
        'carbon_flow_mol_s': species['co2']['flow_mol_s'],
        'nitrogen_flow_mol_s': species['nitrogen']['flow_mol_s'],
        'energy_flow_w': math.fsum(s['energy_flow_w'] for s in species.values()),
        'entropy_production_w_k': math.fsum(s['entropy_production_w_k'] for s in species.values()),
        'species': species,
    }
