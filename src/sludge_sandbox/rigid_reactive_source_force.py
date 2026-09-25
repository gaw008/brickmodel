"""Source-integral evaluation of the existing ideal-gas face forces.

Formation constants cancel algebraically. No mobility, chemical potential,
temperature domain or constitutive law changes in this representation.
"""
import math

from .rigid_reactive_exchange import rigid_face_from_forces


def source_integral_species_force(phase, gas_constant, tl, tr, pl, pr):
    a, b, c, d, e = phase.coefficients
    u = tr-tl
    sl, sr = math.sqrt(tl), math.sqrt(tr)
    dh = u*math.fsum((a, b*(tl+tr)/2, c/(tl*tr),
                     2*d/(sl+sr), e*(tl*tl+tl*tr+tr*tr)/3))
    ds = math.fsum((a*math.log1p(u/tl), u*math.fsum((b,
        c*(tl+tr)/(2*tl*tl*tr*tr), 2*d/((sl+sr)*sl*sr), e*(tl+tr)/2))))
    pressure_difference = pr-pl
    log_pressure_ratio = (math.log1p(pressure_difference/pl)
                          if abs(pressure_difference)<min(pl, pr)
                          else math.log(pr)-math.log(pl))
    return math.fsum((ds, -dh*(tl+tr)/(2*tl*tr), -gas_constant*log_pressure_ratio))


def source_integral_rigid_face(left, right, parameters, cell):
    tl, tr = left['temperature_k'], right['temperature_k']
    r = cell.reaction.gas_constant_j_mol_k
    species = ('co2', 'nitrogen')
    forces = [source_integral_species_force(phase, r, tl, tr,
        left[name+'_partial_pressure_pa'], right[name+'_partial_pressure_pa'])
        for phase, name in zip((cell.gas, cell.nitrogen), species, strict=True)]
    enthalpies = [(left[name+'_partial_enthalpy_j_mol']+right[name+'_partial_enthalpy_j_mol'])/2
                 for name in species]
    return rigid_face_from_forces(left, right, parameters, enthalpies, forces, (tl-tr)/(tl*tr))
