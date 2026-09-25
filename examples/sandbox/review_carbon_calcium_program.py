"""Independent high-precision interpolation and raw-source bath thermochemistry."""
import argparse
import json
from pathlib import Path

import mpmath as mp

from carbon_calcium_pressure_setup import build
from carbon_calcium_source_audit import SourceState
from sludge_sandbox.carbon_calcium_program_cell import CarbonCalciumProgramCell


def independent_program(program, at):
    knots = list(map(mp.mpf, program['knot_times_s']))
    time = mp.mpf(at)
    index = next(i for i in range(len(knots) - 1) if knots[i] <= time <= knots[i + 1])
    weight = (time - knots[index]) / (knots[index + 1] - knots[index])

    def interpolate(values):
        return (1 - weight) * mp.mpf(values[index]) + weight * mp.mpf(values[index + 1])

    fractions = {name: interpolate([row[i] for row in program['mole_fractions']])
                 for i, name in enumerate(program['species_order'])}
    return interpolate(program['gas_temperature_k']), interpolate(program['total_pressure_pa']), fractions


def independent_thermal(source, temperature, pressure, fractions):
    result = {}
    for name, fraction in fractions.items():
        coefficients, t0, h0, s0 = source.thermal[name]
        a, b, c, d, e = map(mp.mpf, coefficients)
        reference = mp.mpf(t0)
        h = (mp.mpf(h0) + a * (temperature - reference) + b * (temperature**2 - reference**2) / 2
             - c * (1 / temperature - 1 / reference) + 2 * d * (mp.sqrt(temperature) - mp.sqrt(reference))
             + e * (temperature**3 - reference**3) / 3)
        s = (mp.mpf(s0) + a * mp.log(temperature / reference) + b * (temperature - reference)
             - c * (1 / temperature**2 - 1 / reference**2) / 2
             - 2 * d * (1 / mp.sqrt(temperature) - 1 / mp.sqrt(reference))
             + e * (temperature**2 - reference**2) / 2
             - mp.mpf(source.r) * mp.log(pressure / mp.mpf(source.p0) * fraction))
        result[name] = {'h': h, 'mu': h - temperature * s}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    face = json.loads((root / p['exchange_parameters']).read_text())
    rigid = json.loads((root / face['rigid_parameters']).read_text())
    pressure = json.loads((root / rigid['pressure_parameters']).read_text())
    model, sources, _ = build(root, pressure)
    source = SourceState(sources)
    cell = CarbonCalciumProgramCell(model, p, face, rigid['numerics'])
    policy = p['boundary_source_review']
    mp.mp.dps = policy['decimal_precision']
    rows = []
    for at in policy['times_s']:
        actual = cell.reservoir_at(at)
        t, pressure, fractions = independent_program(p['boundary_program'], at)
        reference = independent_thermal(source, t, pressure, fractions)
        errors = {
            'temperature_k': float(abs(mp.mpf(actual['temperature_k']) - t)),
            'pressure_pa': float(abs(mp.mpf(actual['pressure_pa']) - pressure)),
            'mole_fraction': max(float(abs(mp.mpf(actual['mole_fractions'][k]) - v)) for k, v in fractions.items()),
            'enthalpy_j_mol': max(float(abs(mp.mpf(model.phases[k].standard(actual['temperature_k'])['enthalpy_j_mol']) - v['h'])) for k, v in reference.items()),
            'chemical_potential_j_mol': max(float(abs(mp.mpf(actual['chemical_potentials_j_mol'][k]) - v['mu'])) for k, v in reference.items()),
        }
        bounds = {'temperature_k': policy['temperature_budget_k'], 'pressure_pa': policy['pressure_budget_pa'],
            'mole_fraction': policy['mole_fraction_budget'], 'enthalpy_j_mol': policy['enthalpy_budget_j_mol'],
            'chemical_potential_j_mol': policy['chemical_potential_budget_j_mol']}
        flags = {k: value <= bounds[k] for k, value in errors.items()}
        rows.append({'time_s': at, 'recorded_bath': actual,
            'independent_temperature_k': str(t), 'independent_pressure_pa': str(pressure),
            'independent_mole_fractions': {k: str(v) for k, v in fractions.items()},
            'independent_thermochemistry': {k: {q: str(v) for q, v in values.items()} for k, values in reference.items()},
            'errors': errors, 'within_budgets': flags})
    result = {'settings': p, 'source_records': sources, 'observations': rows,
        'all_requested_numerical_budgets_met': all(all(r['within_budgets'].values()) for r in rows),
        'material_qualified': False, 'training_eligible': False,
        'scope': 'Independent affine primitive inputs and source Cp integrals with arbitrary-precision arithmetic; no claim of physical input precision or trajectory qualification.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met'],
                      'maxima': {k: max(r['errors'][k] for r in rows) for k in rows[0]['errors']}}))


if __name__ == '__main__':
    main()
