"""Plot saved source-defined reactive capsule observations without fitting."""
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
    states = [r['state'] for r in rows]
    fig, axes = plt.subplots(2, 3, figsize=p['figure_inches'], layout='constrained')
    axes[0, 0].plot(times, [s['temperature_k'] for s in states], label='Reactive cell')
    axes[0, 0].plot(times, [r['reservoir']['temperature_k'] for r in rows], '--', label='Gas bath')
    axes[0, 0].set(ylabel='Temperature / K', title='Prescribed heating and cooling')
    axes[0, 1].plot(times, [s['pressure_pa'] * p['pressure_display_factor'] for s in states], label='Reactive cell')
    axes[0, 1].plot(times, [r['reservoir']['pressure_pa'] * p['pressure_display_factor'] for r in rows], '--', label='Gas bath')
    axes[0, 1].set(ylabel=p['pressure_label'], title='Pressure response')
    for name in p['solid_order']:
        axes[0, 2].plot(times, [s['amounts_mol'][name] * p['amount_display_factor'] for s in states], label=name)
    axes[0, 2].set(ylabel=p['amount_label'], title='Equilibrium solid inventories')
    for i, name in enumerate(p['inventory_labels']):
        axes[1, 0].plot(times, (values[:, i] - values[0, i]) * p['amount_display_factor'], label=name)
    axes[1, 0].set(ylabel=p['amount_label'], title='Net inventory change through gas exchange')
    entropy = np.array([s['entropy_j_k'] for s in states]) - states[0]['entropy_j_k']
    axes[1, 1].plot(times, entropy, label='Cell entropy change')
    axes[1, 1].plot(times, values[:, 5], label='Bath entropy change')
    axes[1, 1].plot(times, values[:, 6], '--', label='Total production')
    axes[1, 1].set(ylabel='Entropy / (J/K)', title='Cell and external bath accounted separately')
    energy = np.array([s['internal_energy_j'] for s in states]) - states[0]['internal_energy_j']
    axes[1, 2].plot(times, energy - values[:, 4], label='Source U change minus energy input')
    axes[1, 2].set(ylabel='Energy residual / J', title='Numerical balance at saved observations')
    for ax in axes.flat:
        ax.set_xlabel('Time / s')
        ax.grid(alpha=p['grid_alpha'])
        ax.legend(fontsize=p['legend_font_size'])
        for knot in header['settings']['boundary_program']['knot_times_s'][1:-1]:
            ax.axvline(knot, color=p['knot_color'], linewidth=p['knot_linewidth'], alpha=p['knot_alpha'])
    fig.suptitle(p['title'])
    fig.savefig(root / p['output_png'], dpi=p['dpi'])
    fig.savefig(root / p['output_pdf'])
    plt.close(fig)


if __name__ == '__main__':
    main()
