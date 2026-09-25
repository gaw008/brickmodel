"""Plot complete qualified conditional carbon-gas calorimeter records."""
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
    ax.set(ylabel='Temperature (K)',xlabel='Time (min)',title='Prescribed 2400 s calorimeter');ax.legend(fontsize=9)
    ax=axes[0,1]
    for name in ['C','CO','CO2']:ax.plot(t,[r['state']['amounts_mol'][name]*p['moles_to_millimoles'] for r in data],color=p['species_colors'][name],label=name)
    ax.set(ylabel='Amount (mmol)',xlabel='Time (min)',title='Carbon changes phase / species');ax.legend(fontsize=9)
    ax=axes[1,0];ax.semilogy(t,[r['state']['amounts_mol']['O2'] for r in data],color=p['species_colors']['O2'])
    ax.set(ylabel='Ideal-continuum O2 amount (mol)',xlabel='Time (min)',title='Trace activity; not a molecular-count claim')
    ax=axes[1,1];selected=[r for r in data if r['segment_index']==0];ax.plot([r['state']['temperature_k'] for r in selected],[r['state']['equilibrium_cp_j_k'] for r in selected],color=p['temperature_color'])
    ax.set(ylabel='Equilibrium Cp (J/K)',xlabel='Temperature (K)',title='Heat capacity changes at graphite exhaustion')
    ax=axes[2,0];ax.plot(t,[r['values'][1] for r in data],color=p['energy_color']);ax.set(ylabel='Net heat into mixture (J)',xlabel='Time (min)',title='Formation enthalpy includes reaction energy')
    ax=axes[2,1]
    series=([r['state']['entropy_j_k']-s0 for r in data],[r['values'][2] for r in data],[r['total_entropy_change_j_k'] for r in data])
    for values,label,color in zip(series,['Mixture','Reservoir','Combined'],p['entropy_colors'],strict=True):ax.plot(t,values,label=label,color=color)
    ax.set(ylabel='Entropy change (J/K)',xlabel='Time (min)',title='Positive combined entropy production');ax.legend(fontsize=9)
    for ax in axes.flat:ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(root/p['output'],dpi=p['dpi']);plt.close(fig)


if __name__=='__main__':main()
