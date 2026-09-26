"""Show source observations and a conditional rate-form diagnostic, without fitting."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    args = parser.parse_args()
    s = json.loads(args.parameters.read_text())
    out = Path(s['output_directory'])
    result = json.loads((out / 'review.json').read_text())
    with (out / 'observations.csv').open() as stream:
        records = list(csv.DictReader(stream))
    fig, axes = plt.subplots(2,2,figsize=(s['figure']['width_inches'],s['figure']['height_inches']))
    for j, atmosphere in enumerate(s['sheets'].values()):
        for curve in result['curves']:
            if curve['atmosphere'] != atmosphere:
                continue
            rows = [r for r in records if r['atmosphere']==atmosphere and int(r['cycle'])==curve['cycle']]
            label = f"Cycle {curve['cycle']}"
            axes[0,j].plot([float(r['time_s']) for r in rows],
                           [float(r['uptake_g_co2_per_g_sorbent']) for r in rows], label=label)
            rates = curve['conditional_f1_interval_rates']
            axes[1,j].plot([(r['start_s']+r['end_s'])/2 for r in rates],
                           [r['conditional_interval_f1_rate_per_s'] for r in rates],marker='o',label=label)
        axes[0,j].axvline(s['source_sorption_end_s'],color='gray',linestyle=':',label='Nominal gas switch')
        axes[0,j].set(title=atmosphere.replace('_',' '),xlabel='Recorded time / s',
                       ylabel='Recorded CO2 uptake / (g per g sorbent)')
        axes[0,j].legend(fontsize=8)
        axes[1,j].set(xlabel='Rate-window midpoint / s',ylabel='Conditional F1 interval k / s^-1',yscale='log')
        axes[1,j].grid(alpha=.25)
    fig.suptitle('Donat & Mueller 2025: normalized TGA observations\n'
                 'Interval F1 diagnostic uses approximate source capacity 0.77 g/g; no fitted kinetics')
    fig.tight_layout()
    destination = Path(s['figure_directory'])/'recorded-carbonation'
    fig.savefig(destination.with_suffix('.png'),dpi=s['figure']['dpi'])
    fig.savefig(destination.with_suffix('.pdf'))


if __name__ == '__main__':
    main()
