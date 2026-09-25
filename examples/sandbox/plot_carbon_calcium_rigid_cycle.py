"""Plot a rigid reactive calorimeter, pressure and independent heat ledger."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;p=json.loads(args.parameters.read_text())
    with (root/p['trajectory']).open() as stream:rows=[json.loads(line) for line in stream]
    data=[r for r in rows if r['kind'] in ('initial','accepted','boundary_transition')];t=[r['time_s']/p['seconds_per_minute'] for r in data]
    temp=[r['state']['temperature_k'] for r in data];s0=data[0]['state']['entropy_j_k']
    fig,axes=plt.subplots(3,2,figsize=p['size_inches']);fig.suptitle(p['title'],fontsize=16,y=.99)
    fig.text(.5,.954,p['subtitle'],ha='center',fontsize=10,color='#555555')
    ax=axes[0,0];ax.plot(t,temp,color=p['temperature_color'],label='Mixture');ax.plot(t,[r['reservoir_temperature_k'] for r in data],ls='--',color=p['reservoir_color'],label='Reservoir')
    ax.set(ylabel='Temperature (K)',xlabel='Time (min)',title='Finite heat input through reactive intervals');ax.legend(fontsize=9)
    nitrogen=rows[0]['inventory']['nitrogen_molecules_mol']*p['moles_to_millimoles']
    for ax,names,title in [(axes[0,1],['calcite','lime','C'],'Coupled solid inventories'),(axes[1,0],['CO','CO2'],f'Shared gas chemistry; N2 fixed at {nitrogen:g} mmol')]:
        for name in names:ax.plot(t,[r['state']['amounts_mol'][name]*p['moles_to_millimoles'] for r in data],color=p['species_colors'][name],label=p['species_labels'][name])
        ax.set(ylabel='Amount (mmol)',xlabel='Time (min)',title=title);ax.legend(fontsize=9)
    ax=axes[1,1];ax.plot(t,[r['state']['pressure_pa']/p['pascals_per_bar'] for r in data],color=p['pressure_color'])
    ax.set(ylabel='Total pressure (bar)',xlabel='Time (min)',title='Pressure follows fixed volume and changing composition')
    ax=axes[2,0];ax.plot(t,[r['values'][1] for r in data],color=p['energy_color'],label='Integrated heat');ax.plot(t,[r['internal_energy_change_j'] for r in data],ls='--',color=p['temperature_color'],label='Source internal energy change');ax.set(ylabel='Energy change (J)',xlabel='Time (min)',title='Independent heat and source internal-energy ledgers');ax.legend(fontsize=9)
    ax=axes[2,1];series=([r['state']['entropy_j_k']-s0 for r in data],[r['values'][2] for r in data],[r['total_entropy_change_j_k'] for r in data])
    for values,label,color in zip(series,['Mixture','Reservoir','Combined'],p['entropy_colors'],strict=True):ax.plot(t,values,label=label,color=color)
    ax.set(ylabel='Entropy change (J/K)',xlabel='Time (min)',title='Combined entropy increases');ax.legend(fontsize=9)
    for ax in axes.flat:ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(root/p['output'],dpi=p['dpi']);plt.close(fig)


if __name__=='__main__':main()
