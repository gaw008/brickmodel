"""Published finite-rate arithmetic and unresolved mass/mole normalization.

This source review deliberately does not supply a kinetics implementation.
The dimensionful literal exponent is displayed only as an invalid numeric
substitution; the molar-area alternative is an explicitly unconfirmed reading.
"""
import argparse
import json
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    settings = json.loads(args.parameters.read_text())
    constants = settings['constants']
    results = []
    for case in settings['cases']:
        material = settings['materials'][case['material']]
        temperature = case['temperature_c'] + constants['celsius_offset_k']
        rate = material['prefactor'] * math.exp(
            -settings['activation_energy_j_mol']
            / (constants['gas_constant_j_mol_k'] * temperature))
        literal = rate * material['bet_m2_g'] * case['residence_s']
        molar = literal * constants['calcite_molar_mass_g_mol']
        results.append({
            'case': case,
            'temperature_k': temperature,
            'rate_as_printed_mol_m2_s': rate,
            'literal_exponent_numeric_value': literal,
            'literal_exponent_units': 'mol/g; invalid as an exponential argument',
            'invalid_literal_numeric_conversion': -math.expm1(-literal),
            'unconfirmed_pure_calcite_molar_area_m2_mol': (
                material['bet_m2_g'] * constants['calcite_molar_mass_g_mol']),
            'unconfirmed_molar_exponent_dimensionless': molar,
            'unconfirmed_molar_conversion': -math.expm1(-molar),
        })
    result = {
        'settings': settings,
        'arithmetic': results,
        'dimensional_inference': (
            'a1*Sg*time has mol/g using the two printed table units. '
            'Converting area to m2 per mol of reacting carbonate would remove '
            'this dimension; its relation to BET per g of the actual mixed '
            'sample requires the carbonate inventory and authors normalization.'),
        'admission': 'unresolved_source_normalization',
        'material_qualified': False,
        'training_eligible': False,
    }
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
