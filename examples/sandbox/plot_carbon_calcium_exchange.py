"""Plot recorded reactive exchange, conserved energy and increasing entropy."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;p=json.loads(args.parameters.read_text())
    data=[]
    with (root/p['trajectory']).open() as stream:
        header=json.loads(next(stream))
        for line in stream:
            row=json.loads(line)
            if row['kind'] in ('initial','accepted'):data.append(row)
    t=[r['time_s']/p['seconds_per_minute'] for r in data]
    fig,axes=plt.subplots(3,2,figsize=p['size_inches']);fig.suptitle(p['title'],fontsize=16,y=.99)
    fig.text(.5,.954,p['subtitle'],ha='center',fontsize=10,color='#555555')
    for i,(color,label) in enumerate(zip(p['cell_colors'],p['cell_labels'],strict=True)):
        axes[0,0].plot(t,[r['states'][i]['temperature_k'] for r in data],color=color,label=label)
        axes[0,1].plot(t,[r['states'][i]['pressure_pa']/p['pascals_per_bar'] for r in data],color=color,label=label)
        for name,ls in [('calcite','-'),('C','--')]:
            axes[1,0].plot(t,[r['states'][i]['amounts_mol'][name]*p['moles_to_millimoles'] for r in data],color=color,ls=ls,label=label+': '+{'calcite':'CaCO3','C':'graphite'}[name])
        axes[1,1].plot(t,[r['states'][i]['internal_energy_j']-header['initial_internal_energies_j'][i] for r in data],color=color,label=label)
    for index,(label,color) in enumerate(zip(['C atoms','O atoms','N2 molecules'],p['element_colors'],strict=True)):
        axes[2,0].plot(t,[(r['values'][4+index]-data[0]['values'][4+index])*p['moles_to_millimoles'] for r in data],color=color,label=label)
    s0=sum(s['entropy_j_k'] for s in data[0]['states'])
    axes[2,1].plot(t,[sum(s['entropy_j_k'] for s in r['states'])-s0 for r in data],color=p['cell_colors'][0],label='Source entropy change')
    axes[2,1].plot(t,[r['values'][-1] for r in data],color=p['cell_colors'][1],ls='--',label='Integrated entropy production')
    panels=[('Temperature (K)','Thermal relaxation'),('Pressure (bar)','Pressure and composition evolve together'),
            ('Solid amount (mmol)','Local equilibrium shifts the solid phases'),('Internal-energy change (J)','Energy stays within the closed pair'),
            ('Inventory gained by cool cell (mmol)','Gas transfers elemental inventories'),('Entropy increase (J/K)','Independent entropy accounting')]
    for ax,(ylabel,title) in zip(axes.flat,panels,strict=True):
        ax.set(xlabel='Time (min)',ylabel=ylabel,title=title);ax.legend(fontsize=8);ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(root/p['output'],dpi=p['dpi']);plt.close(fig)


if __name__=='__main__':main()
