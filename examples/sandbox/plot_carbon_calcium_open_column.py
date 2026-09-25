"""Plot recorded spatial reactive states and independently accounted reservoirs."""
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
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    rows = []
    with (root / p['trajectory']).open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['kind'] == 'input':
                header = row
            if row['kind'] in ('initial', 'sample'):
                rows.append(row)
    times = np.array([r['time_s'] for r in rows])
    values = np.array([r['values'] for r in rows])
    count, calcium = header['cell_count'], header['cell_calcium_mol']
    ledgers = values[:, 4*count:]
    fig, axes = plt.subplots(2, 4, figsize=p['figure_inches'], layout='constrained')
    for i in p['cell_indices']:
        position = header['cell_centers_m'][i] * p['length_display_factor']
        label = f"x = {position:g} {p['length_label']}"
        axes[0, 0].plot(times, [r['states'][i]['temperature_k'] for r in rows], label=label)
        axes[0, 1].plot(times, [r['states'][i]['pressure_pa'] * p['pressure_display_factor'] for r in rows], label=label)
        axes[0, 2].plot(times, [r['states'][i]['amounts_mol']['lime'] / calcium for r in rows], label=label)
    axes[0, 0].plot(times, [r['reservoir']['temperature_k'] for r in rows], '--', label='Gas bath')
    axes[0, 0].plot(times, [r['radiation']['reservoir_temperature_k'] for r in rows], ':', label='Radiation source')
    axes[0, 0].set(ylabel='Temperature / K', title='Internal temperature and boundary programs')
    axes[0, 1].plot(times, [r['reservoir']['pressure_pa'] * p['pressure_display_factor'] for r in rows], '--', label='Gas bath')
    axes[0, 1].set(ylabel=p['pressure_label'], title='Internal pressure')
    axes[0, 2].set(ylabel='Lime / total calcium', title='Local equilibrium phase response')
    inventory = values[:, :4*count].reshape(len(rows), count, 4)[:, :, :3].sum(axis=1)
    for i, name in enumerate(p['inventory_labels']):
        axes[0, 3].plot(times, (inventory[:, i] - inventory[0, i]) * p['amount_display_factor'], label=name)
    axes[0, 3].set(ylabel=p['amount_label'], title='Net elemental exchange')
    axes[1, 0].plot(times, [r['contact']['energy_flow_w'] for r in rows], label='Gas and conduction')
    axes[1, 0].plot(times, [r['radiation']['energy_in_w'] for r in rows], label='Radiation')
    axes[1, 0].set(ylabel='Energy input rate / W', title='Independent boundary energy ports')
    axes[1, 1].plot(times, ledgers[:, 0] - ledgers[:, 3], label='Gas and conduction')
    axes[1, 1].plot(times, ledgers[:, 3], label='Radiation')
    axes[1, 1].plot(times, ledgers[:, 0], '--', label='Total')
    axes[1, 1].set(ylabel='Energy input / J', title='Cumulative boundary exchange')
    entropy = np.array([sum(s['entropy_j_k'] for s in r['states']) for r in rows])
    axes[1, 2].plot(times, entropy - entropy[0], label='Column change')
    axes[1, 2].plot(times, ledgers[:, 1], label='Gas bath change')
    axes[1, 2].plot(times, ledgers[:, 4], label='Radiation source change')
    axes[1, 2].plot(times, ledgers[:, 2], '--', label='Total production')
    axes[1, 2].set(ylabel='Entropy / (J/K)', title='All bodies and external reservoirs')
    energy = np.array([sum(s['internal_energy_j'] for s in r['states']) for r in rows])
    axes[1, 3].plot(times, energy - energy[0] - ledgers[:, 0], label='Source U change minus total input')
    axes[1, 3].set(ylabel='Energy residual / J', title='Balance at saved observations')
    for ax in axes.flat:
        ax.set_xlabel('Time / s')
        ax.grid(alpha=p['grid_alpha'])
        ax.legend(fontsize=p['legend_font_size'])
    fig.suptitle(p['title'])
    fig.savefig(root / p['output_png'], dpi=p['dpi'])
    fig.savefig(root / p['output_pdf'])
    plt.close(fig)


if __name__ == '__main__':
    main()
