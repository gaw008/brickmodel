"""Plot public observations and fixed-source model, including invalid source points."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comparison',type=Path,required=True)
    parser.add_argument('--output-directory',type=Path,required=True)
    args = parser.parse_args(); d = json.loads(args.comparison.read_text()); out = args.output_directory
    out.mkdir(parents=True,exist_ok=True)
    fig,axes = plt.subplots(3,4,figsize=(15,10),sharey=True,layout='constrained')
    for ax,run in zip(axes.flat,d['runs'],strict=True):
        rows = run['variants'][0]['points']; valid = [p for p in rows if p['porosity_error_printed']>=0]
        invalid = [p for p in rows if p['porosity_error_printed']<0]
        ax.errorbar([p['time_s']/3600 for p in valid],[p['normalized_porosity'] for p in valid],
            yerr=[p['porosity_error_printed'] for p in valid],fmt='.',markersize=2.5,
            color='#273e52',ecolor='#bbcad3',elinewidth=.55)
        ax.scatter([p['time_s']/3600 for p in invalid],[p['normalized_porosity'] for p in invalid],
            marker='x',color='#a50f15',s=22,zorder=6)
        for variant in run['variants']:
            supported = [p for p in variant['points'] if p['inside_positive_radius_domain']]
            central = variant['settings']['id']=='central-2016'
            ax.plot([p['time_s']/3600 for p in supported],[p['normalized_porosity_prediction'] for p in supported],
                color='#cb4b31' if central else '#bd9f85',lw=1.8 if central else .6,
                alpha=1 if central else .65,zorder=4 if central else 3)
        closed = [p for p in rows if not p['inside_positive_radius_domain']]
        if closed:
            ax.axvspan(closed[0]['time_s']/3600,rows[-1]['time_s']/3600,color='#fae7db',alpha=.4,zorder=0)
        target = run['nominal_temperature_header'].split(':')[-1].strip()
        ax.set_title(f"{run['run_id'][-2:]} | nominal {target} K",fontsize=10)
        ax.set_ylim(-.035,1.08); ax.grid(axis='y',alpha=.18)
        ax.spines[['top','right']].set_visible(False);ax.set_xlabel('Recorded time (hours)',fontsize=9)
    for ax in axes[:,0]:ax.set_ylabel('Porosity / initial porosity')
    fig.suptitle('Vented-pore law vs. public glass sintering data | fixed published inputs, no fitting',fontsize=15)
    fig.legend(handles=[Line2D([0],[0],marker='.',ls='',color='#273e52',label='Data + nonnegative printed errors'),
        Line2D([0],[0],color='#cb4b31',lw=2,label='Central model until finite closure'),
        Line2D([0],[0],color='#bd9f85',label='Separate parameter sensitivities'),
        Line2D([0],[0],marker='x',ls='',color='#a50f15',label='Negative printed error')],
        loc='outside lower center',ncol=2,frameon=False)
    fig.savefig(out/'comparison.png',dpi=150);fig.savefig(out/'comparison.pdf');plt.close(fig)
    fig,ax = plt.subplots(figsize=(9,5.7),layout='constrained')
    for run,color in zip(d['runs'],plt.cm.viridis(np.linspace(.05,.95,len(d['runs']))),strict=True):
        rows = [p for p in run['variants'][0]['points'] if p['capillary_clock']>0]
        ax.scatter([p['capillary_clock'] for p in rows],[p['normalized_porosity'] for p in rows],
                   s=8,alpha=.55,color=color,label=run['run_id'][-2:])
    curve = sorted([p for run in d['runs'] for p in run['variants'][0]['points']
        if p['inside_positive_radius_domain'] and p['capillary_clock']>0],key=lambda p:p['capillary_clock'])
    ax.plot([p['capillary_clock'] for p in curve],[p['normalized_porosity_prediction'] for p in curve],
            c='#bd351f',lw=2,label='Central vented law')
    ax.axvline(d['runs'][0]['variants'][0]['closure_clock'],c='#bd351f',ls='--',lw=1)
    ax.set_xscale('log');ax.set_xlabel('Capillary time: integral[ surface tension / (initial radius * viscosity(T)) dt ]')
    ax.set_ylabel('Porosity / initial porosity');ax.set_ylim(-.035,1.08)
    ax.set_title('Finite closure does not explain the observed nonzero tail')
    ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False);ax.legend(ncol=4,fontsize=8,frameon=False)
    fig.savefig(out/'capillary-collapse.png',dpi=160);fig.savefig(out/'capillary-collapse.pdf')


if __name__=='__main__':
    main()
