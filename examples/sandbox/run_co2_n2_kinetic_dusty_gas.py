"""CO2/N2 pore transport at a temperature with a published nonspherical A*."""
import argparse
import json
from pathlib import Path

from run_co2_n2_reference_dusty_gas import reference_properties
from run_dusty_gas_isothermal_column import record_column
from sludge_sandbox.chapman_enskog_dusty_gas import ChapmanEnskogDustyGasColumn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--mesh', required=True)
    parser.add_argument('--tolerance', choices=['base', 'refined'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    properties = reference_properties(p, root)
    properties['mixture_source_settings'] = json.loads((root/p['mixture_viscosity']['source_review_file']).read_text())
    record_column(p, properties, args, ChapmanEnskogDustyGasColumn)


if __name__ == '__main__':
    main()
