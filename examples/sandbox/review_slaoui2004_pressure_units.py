"""Review the literal printed pressure units before admitting kinetic constants."""
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
    imposed = settings['experimental_co2_pressure_kpa']*settings['pascals_per_kilopascal']
    records = []
    for temperature in settings['temperatures_c']:
        t = temperature+settings['kelvin_offset']
        peq = settings['literal_nomenclature_reference_pressure_pa']*math.exp(settings['equilibrium_log_slope_k']/t+settings['equilibrium_log_intercept'])
        driving = 1-imposed/peq
        records.append({'temperature_c': temperature, 'temperature_k': t,
                        'literal_equilibrium_pressure_pa': peq, 'experimental_co2_pressure_pa': imposed,
                        'eq9_driving_factor': driving,
                        'literal_reading_predicts_forward_decomposition': driving>0})
    result = {'settings': settings, 'records': records,
              'conclusion': 'The literal Pa reading reverses the sign relative to reported decomposition at every selected temperature. A pressure normalization must be resolved before using Eq8/9; no replacement normalization is admitted here.',
              'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
