"""Plot the recorded closed-mixture cycle without running a solver."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    with (root/settings['trajectory']).open() as stream:
        header=json.loads(next(stream));rows=[r for line in stream if (r:=json.loads(line))['kind'] in ('initial','sample')]
    config=header['parameters'];scale=settings['time_display_seconds_per_hour'];zero=settings['temperature_reference_celsius_zero_k']
    time=np.array([r['time_s']/scale for r in rows]);values=np.array([r['values'] for r in rows]);states=[r['state'] for r in rows]
    series=lambda key:np.array([s[key] for s in states])
    figure=settings['figure'];fig,axes=plt.subplots(2,3,figsize=(figure['width_inches'],figure['height_inches']),layout='constrained')
    ax=axes[0,0];ax.plot(time,series('temperature_k')-zero,label='Mixture',color='#a64b26')
    knots=[p['start_s']/scale for p in config['wall_program']]+[config['wall_program'][-1]['end_s']/scale]
    wall=[p['temperature_k']-zero for p in config['wall_program']]+[config['wall_program'][-1]['temperature_k']-zero]
    ax.step(knots,wall,where='post',ls='--',label='Thermal reservoir',color='#8c939e')
    ax.set_ylabel('Temperature (°C)');ax.legend(fontsize=8)
    ax=axes[0,1]
    for key,label in [('calcite_mol','CaCO3'),('lime_mol','CaO'),('co2_mol','Retained CO2')]:ax.plot(time,series(key),label=label)
    ax.set_ylabel('Amount (mol)');ax.legend(fontsize=8)
    ax=axes[0,2];ax.plot(time,series('co2_partial_pressure_pa')/settings['pressure_pa_per_bar'],label='CO2 partial pressure')
    ax.set_ylabel('Pressure (bar)');ax.legend(fontsize=8)
    ax=axes[1,0];kj=header['affinity_parameters']['joules_per_kilojoule']
    ax.plot(time,values[:,1]/kj,label='External heat in');ax.plot(time,(values[:,0]-values[0,0])/kj,ls='--',label='Total enthalpy change')
    ax.set_ylabel('Energy (kJ)');ax.legend(fontsize=8)
    ax=axes[1,1];entropy=series('entropy_j_k')
    ax.plot(time,entropy-entropy[0]-values[:,2],label='Mixture + reservoir entropy')
    ax.plot(time,values[:,3],ls='--',label='Integrated production');ax.set_ylabel('Entropy (J/K)');ax.legend(fontsize=8)
    ax=axes[1,2];ax.plot(time,series('gas_occupied_volume_m3')*settings['gas_volume_litres_per_m3'],label='Gas occupied volume only')
    ax.set_ylabel('Gas volume (L)');ax.legend(fontsize=8)
    for ax in axes.flat:ax.set_xlabel('Time (h)');ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.suptitle(settings['plot_title'],fontsize=12);fig.savefig(root/figure['filename'],dpi=figure['dpi']);plt.close(fig)
    print(json.dumps({'figure':figure['filename'],'observations':len(rows),'matplotlib_version':matplotlib.__version__}))


if __name__=='__main__':main()
