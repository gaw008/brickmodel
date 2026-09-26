"""Plot the declared virtual gas-transfer and shrinking-pore trajectory."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    with (root/p['trajectory']).open() as stream:
        header = json.loads(next(stream))
        rows = [json.loads(line) for line in stream]
    samples = [r for r in rows if r['kind'] in ('initial','sample')]
    t = np.array([r['time_s'] for r in samples]);s = [r['state'] for r in samples]
    fig,axes = plt.subplots(2,2,figsize=p['figure_size_inches'],layout='constrained')
    radii = np.array([r['radius_m'] for r in s])
    axes[0,0].plot(t,radii/p['radius_units_m'],color='#235789')
    axes[0,0].set_ylabel('Pore radius (micrometres)')
    for field,label,color in [('pore_temperature_k','Pore + matrix','#235789'),
                              ('reservoir_temperature_k','Rigid reservoir + body','#d1495b')]:
        axes[0,1].plot(t,[r[field] for r in s],label=label,color=color)
    axes[0,1].set_ylabel('Temperature (K)');axes[0,1].legend(frameon=False)
    for index,label,color in [(0,'Pore gas','#235789'),(1,'Reservoir gas','#d1495b')]:
        axes[1,0].plot(t,[r['gases'][index]['pressure_pa']/p['pressure_units_pa'] for r in s],label=label,color=color)
    model = header['settings']['model']
    equilibrium = (model['outside_pressure_pa']+2*model['surface_tension_n_m']/radii)/p['pressure_units_pa']
    axes[1,0].plot(t,equilibrium,linestyle=':',color='#555555',label='Mechanical equilibrium pressure')
    axes[1,0].set_ylabel('Pressure (kPa)');axes[1,0].legend(frameon=False,fontsize=8)
    for field,label,color in [('pore_amount_mol','Pore N2','#235789'),('reservoir_amount_mol','Reservoir N2','#d1495b')]:
        axes[1,1].plot(t,[r[field]/p['amount_units_mol'] for r in s],label=label,color=color)
    axes[1,1].set_ylabel('Gas inventory (pmol)');axes[1,1].legend(frameon=False)
    for ax in axes.flat:
        ax.set_xlabel('Time (s)');ax.grid(alpha=.2)
        for segment in header['case']['segments'][:-1]:ax.axvline(segment['end_time_s'],color='#aaaaaa',linestyle='--',linewidth=.7)
    fig.suptitle('Virtual finite gas exchange and viscous pore motion\nSource thermochemistry; conditional geometry and matrix properties',fontsize=13)
    stem = root/p['output_stem']
    fig.savefig(stem.with_suffix('.png'),dpi=p['dpi']);fig.savefig(stem.with_suffix('.pdf'));plt.close(fig)
    print(json.dumps({'observations':len(samples),'outputs':[str(stem.with_suffix(x)) for x in ['.png','.pdf']]}))


if __name__ == '__main__':
    main()
