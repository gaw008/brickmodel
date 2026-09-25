"""Plot recorded reaction-column profiles and frozen spatial-budget ratios."""
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
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text()); time = []; temperatures = []; lime = []
    with (root/settings['trajectory']).open() as stream:
        header = json.loads(next(stream))
        for line in stream:
            row = json.loads(line)
            if row['kind'] not in ('initial', 'sample'):
                continue
            time.append(row['time_s']); temperatures.append([s['temperature_k'] for s in row['states']])
            lime.append([s['lime_mol']/(s['lime_mol']+s['calcite_mol']) for s in row['states']])
    time = np.array(time); temperatures = np.array(temperatures); lime = np.array(lime)
    n = header['cell_count']; length = header['parameters']['domain']['length_m']
    x = (np.arange(n)+.5)*length/n*settings['millimetres_per_metre']
    style = settings['figure']; fig, axes = plt.subplots(2, 2, figsize=(style['width_inches'], style['height_inches']), layout='constrained')
    for t in settings['profile_times_s']:
        index = list(time).index(t)
        axes[0, 0].plot(x, temperatures[index], label=f'{t:g} s')
        axes[1, 0].plot(x, lime[index], label=f'{t:g} s')
    axes[0, 0].set(xlabel='Position (mm)', ylabel='Temperature (K)', title=f'{n} cells: temperature profiles')
    axes[1, 0].set(xlabel='Position (mm)', ylabel='CaO / total Ca (mol/mol)', title='Reaction redistribution; instantaneous local equilibrium')
    for ax in (axes[0, 0], axes[1, 0]):
        ax.legend(fontsize=8, ncol=2); ax.grid(alpha=.2)
    mesh = axes[0, 1].pcolormesh(x, time, temperatures, shading='nearest', cmap='coolwarm')
    axes[0, 1].set(xlabel='Position (mm)', ylabel='Time (s)', title='Temperature history (K)'); fig.colorbar(mesh, ax=axes[0, 1])
    comparison = json.loads((root/settings['comparison']).read_text()); budget = comparison['settings']['budgets']
    records = comparison['space_comparisons']; numbers = [r['cell_counts'][1] for r in records]
    labels = {'mean_temperature_k': 'Mean T', 'cell_average_temperature_k': 'Local cell T', 'mean_pressure_pa': 'Mean P', 'total_lime_mol': 'Total CaO'}
    for key, label in labels.items():
        axes[1, 1].plot(numbers, [r['maximum_differences'][key]/budget['space_'+key] for r in records], marker='o', label=label)
    axes[1, 1].plot(numbers, [r['event_difference_s']/budget['space_event_time_s'] for r in records], marker='o', label='Equalization time')
    axes[1, 1].axhline(1., color='black', linestyle='--', label='Frozen budget')
    axes[1, 1].set(xlabel='Finer cell count in adjacent-mesh comparison', ylabel='Maximum difference / budget',
                    title='All shared observations, including early transient', xscale='log', yscale='log')
    axes[1, 1].legend(fontsize=8); axes[1, 1].grid(alpha=.2)
    fig.suptitle(settings['title'], fontsize=12); fig.savefig(root/style['filename'], dpi=style['dpi']); plt.close(fig)
    print(json.dumps({'figure': style['filename'], 'samples': len(time), 'matplotlib_version': matplotlib.__version__}))


if __name__ == '__main__':
    main()
