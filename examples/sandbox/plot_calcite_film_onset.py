"""Plot a recorded external-observation comparison without changing model data."""
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
    result=json.loads((root/settings['review_file']).read_text());rows=result['records'];curve=result['source_equilibrium_curve'];zero=settings['temperature_celsius_zero_k']
    t=np.array([r['digitized_onset_temperature_k'] for r in rows]);p=np.array([r['pressure_atm'] for r in rows]);pred=np.array([r['equilibrium_temperature_k'] for r in rows])
    intervals=np.array([r['onset_pixel_reading_interval_k'] for r in rows]);err=np.array([t-intervals[:,0],intervals[:,1]-t])
    f=settings['figure'];fig,axes=plt.subplots(1,2,figsize=(f['width_inches'],f['height_inches']),layout='constrained')
    ax=axes[0];ax.plot([r['temperature_k']-zero for r in curve],[r['co2_pressure_atm'] for r in curve],label='Frozen USGS equilibrium',color='#2566a3')
    ax.errorbar(t-zero,p,xerr=err,fmt='o',capsize=3,color='#b44627',label='Published film onset, digitized')
    ax.set_yscale('log');ax.set_xlabel('Temperature (°C)');ax.set_ylabel('CO2 partial pressure (atm)');ax.legend(fontsize=8)
    ax=axes[1];ax.errorbar(p,pred-t,yerr=err[::-1],fmt='o',capsize=3,color='#b44627');ax.axhline(0,color='#79818b',ls='--')
    ax.set_xscale('log');ax.set_xlabel('CO2 partial pressure (atm)');ax.set_ylabel('Equilibrium minus observed onset (K)')
    for ax in axes:ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.suptitle(settings['plot_title'],fontsize=11);fig.savefig(root/f['filename'],dpi=f['dpi']);plt.close(fig)
    print(json.dumps({'figure':f['filename'],'observations':len(rows),'no_material_acceptance_claim':True}))


if __name__=='__main__':main()
