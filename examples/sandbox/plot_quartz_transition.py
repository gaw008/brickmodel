"""Plot the recorded conditional phase-change calorimeter."""
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
    records=[r for r in rows if r['kind'] in ('initial','accepted')];events=[r for r in rows if r['kind']=='phase_event']
    t=[r['time_s'] for r in records];temperature=[r['state']['temperature_k'] for r in records];fraction=[r['state']['beta_fraction'] for r in records]
    transition=rows[0]['settings']['phase_transition']['temperature_k'];scale=p['seconds_per_minute']
    fig,axes=plt.subplots(2,2,figsize=p['size_inches']);fig.suptitle(p['title'],fontsize=16,y=.99)
    fig.text(.5,.945,p['subtitle'],ha='center',fontsize=10,color='#555555')
    axes[0,0].plot([v/scale for v in t],temperature,color=p['color_temperature']);axes[0,0].set(ylabel='Temperature (K)',xlabel='Time (min)',title='Complete 9000 s cycle')
    axes[0,0].axhline(transition,color=p['color_transition'],ls='--',lw=1,label='847 K phase transition');axes[0,0].legend(fontsize=9)
    axes[1,0].plot([v/scale for v in t],fraction,color=p['color_fraction']);axes[1,0].set(ylabel='Beta-quartz fraction',xlabel='Time (min)',ylim=(-.03,1.03),title='Finite latent-heat interval')
    for axis,direction in zip((axes[0,1],axes[1,1]),('heating','cooling'),strict=True):
        selected=[r for r in events if r['direction']==direction];start,end=[r['time_s'] for r in selected]
        axis.plot(t,temperature,color=p['color_temperature']);axis.axhline(transition,color=p['color_transition'],ls='--',lw=1)
        axis.axvspan(start,end,color=p['color_transition'],alpha=.14)
        axis.set(xlim=(start-p['phase_window_padding_s'],end+p['phase_window_padding_s']),
                 ylim=(transition-p['phase_temperature_half_window_k'],transition+p['phase_temperature_half_window_k']),
                 xlabel='Time (s)',ylabel='Temperature (K)',title=f'{direction.capitalize()}: plateau {end-start:.6f} s')
    for axis in axes.flat:axis.grid(alpha=.2);axis.spines[['top','right']].set_visible(False)
    fig.tight_layout(rect=(0,0,1,.925));fig.savefig(root/p['output'],dpi=p['dpi']);plt.close(fig)


if __name__=='__main__':main()
