"""Exact-binary inventory/U accounting at every saved accepted BDF step.

Uses only recorded conserved states and external integrals. It does not decode
temperature, assert constitutive accuracy, or certify unsaved intermediate time.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    settings = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    results = []
    for name, path in settings['trajectories'].items():
        with (root/path).open() as stream:
            header, initial = json.loads(next(stream)), json.loads(next(stream))
            species = header['parameters']['boundary_program']['values']['species_order']
            labels = species+['U']
            width, cells = len(labels), header['cell_count']
            baseline = [sum(Fraction(p['inventories_mol'][k]) for p in initial['states']) for k in species]
            baseline.append(sum(Fraction(p['internal_energy_j']) for p in initial['states']))
            maxima = [Fraction(0) for _ in labels]
            steps = 0
            for line in stream:
                row = json.loads(line)
                if row['kind'] != 'accepted':
                    continue
                values = row['conserved_state']
                for j in range(width):
                    total = sum(Fraction(values[i*width+j]) for i in range(cells))
                    residual = total-baseline[j]+Fraction(values[cells*width+j])
                    maxima[j] = max(maxima[j], abs(residual))
                steps += 1
            results.append({'name': name, 'trajectory': path, 'accepted_steps': steps,
                'scalar_balances': steps*width,
                'maximum_absolute_residuals': {
                    label: {'value': float(value), 'unit': 'J' if label == 'U' else 'mol',
                            'exact_numerator': value.numerator, 'exact_denominator': value.denominator}
                    for label, value in zip(labels, maxima, strict=True)}})
    result = {'settings': settings, 'results': results,
        'qualification': 'Exact arithmetic on saved binary values, not exactly zero numerical residuals, independent experimental validation, or a continuous-time error bound.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
