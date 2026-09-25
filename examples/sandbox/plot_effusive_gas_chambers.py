"""Plot recorded conditional gas temperatures, pressure, composition and entropy."""
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
    audit=json.loads((root/settings['audit']).read_text());records=[]
    with (root/settings['trajectory']).open() as stream:
        for line in stream:
            row=json.loads(line)
            if row['kind'] not in ('initial','sample'):continue
            records.append({'time_s':row['time_s'],'temperature_k':[s['temperature_k'] for s in row['states']],
                'pressure_pa':[s['pressure_pa'] for s in row['states']],
                'co2_fraction':[s['co2_mol']/(s['co2_mol']+s['nitrogen_mol']) for s in row['states']],
                'total_entropy_j_k':sum(s['entropy_j_k'] for s in row['states'])})
    out={'records':records,'equilibrium':audit['independent_equilibrium'],'material_qualified':False,'training_eligible':False}
    with (root/settings['output_observations']).open('x') as stream:json.dump(out,stream,indent=2);stream.write('\n')
    fig,axes=plt.subplots(2,2,figsize=settings['figure_size_inches'],layout='constrained')
    hours=np.array([r['time_s'] for r in records])/3600
    for ax,key,label in zip(axes.flat[:3],['temperature_k','pressure_pa','co2_fraction'],['Temperature [K]','Pressure [Pa]','CO2 mole fraction'],strict=True):
        values=np.array([r[key] for r in records])
        for i in range(2):ax.plot(hours,values[:,i],label=f'Chamber {i+1}')
        if key in audit['independent_equilibrium']:ax.axhline(audit['independent_equilibrium'][key],ls=':',c='black',label='Total-inventory equilibrium')
        ax.set(xlabel='Time [h]',ylabel=label);ax.grid(alpha=.25);ax.legend(fontsize=8)
    entropy=np.array([r['total_entropy_j_k'] for r in records]);s0=entropy[0]
    ax=axes[1,1];ax.plot(hours,entropy-s0,label='Recorded entropy gain')
    ax.axhline(audit['independent_equilibrium']['S']-s0,ls=':',c='black',label='Independent equilibrium gain')
    ax.set(xlabel='Time [h]',ylabel='Total entropy gain [J/K]');ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.suptitle('Two finite CO2/N2 chambers: conditional collisionless aperture\nSource thermochemistry; virtual geometry; no real-brick qualification',fontsize=12)
    fig.savefig(root/settings['output_figure'],dpi=settings['dpi']);plt.close(fig)
    print(json.dumps({'observations':len(records),'figure':settings['output_figure']}))


if __name__=='__main__':
    main()
