"""Plot saved reactive exchange observations without solver execution."""
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
    time=np.array([row['time_s']/settings['time_display_seconds_per_hour'] for row in rows]);values=np.array([row['values'] for row in rows])
    figure=settings['figure'];fig,axes=plt.subplots(2,2,figsize=(figure['width_inches'],figure['height_inches']),layout='constrained')
    for i,label in enumerate(('Left','Right')):
        axes[0,0].plot(time,[row['states'][i]['temperature_k']-settings['temperature_reference_celsius_zero_k'] for row in rows],label=label)
        axes[0,1].plot(time,[row['states'][i]['calcite_mol'] for row in rows],label=label+' CaCO3')
        axes[0,1].plot(time,[row['states'][i]['carbon_mol'] for row in rows],ls='--',label=label+' total carbon')
    axes[0,0].set_ylabel('Temperature (°C)');axes[0,1].set_ylabel('Amount (mol)')
    ax=axes[1,0];kj=header['affinity_parameters']['joules_per_kilojoule']
    ax.plot(time,values[:,5]/kj,label='Enthalpy transferred L to R')
    ax.plot(time,(values[:,1]+values[:,3]-values[0,1]-values[0,3])/kj,label='Total enthalpy residual',ls='--')
    ax.set_ylabel('Energy (kJ)')
    ax=axes[1,1];entropy=np.array([sum(s['entropy_j_k'] for s in row['states']) for row in rows])
    ax.plot(time,entropy-entropy[0],label='Total entropy increase');ax.plot(time,values[:,6],ls='--',label='Integrated exchange production')
    ax.set_ylabel('Entropy (J/K)')
    for ax in axes.flat:ax.legend(fontsize=8);ax.set_xlabel('Time (h)');ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.suptitle(settings['plot_title'],fontsize=12);fig.savefig(root/figure['filename'],dpi=figure['dpi']);plt.close(fig)
    print(json.dumps({'figure':figure['filename'],'observations':len(rows),'matplotlib_version':matplotlib.__version__}))


if __name__=='__main__':main()
