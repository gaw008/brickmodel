"""Plot source thermochemistry, table discrepancies and a conditional rate law."""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    thermal = json.loads((root / p['thermochemistry_review']).read_text())
    kinetics = json.loads((root / p['kinetics_review']).read_text())
    plt.rcParams.update({'font.size': p['font_size']})
    fig, axes = plt.subplots(2, 2, figsize=p['figure_size_inches'], layout='constrained')
    for color, (name, review) in zip(p['colors'], thermal['phase_reviews'].items(), strict=True):
        mass = float(thermal['source']['phases'][name]['molar_mass_g_mol']) / 1000
        axes[0, 0].plot([row['temperature_k'] for row in review['points']],
                       [row['state']['cp_j_mol_k'] / mass for row in review['points']],
                       'o-', color=color, label=name.replace('_', ' '))
    axes[0, 0].set(title='USGS 1995 source heat capacities', xlabel='Temperature (K)', ylabel='Cp (J kg⁻¹ K⁻¹)')
    axes[0, 0].legend(fontsize=p['font_size'] - 1)
    names = ['Andalusite + quartz + steam', 'Mullite + quartz + steam']
    for color, label, (name, review) in zip(p['colors'], names, thermal['reactions'].items()):
        basis = thermal['settings']['reaction_extent_basis_kaolinite_mol'][name]
        axes[0, 1].plot([row['temperature_k'] for row in review['points']],
                       [row['state']['gibbs_j_mol'] / basis / 1000 for row in review['points']],
                       'o-', color=color, label=label)
    axes[0, 1].axhline(0, color='0.5', linewidth=.7)
    axes[0, 1].set(title='Restricted product affinity, p(H₂O) = 1 bar',
                  xlabel='Temperature (K)', ylabel='ΔG (kJ per mol kaolinite)')
    axes[0, 1].legend(fontsize=p['font_size'] - 1)
    table = kinetics['table_arithmetic']['declared_si']['rows']
    x = np.arange(len(table))
    axes[1, 0].plot(x, [row['printed_half_time_min'] for row in table], 'o',
                    color=p['colors'][0], label='Printed table')
    axes[1, 0].plot(x, [row['calculated_half_time_min'] for row in table], 'x',
                    color=p['colors'][1], label='Recalculated, declared SI constants')
    axes[1, 0].set_xticks(x, [row['id'].replace('_clay', '').replace('_', ' ') for row in table],
                         rotation=60, ha='right', fontsize=p['font_size'] - 2)
    axes[1, 0].set(title='1955 half-time table: disagreement retained', ylabel='Half-time at 550°C (min)')
    axes[1, 0].legend(fontsize=p['font_size'] - 1)
    trajectory = kinetics['trajectories']['refined']['observations']
    axes[1, 1].plot([row['time_s'] / 60 for row in trajectory],
                    [row['conversion'] for row in trajectory], color=p['colors'][0], label='Normalized conversion')
    axes[1, 1].set(title='China clay 2: prescribed temperature example',
                  xlabel='Time (min)', ylabel='Normalized dehydroxylation fraction')
    twin = axes[1, 1].twinx()
    program = kinetics['settings']['temperature_program']
    twin.plot(np.array(program['time_s']) / 60, program['temperature_c'], '--',
              color=p['colors'][1], label='Prescribed temperature')
    twin.set_ylabel('Temperature (°C)', color=p['colors'][1])
    fig.suptitle('Source calculations and conditional kinetics — no brick material qualification', fontsize=p['font_size'] + 2)
    for ax in axes.flat:
        ax.grid(alpha=.2)
    output = root / p['output_directory']
    output.mkdir(parents=True, exist_ok=True)
    for suffix in ['png', 'pdf']:
        fig.savefig(output / (p['basename'] + '.' + suffix), dpi=p['raster_dpi'])
    plt.close(fig)


if __name__ == '__main__':
    main()
