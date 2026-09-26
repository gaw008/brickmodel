"""Display the documented heat-capacity versions without selecting a material law."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output-prefix', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    result = json.loads(args.review.read_text())
    fig, axes = plt.subplots(2, 1, figsize=(p['plot']['width_inches'], p['plot']['height_inches']), constrained_layout=True)
    for name, label in [('thesis_calcined', '2008 thesis, printed Eq. 4-2'),
                        ('journal_abstract_calcined', '2011 journal abstract')]:
        rows = result['models'][name]['rows']
        temperature = [row['temperature_c'] for row in rows]
        axes[0].plot(temperature, [row['cp_j_kg_k'] for row in rows], 'o-', label=label)
        axes[1].plot(temperature, [row['relative_enthalpy_j_kg']/1000 for row in rows], 'o-', label=label)
    axes[0].set(xlabel='Temperature / C', ylabel='Cp / J kg^-1 K^-1', title='Printed versions differ; no automatic correction or phase qualification')
    axes[1].set(xlabel='Temperature / C', ylabel='Sensible enthalpy from 40 C / kJ kg^-1', title='Integral of each stated formula; reaction energy is absent')
    for ax in axes:
        ax.legend()
        ax.grid(alpha=.2)
    fig.savefig(args.output_prefix.with_suffix('.png'), dpi=p['plot']['dpi'])
    fig.savefig(args.output_prefix.with_suffix('.pdf'))
    plt.close(fig)


if __name__ == '__main__':
    main()
