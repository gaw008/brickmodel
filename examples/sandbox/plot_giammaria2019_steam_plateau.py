"""Plot fixed published rates and conditional open-hold heat requirements."""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    args=parser.parse_args();s=json.loads(args.parameters.read_text())
    result=json.loads((Path(s['output_directory'])/'review.json').read_text())
    rows=result['rate_reproduction']
    fig,axes=plt.subplots(1,2,figsize=(s['figure']['width_inches'],s['figure']['height_inches']))
    x=[r['pressure_bar'] for r in rows]
    axes[0].errorbar(x,[r['observed_rate_mol_s'] for r in rows],
                    xerr=[r['source_pressure_margin_bar'] for r in rows],
                    yerr=[r['source_rate_margin_mol_s'] for r in rows],fmt='o',
                    color='black',markersize=3,label='Author data and margins, 590 C')
    axes[0].plot(x,[r['predicted_rate_mol_s'] for r in rows],label='Printed nominal parameters')
    axes[0].fill_between(x,[r['parameter_box_rate_bounds'][0] for r in rows],
                        [r['parameter_box_rate_bounds'][1] for r in rows],alpha=.15,
                        label='Printed parameter box (not confidence)')
    axes[0].set(xlabel='Water partial pressure / bar',ylabel='Fixed-specimen rate / mol s^-1',xscale='log',
                title='Source-fit reproduction: 11/13 nominal rectangles')
    axes[0].legend(fontsize=7)
    temperatures=sorted({r['temperature_c'] for r in result['conditional_holds']})
    for t in temperatures:
        selected=[r for r in result['conditional_holds'] if r['temperature_c']==t]
        axes[1].plot([r['water_pressure_bar'] for r in selected],[r['supplied_heat_j'] for r in selected],
                     marker='.',label=f'{t} C')
    axes[1].set(xlabel='Source inlet water partial pressure / bar',ylabel='Required isothermal heat / J',
                xscale='log',title=f"Conditional {s['isothermal_open_hold']['duration_s']} s initial plateau")
    axes[1].legend(fontsize=8)
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle('Giammaria 2019 / thesis 2020: source rates + USGS net-reaction heat\n'
                 'Fixed aged specimen; no independent material or full-transient qualification',fontsize=10)
    fig.tight_layout()
    folder=Path(s['figure_directory']);folder.mkdir(parents=True,exist_ok=True)
    fig.savefig(folder/'source-rate-and-heat.png',dpi=s['figure']['dpi'])
    fig.savefig(folder/'source-rate-and-heat.pdf')


if __name__=='__main__':
    main()
