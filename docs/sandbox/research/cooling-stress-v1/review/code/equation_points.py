"""Exact point arithmetic for the declared equations, not a model trajectory."""
from fractions import Fraction as F
import json
from pathlib import Path


def dense_solve(matrix, rhs):
    augmented = [list(row)+[value] for row, value in zip(matrix, rhs, strict=True)]
    for pivot in range(len(rhs)):
        scale = augmented[pivot][pivot]
        assert scale != 0
        augmented[pivot] = [value/scale for value in augmented[pivot]]
        for row in range(len(rhs)):
            if row != pivot:
                scale = augmented[row][pivot]
                augmented[row] = [a-scale*b for a, b in zip(augmented[row], augmented[pivot], strict=True)]
    return [row[-1] for row in augmented]


def point(M, alpha, C, Tr, area, widths, temperatures, net_heat, interfaces, boundary=None):
    volume = [area*h for h in widths]
    weight = [h/sum(widths) for h in widths]
    mean = sum(w*T for w, T in zip(weight, temperatures, strict=True))
    strain = alpha*(mean-Tr)
    stress = [M*alpha*(mean-T) for T in temperatures]
    b = M*alpha**2
    diagonal = [C-2*b*T for T in temperatures]
    coupling = [2*b*T for T in temperatures]
    assert all(D > 0 for D in diagonal)
    q = [Q/V for Q, V in zip(net_heat, volume, strict=True)]
    mean_rate = sum(w*v/D for w, v, D in zip(weight, q, diagonal, strict=True))/(1+sum(w*c/D for w, c, D in zip(weight, coupling, diagonal, strict=True)))
    rate = [(v-c*mean_rate)/D for v, c, D in zip(q, coupling, diagonal, strict=True)]
    strain_rate = alpha*mean_rate
    matrix = [[(diagonal[i] if i == j else F(0))+coupling[i]*weight[j] for j in range(len(q))] for i in range(len(q))]
    assert all(sum(row) == C for row in matrix)
    assert dense_solve(matrix, q) == rate
    assert sum(w*r for w, r in zip(weight, rate, strict=True)) == mean_rate
    energy = [C*(T-Tr)+M*(strain+alpha*Tr)**2-b*T*T for T in temperatures]
    variance_energy = C*sum(V*(T-Tr) for V, T in zip(volume, temperatures, strict=True))-b*sum(V*(T-mean)**2 for V, T in zip(volume, temperatures, strict=True))
    assert sum(V*u for V, u in zip(volume, energy, strict=True)) == variance_energy
    work = [2*V*s*strain_rate for V, s in zip(volume, stress, strict=True)]
    energy_rate = [V*(D*r+2*M*(strain+alpha*Tr)*strain_rate) for V, D, r in zip(volume, diagonal, rate, strict=True)]
    local_residuals = [udot-Q-P for udot, Q, P in zip(energy_rate, net_heat, work, strict=True)]
    assert all(r == 0 for r in local_residuals) and sum(work) == 0
    assert sum(energy_rate) == sum(net_heat)
    assert any(P != 0 for P in work)  # Omitting local work fails despite zero total work.
    entropy_cells = sum(V*((C/T-2*b)*r+2*M*alpha*strain_rate) for V, T, r in zip(volume, temperatures, rate, strict=True))
    assert entropy_cells == sum(Q/T for Q, T in zip(net_heat, temperatures, strict=True))
    production = sum(G*(temperatures[i]-temperatures[j])**2/(temperatures[i]*temperatures[j]) for i, j, G in interfaces)
    reservoir = F(0)
    if boundary is not None:
        G, Tb = boundary
        Qb = G*(Tb-temperatures[-1])
        reservoir = -Qb/Tb
        production += G*(Tb-temperatures[-1])**2/(Tb*temperatures[-1])
    assert entropy_cells+reservoir == production and production >= 0
    return dict(mean_temperature=mean, mean_rate=mean_rate, temperatures_rate=rate,
        common_strain=strain, common_strain_rate=strain_rate, stresses=stress,
        local_mechanical_power=work, local_energy_residuals=local_residuals,
        energy=variance_energy, entropy_production=production,
        omitted_local_work_residuals=work)


def main():
    two = point(F(10**9), F(1, 10000), F(100000), F(300), F(1),
        [F(1, 10000)]*2, [F(304), F(300)], [F(-4), F(4)], [(0, 1, F(1))])
    delta, V, G, b, C = F(2), F(1, 10000), F(1), F(10), F(100000)
    delta_rate = -2*G/V*delta/(C-2*b*two['mean_temperature'])
    assert two['temperatures_rate'][0]-two['temperatures_rate'][1] == 2*delta_rate
    assert two['mean_rate'] == 2*b/C*delta*delta_rate
    assert two['entropy_production'] == F(1, 5700)
    three = point(F(10), F(1, 100), F(100), F(300), F(2),
        [F(1, 5), F(3, 10), F(1, 2)], [F(310), F(305), F(300)],
        [F(-120), F(45), F(-165)], [(0, 1, F(24)), (1, 2, F(15))],
        boundary=(F(24), F(290)))
    # G= k*A/(h/2), with k=3, A=2, outer h=1/2.
    assert F(3)*F(2)/(F(1, 2)/2) == 24
    output = dict(qualification='manufactured equation point checks only; no implementation imported or trajectory run',
                  two_equal_cells_adiabatic=two, three_unequal_cells_fixed_surface=three)
    raw = json.dumps(output, indent=2, default=lambda value: str(value))+'\n'
    (Path(__file__).parent/'EQUATION_POINTS.json').write_text(raw)
    print(raw, end='')


if __name__ == '__main__':
    main()
