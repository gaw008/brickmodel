"""Display printed and recalibrated temperature relations with retained deviations."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    s = json.loads(args.parameters.read_text())
    result = json.loads((root / s['output_directory'] / 'review.json').read_text())
    fig, axes = plt.subplots(2, 3, figsize=(s['figure']['width_inches'], s['figure']['height_inches']))
    for column, name in enumerate(['dry', 'wet', 'adsorption']):
        data = result['relations'][name]
        rows = data['rows']
        temperatures = [r['temperature_c'] for r in rows]
        factor = 1e8 if name != 'adsorption' else 1e5
        ax = axes[0, column]
        ax.errorbar(temperatures, [r['value'] * factor for r in rows],
            yerr=[r['margin'] * factor for r in rows], fmt='o', color='#222222', capsize=3, label='Source table + margins')
        ax.plot(temperatures, [r['printed_central_prediction'] * factor for r in rows], '--', color='#c34c40', label='Printed central relation')
        ax.plot(temperatures, [r['reconciled_prediction'] * factor for r in rows], color='#24776c', label='Table recalibration')
        ax.set_title(name.capitalize())
        ax.set_ylabel('Specimen rate (10$^{-8}$ mol/s)' if name != 'adsorption' else 'K (bar$^{-1}$)')
        ax.set_xlabel('Temperature (°C)')
        ax.grid(alpha=.2)
        ax = axes[1, column]
        ax.axhspan(-1, 1, color='#d9e9e2', label='Source table margin')
        ax.axhline(0, color='#777777', lw=.6)
        ax.plot(temperatures, [(r['predicted'] - r['source_value']) / r['source_margin'] for r in data['withheld_table_rows']],
            'o-', color='#a76a24', label='One table row withheld')
        ax.set_ylabel('Residual / source margin')
        ax.set_xlabel('Withheld temperature (°C)')
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=7)
    axes[1, 0].legend(fontsize=7)
    fig.suptitle('Giammaria source temperature consistency\nRecalibration of fitted table values; no independent transient validation', fontsize=12)
    fig.tight_layout()
    out = root / s['figure_directory']
    out.mkdir(parents=True, exist_ok=True)
    for suffix in ['png', 'pdf']:
        fig.savefig(out / ('temperature-relations.' + suffix), dpi=s['figure']['dpi'])


if __name__ == '__main__':
    main()
