"""Render the recorded conditional cycle and export physical extrema."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text());rows = []
    with (root/settings['trajectory']).open() as stream:
        header = json.loads(next(stream))
        for line in stream:
            row = json.loads(line)
            if row['kind'] in ('initial','accepted','boundary_transition'):
                rows.append(row)
    time = np.array([r['time_s'] for r in rows]);states = [r['state'] for r in rows]
    field = lambda key: np.array([s[key] for s in states])
    values = np.array([r['values'] for r in rows]);ca = header['settings']['cell']['calcium_mol']
    surface = np.array([r['contact']['surface']['temperature_k'] for r in rows])
    environment = np.array([r['reservoir']['temperature_k'] for r in rows])
    pressure = field('pressure_pa');lime = field('lime_mol')/ca
    sigma = values[:,12];total_entropy = field('entropy_j_k')-states[0]['entropy_j_k']+values[:,10]+values[:,11]
    style = settings['figure'];fig,axes = plt.subplots(3,2,figsize=(style['width_inches'],style['height_inches']),layout='constrained')
    axes[0,0].plot(time,field('temperature_k'),label='Cell');axes[0,0].plot(time,surface,label='Massless surface')
    axes[0,0].plot(time,environment,'--',label='Gas / radiation reservoirs');axes[0,0].set(ylabel='Temperature (K)',title='Prescribed heating and cooling')
    axes[0,1].plot(time,pressure,label='Cell');axes[0,1].plot(time,[r['reservoir']['pressure_pa'] for r in rows],'--',label='Gas reservoir')
    axes[0,1].set(yscale='log',ylabel='Pressure (Pa)',title='Rigid pore volume and exchange feedback')
    axes[1,0].plot(time,lime,label='CaO / total Ca');axes[1,0].set(ylabel='Molar fraction',title='Instantaneous equilibrium reaction limit')
    for key,label in [('carbon_flow_mol_s','CO2'),('nitrogen_flow_mol_s','N2')]:
        axes[1,1].plot(time,[r['contact']['exterior_face'][key] for r in rows],label=label)
    axes[1,1].set(ylabel='Outward mol/s',title='Gas exchange across exterior face')
    axes[2,0].plot(time,values[:,9],label='Radiation in');axes[2,0].plot(time,-values[:,8],label='Exterior gas energy in')
    axes[2,0].plot(time,values[:,2]-values[0,2],'--',label='Cell internal-energy change')
    axes[2,0].set(ylabel='Energy (J)',title='One formation-energy reference throughout')
    axes[2,1].plot(time,total_entropy,label='Cell + reservoirs entropy change')
    axes[2,1].plot(time,sigma,'--',label='Integrated entropy production')
    axes[2,1].set(ylabel='Entropy (J/K)',title='Complete exterior entropy account')
    for ax in axes.flat:
        ax.set_xlabel('Time (s)');ax.grid(alpha=style['grid_alpha']);ax.legend(fontsize=style['legend_font_size'])
    fig.suptitle(settings['title'],fontsize=style['title_font_size'])
    fig.savefig(root/style['filename'],dpi=style['dpi']);plt.close(fig)
    def extrema(array):
        low,high = int(np.argmin(array)),int(np.argmax(array))
        return {'minimum':float(array[low]),'minimum_time_s':float(time[low]),'maximum':float(array[high]),'maximum_time_s':float(time[high])}
    result = {'settings':settings,'recorded_physical_states':len(rows),
        'temperature_k':extrema(field('temperature_k')),'pressure_pa':extrema(pressure),'lime_fraction':extrema(lime),
        'co2_mol':extrema(field('co2_mol')),'nitrogen_mol':extrema(field('nitrogen_mol')),
        'final_C_N_U':values[-1,:3].tolist(),'final_exterior_ledgers':dict(zip(header['state_order'][6:],values[-1,6:].tolist(),strict=True)),
        'maximum_entropy_ledger_residual_j_k':float(np.max(np.abs(total_entropy-sigma))),
        'material_qualified':False,'training_eligible':False,
        'scope':'Extrema over all recorded accepted states, not continuous-time bounds; virtual geometry and transport, equilibrium reaction, no material kinetics.'}
    with (root/settings['observations_output']).open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'figure':style['filename'],'observations':settings['observations_output'],'matplotlib_version':matplotlib.__version__}))


if __name__=='__main__':
    main()
