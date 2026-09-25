"""Phase-local analytic derivatives of the recorded rigid reactive closure.

Derivatives use conserved coordinates (total carbon, N2, internal energy).
At a phase boundary the selected equilibrium branch supplies its one-sided
derivative; no smoothing or kinetic interpretation is introduced.
"""
import numpy as np
from scipy.sparse import coo_matrix

from .rigid_reactive_exchange import rigid_reactive_face


def inventory_tangent(cell, state):
    t = state['temperature_k']
    g = state['co2_mol']
    n = state['nitrogen_mol']
    vg = state['gas_volume_m3']
    p = state['pressure_pa']
    r = cell.reaction.gas_constant_j_mol_k
    rt = r * t
    du = state['reaction_internal_energy_j_mol']
    ec, en, eu = np.eye(3)

    if state['phase'] == 'coexistence':
        fg = state['reaction_gas_derivative_j_mol2']
        gc = -cell.dv * (rt - p * cell.dv) / (vg * fg)
        gn = cell.dv * rt / (vg * fg)
        gt = du / (t * fg)
    else:
        gc, gn, gt = 1., 0., 0.

    a = cell.reactant.standard(t)
    b = cell.product.standard(t)
    gas = cell.gas.standard(t)
    carrier = cell.nitrogen.standard(t)
    uc = a['enthalpy_j_mol'] - cell.p0 * cell.vc
    ul = b['enthalpy_j_mol'] - cell.p0 * cell.vl
    un = carrier['enthalpy_j_mol'] - rt
    dt = (eu - (uc - ul + du * gc) * ec - (un + du * gn) * en) / state['equilibrium_cv_j_k']
    dg = gc * ec + gn * en + gt * dt
    dvg = cell.dv * (dg - ec)
    dp = p * ((dg + en) / (g + n) + dt / t - dvg / vg)
    dlogc = dg / g + dt / t - dvg / vg
    dlogn = en / n + dt / t - dvg / vg
    dmu_over_t = np.array([
        -gas['enthalpy_j_mol'] * dt / t**2 + r * dlogc,
        -carrier['enthalpy_j_mol'] * dt / t**2 + r * dlogn,
    ])
    inverse = -dt / t**2
    enthalpies = np.array([gas['cp_j_mol_k'] * dt, carrier['cp_j_mol_k'] * dt])
    xc = (n * dg - g * en) / (g + n)**2
    fractions = np.array([xc, -xc])
    return {
        'temperature': dt, 'co2': dg, 'pressure': dp,
        'potential_over_temperature': dmu_over_t,
        'inverse_temperature': inverse, 'enthalpies': enthalpies,
        'fractions': fractions,
        'entropy_hessian': np.vstack((-dmu_over_t, inverse)),
    }


def face_tangents(left, right, left_tangent, right_tangent, parameters, face=None):
    provided_face = face is not None
    if face is None: face = rigid_reactive_face(left, right, parameters)
    h = np.array(face['face_partial_enthalpies_j_mol'])
    x = np.array(face['face_mole_fractions'])
    force = np.array(face['species_forces_j_mol_k'])
    bulk = face['bulk_force_j_mol_k']
    difference = face['counter_force_j_mol_k']
    tl, tr = left['temperature_k'], right['temperature_k']
    inv = (tl-tr)/(tl*tr) if provided_face else 1/tr-1/tl
    lb = parameters['bulk_mobility_mol2_k_j_s']
    ld = parameters['counter_mobility_mol2_k_j_s']
    flows = np.array([face['carbon_flow_mol_s'], face['nitrogen_flow_mol_s']])
    derivatives = []
    for sign, tangent in ((1., left_tangent), (-1., right_tangent)):
        dh = tangent['enthalpies'] / 2
        dx = tangent['fractions'] / 2
        dinv = -sign * tangent['inverse_temperature']
        dforce = sign * tangent['potential_over_temperature'] + dh * inv + h[:, None] * dinv
        dbulk = force @ dx + x @ dforce
        ddifference = dforce[0] - dforce[1]
        dflows = lb * (bulk * dx + x[:, None] * dbulk) + ld * np.array([ddifference, -ddifference])
        dheat = sign * parameters['heat_conductance_w_k'] * tangent['temperature']
        denergy = dheat + flows @ dh + h @ dflows
        dentropy = dheat * inv + face['conductive_heat_w'] * dinv + 2 * lb * bulk * dbulk + 2 * ld * difference * ddifference
        derivatives.append(np.vstack((dflows, denergy, dentropy)))
    return derivatives


def column_jacobian(column, time_s, values):
    states = column.states(values)
    tangents = [inventory_tangent(cell, state) for cell, state in zip(column.cells, states, strict=True)]
    rows, cols, entries = [], [], []
    for i in range(column.count - 1):
        pair = face_tangents(states[i], states[i+1], tangents[i], tangents[i+1], column.face_parameters)
        for side, derivative in enumerate(pair):
            for coordinate in range(3):
                col = 3 * (i + side) + coordinate
                for component in range(3):
                    rate = derivative[component, coordinate]
                    rows.extend((3*i+component, 3*(i+1)+component, 3*column.count+3*i+component))
                    cols.extend((col, col, col))
                    entries.extend((-rate, rate, rate))
                rows.append(len(values)-1); cols.append(col); entries.append(derivative[3, coordinate])
    return coo_matrix((entries, (rows, cols)), shape=(len(values), len(values))).tocsc()
