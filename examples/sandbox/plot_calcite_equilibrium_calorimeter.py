"""Plot saved scientific observations; no solver or online inputs."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    with (root/settings['trajectory']).open() as stream:
        header=json.loads(next(stream));rows=[r for line in stream if (r:=json.loads(line))['kind'] in ('initial','sample')]
    config=header['parameters'];scale=settings['time_display_seconds_per_hour'];zero=settings['temperature_reference_celsius_zero_k']
    hours=np.array([r['time_s']/scale for r in rows]);temperature=np.array([r['state']['temperature_k'] for r in rows])-zero
    values=np.array([r['values'] for r in rows]);extent=np.array([r['state']['extent_mol'] for r in rows])
    figure=settings['figure'];fig,axes=plt.subplots(2,2,figsize=(figure['width_inches'],figure['height_inches']),layout='constrained')
    ax=axes[0,0];ax.plot(hours,temperature,label='Solid temperature',color='#a64b26')
    knots=[p['start_s']/scale for p in config['wall_program']]+[config['wall_program'][-1]['end_s']/scale]
    wall=[p['temperature_k']-zero for p in config['wall_program']]+[config['wall_program'][-1]['temperature_k']-zero]
    ax.step(knots,wall,where='post',label='Thermal reservoir',ls='--',color='#8c939e')
    ax.axhline(header['equilibrium_temperature_k']-zero,color='#3b7080',lw=1,label='Nominal equilibrium')
    ax.set_ylabel('Temperature (°C)');ax.legend(fontsize=8)
    ax=axes[0,1];ax.plot(hours,config['initial_calcite_mol']-extent,label='CaCO3');ax.plot(hours,extent,label='CaO')
    ax.plot(hours,values[:,1],label='Net CO2 released',ls='--');ax.set_ylabel('Amount (mol)');ax.legend(fontsize=8)
    ax=axes[1,0];kj=header['affinity_parameters']['joules_per_kilojoule']
    ax.plot(hours,values[:,2]/kj,label='External heat in')
    ax.plot(hours,(values[:,0]-values[0,0])/kj,label='Solid enthalpy change')
    ax.plot(hours,values[:,3]/kj,label='CO2 flow enthalpy out')
    ax.set_ylabel('Cumulative energy (kJ)');ax.legend(fontsize=8)
    ax=axes[1,1];entropy=np.array([r['state']['entropy_j_k'] for r in rows])
    ax.plot(hours,entropy-entropy[0]+values[:,5]-values[:,4],label='Solid + external entropy')
    ax.plot(hours,values[:,6],label='Integrated heat-transfer production',ls='--')
    ax.set_ylabel('Entropy change (J/K)');ax.legend(fontsize=8)
    for ax in axes.flat:
        ax.set_xlabel('Time (h)');ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.suptitle(settings['plot_title'],fontsize=12)
    fig.savefig(root/figure['filename'],dpi=figure['dpi']);plt.close(fig)
    print(json.dumps({'figure':figure['filename'],'observations':len(rows),'matplotlib_version':matplotlib.__version__}))


if __name__=='__main__':main()
