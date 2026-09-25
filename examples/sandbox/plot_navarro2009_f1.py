"""Show fixed-parameter kinetic reproduction and unresolved time units."""
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
    settings = json.loads(args.parameters.read_text())
    result = json.loads((root/settings['results']).read_text())
    style = settings['figure']
    fig, axes = plt.subplots(1, len(result['records']), figsize=(style['width_inches'], style['height_inches']), sharey=True)
    for ax, record in zip(axes, result['records'], strict=True):
        for curve, color, marker in zip(record['curves'], style['colors'], style['markers'], strict=True):
            rate = curve['heating_rate_k_min']
            ax.plot(curve['temperature_k'], curve['conversion'], color=color, linewidth=style['line_width'], label=f'{rate:g} K/min')
            for sample in result['readings']['samples']:
                if sample['heating_rate_k_min']!=rate: continue
                low, high = sample['temperature_reading_interval_k']
                ylo, yhi = sample['conversion_reading_interval']
                ax.errorbar((low+high)/2, sample['conversion_nominal'], xerr=(high-low)/2,
                            yerr=(yhi-ylo)/2, fmt=marker, color=color,
                            markersize=style['marker_size'], elinewidth=style['error_line_width'])
        ax.set(title=settings['titles'][record['interpretation']], xlabel='Temperature (K)',
               xlim=style['temperature_range_k'], ylim=style['conversion_range'])
        ax.grid(alpha=style['grid_alpha'])
        ax.legend()
    axes[0].set_ylabel('Calcite conversion')
    fig.suptitle('Rodriguez-Navarro et al. 2009: F1 source reproduction')
    fig.text(.5, .02, settings['caption'], ha='center', fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.95))
    fig.savefig(root/settings['output'], dpi=style['dpi'])
    plt.close(fig)


if __name__ == '__main__':
    main()
