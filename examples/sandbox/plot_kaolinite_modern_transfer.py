"""Show published observations and fixed-parameter conditional transfer errors."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output-prefix', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    result = json.loads(args.review.read_text())
    fig, axes = plt.subplots(2, 2, figsize=(p['plot']['width_inches'], p['plot']['height_inches']), constrained_layout=True)
    colors = {row['heating_rate_c_min']: np.array(row['rgb']) / 255 for row in p['curve_colors']}
    for col, specimen in enumerate(p['curve_axes']):
        for review in result['reviews']:
            if review['specimen'] != specimen:
                continue
            rows = review['observations']
            beta = review['heating_rate_c_min']
            color = colors[beta]
            temperature = [row['source_temperature_c'] for row in rows]
            measured = np.array([row['observed_conversion'] for row in rows])
            predicted = np.array([row['predicted_conversion'] for row in rows])
            label = f'{beta} C/min'
            axes[0, col].plot(temperature, measured, 'o-', color=color, markersize=4, linewidth=1, label=label)
            axes[0, col].plot(temperature, predicted, '--', color=color, linewidth=1)
            axes[1, col].plot(measured, predicted-measured, 'o-', color=color, markersize=4, linewidth=1, label=label)
        axes[0, col].set(title=f'{specimen}: source points (solid), F3 prediction (dashed)',
                         xlabel='Temperature / C', ylabel='Normalized conversion alpha')
        axes[1, col].set(title=f'{specimen}: prediction minus observation',
                         xlabel='Observed conversion alpha', ylabel='Conversion difference')
        axes[1, col].axhline(0, color='black', linewidth=.7)
        axes[0, col].legend(fontsize=8)
        axes[1, col].legend(fontsize=8)
        for ax in axes[:, col]:
            ax.grid(alpha=.2)
    fig.suptitle('Polcowñuk Iriarte et al. 2025: fixed 3 C/min parameters\n'
                 'Each target curve supplies its alpha=0.1 initial temperature; digitized data, no refitting', fontsize=12)
    fig.savefig(args.output_prefix.with_suffix('.png'), dpi=p['plot']['dpi'])
    fig.savefig(args.output_prefix.with_suffix('.pdf'))
    plt.close(fig)


if __name__ == '__main__':
    main()
