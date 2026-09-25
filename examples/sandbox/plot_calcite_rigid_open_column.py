"""Visualize finite-volume heating, phase redistribution and exterior accounts."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent;settings = json.loads(args.parameters.read_text());rows = []
    with (root/settings['trajectory']).open() as stream:
        header = json.loads(next(stream))
        for line in stream:
            row = json.loads(line)
            if row['kind'] in ('initial','sample'):rows.append(row)
    times = np.array([r['time_s'] for r in rows]);n = header['cell_count'];base = 3*n
    temperature = np.array([[s['temperature_k'] for s in r['states']] for r in rows])
    pressure = np.array([[s['pressure_pa'] for s in r['states']] for r in rows])
    lime = np.array([[s['lime_mol']/(s['lime_mol']+s['calcite_mol']) for s in r['states']] for r in rows])
    values = np.array([r['values'] for r in rows]);ledger = values[:,base:]
    energy = values[:,:base].reshape(len(rows),n,3)[:,:,2].sum(axis=1)
    entropy = np.array([sum(s['entropy_j_k'] for s in r['states']) for r in rows])
    x = (np.arange(n)+.5)*header['cell_width_m']*settings['millimetres_per_metre']
    style = settings['figure'];fig,axes = plt.subplots(3,2,figsize=(style['width_inches'],style['height_inches']),layout='constrained')
    for t in settings['profile_times_s']:
        index = list(times).index(t)
        axes[0,0].plot(x,temperature[index],marker='o',label=f'{t:g} s')
        axes[1,0].plot(x,lime[index],marker='o',label=f'{t:g} s')
    axes[0,0].set(xlabel='Position (mm)',ylabel='Temperature (K)',title='Cell centers; heating through the right surface')
    axes[1,0].set(xlabel='Position (mm)',ylabel='CaO / total Ca (mol/mol)',title='Equilibrium reaction distribution')
    mesh = axes[0,1].pcolormesh(x,times,temperature,shading='nearest',cmap='coolwarm');fig.colorbar(mesh,ax=axes[0,1])
    axes[0,1].set(xlabel='Position (mm)',ylabel='Time (s)',title='Temperature history (K)')
    axes[1,1].plot(times,pressure.min(axis=1),label='Minimum cell');axes[1,1].plot(times,pressure.max(axis=1),label='Maximum cell')
    axes[1,1].plot(times,[r['contact']['surface']['pressure_pa'] for r in rows],'--',label='Massless surface')
    axes[1,1].set(xlabel='Time (s)',ylabel='Pressure (Pa)',yscale='log',title='Recorded pressure feedback')
    axes[2,0].plot(times,ledger[:,6],label='Radiation in');axes[2,0].plot(times,-ledger[:,5],label='Exterior gas energy in')
    axes[2,0].plot(times,energy-energy[0],'--',label='Total cell energy change')
    axes[2,0].set(xlabel='Time (s)',ylabel='Energy (J)',title='Single exterior energy account')
    axes[2,1].plot(times,entropy-entropy[0]+ledger[:,7]+ledger[:,8],label='Cells + reservoirs entropy change')
    axes[2,1].plot(times,ledger[:,9],'--',label='Integrated entropy production')
    axes[2,1].set(xlabel='Time (s)',ylabel='Entropy (J/K)',title='Internal faces and both reservoirs included')
    for i,ax in enumerate(axes.flat):
        ax.grid(alpha=style['grid_alpha'])
        if i!=1:ax.legend(fontsize=style['legend_font_size'])
    fig.suptitle(settings['title'],fontsize=style['title_font_size']);fig.savefig(root/style['filename'],dpi=style['dpi']);plt.close(fig)
    output = {'settings':settings,'observations':len(rows),'cell_count':n,'matplotlib_version':matplotlib.__version__,
        'maximum_recorded_temperature_span_k':float(np.max(np.ptp(temperature,axis=1))),
        'temperature_range_k':[float(temperature.min()),float(temperature.max())],
        'pressure_range_pa':[float(pressure.min()),float(pressure.max())],
        'maximum_lime_fraction':float(lime.max()),'final_temperatures_k':temperature[-1].tolist(),'final_lime_fractions':lime[-1].tolist(),
        'material_qualified':False,'training_eligible':False,'scope':'Common recorded observations, not continuous extrema or material predictions.'}
    with (root/settings['observations_output']).open('x') as stream:
        json.dump(output,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(output))


if __name__=='__main__':
    main()
