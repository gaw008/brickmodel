"""Plot recorded cell profiles and closed-system source U/S residuals."""
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
    args=parser.parse_args();root=args.parameters.resolve().parent;p=json.loads(args.parameters.read_text())
    profiles={};time=[];energy=[];entropy=[]
    with (root/p['trajectory']).open() as stream:
        header=json.loads(next(stream));u0=sum(header['initial_internal_energies_j'])
        for line in stream:
            row=json.loads(line)
            if row['kind']=='initial':s0=sum(s['entropy_j_k'] for s in row['states'])
            if row['kind'] in ('initial','sample') and row['time_s'] in p['profile_times_s']:
                profiles[row['time_s']]=row['states']
            if row['kind'] in ('initial','accepted'):
                time.append(row['time_s']/p['seconds_per_minute'])
                energy.append((sum(s['internal_energy_j'] for s in row['states'])-u0)*p['joules_to_microjoules'])
                entropy.append((sum(s['entropy_j_k'] for s in row['states'])-s0-row['values'][-1])*p['joules_to_nanojoules'])
    edges=np.linspace(0,header['settings']['geometry']['length_m'],header['cell_count']+1)*p['metres_to_millimetres']
    fig,axes=plt.subplots(3,2,figsize=p['size_inches'])
    fig.suptitle(p['title'],fontsize=16,y=.99);fig.text(.5,.955,p['subtitle'],ha='center',fontsize=10,color='#555555')
    for at,color in zip(p['profile_times_s'],p['profile_colors'],strict=True):
        states=profiles[at];label=f'{at:g} s'
        fields=[[s['temperature_k'] for s in states],
                [s['pressure_pa']/p['pascals_per_bar'] for s in states],
                [s['amounts_mol']['lime']/inv['calcium_atoms_mol'] for s,inv in zip(states,header['inventories'],strict=True)],
                [s['amounts_mol']['C']/header['cell_volume_m3'] for s in states]]
        for ax,values in zip(axes[:2].flat,fields,strict=True):ax.stairs(values,edges,baseline=None,color=color,label=label)
    labels=[('Temperature (K)','Temperature profiles'),('Pressure (bar)','Pressure profiles'),
            ('CaO / total Ca (mol/mol)','Local calcium phase fraction'),('Graphite inventory (mol/m³)','Immobile graphite distribution')]
    for ax,(ylabel,title) in zip(axes[:2].flat,labels,strict=True):
        ax.set(xlabel='Position (mm)',ylabel=ylabel,title=title);ax.legend(fontsize=8)
    axes[2,0].plot(time,energy,color=p['residual_color'])
    axes[2,0].set(xlabel='Time (min)',ylabel='Source U drift (µJ)',title='Closed-system energy residual')
    axes[2,1].plot(time,entropy,color=p['residual_color'])
    axes[2,1].set(xlabel='Time (min)',ylabel='Source ΔS − production (nJ/K)',title='Independent entropy residual')
    for ax in axes.flat:ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(root/p['output'],dpi=p['dpi']);plt.close(fig)


if __name__=='__main__':main()
