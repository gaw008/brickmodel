"""Independent high-precision reconstruction of prescribed reservoir histories."""
import argparse
import json
from pathlib import Path

from mpmath import mp

from calcite_affinity_setup import from_records
from calcite_closed_setup import nitrogen_from_record
from sludge_sandbox.rigid_reactive_open_column import OpenRigidReactiveColumn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--trajectory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());mp.dps=settings['decimal_digits']
    maxima={k:0. for k in settings['absolute_budgets']};worst={k:None for k in maxima};count=0
    with args.trajectory.open() as stream:
        header=json.loads(next(stream));p=header['settings'];program=p['continuous_boundary_program']
        reaction=from_records(header['affinity_parameters'],header['source'],header['reference_facts'])
        nitrogen=nitrogen_from_record(header['nitrogen_source'])
        model=OpenRigidReactiveColumn(reaction,nitrogen,header['volume_source'],header['model_parameters'],p,
            header['surface_parameters'],header['cell_count'],header['cell_widths_m'])
        cell=model.cells[-1];r=mp.mpf(cell.reaction.gas_constant_j_mol_k);p0=mp.mpf(cell.p0)
        def standard(phase,t):
            a,b,c,d,e=map(mp.mpf,phase.coefficients);t0=mp.mpf(phase.reference_temperature_k)
            h=mp.mpf(phase.reference_enthalpy_j_mol)+a*(t-t0)+b*(t*t-t0*t0)/2+c*(1/t0-1/t)+2*d*(mp.sqrt(t)-mp.sqrt(t0))+e*(t**3-t0**3)/3
            s=mp.mpf(phase.reference_entropy_j_mol_k)+a*mp.log(t/t0)+b*(t-t0)+c*(1/t0**2-1/t**2)/2+2*d*(1/mp.sqrt(t0)-1/mp.sqrt(t))+e*(t*t-t0*t0)/2
            return h,s
        knots=list(map(mp.mpf,program['knot_times_s']));ci=program['species_order'].index('CO2')
        for line in stream:
            row=json.loads(line);terminal=row
            if row['kind'] not in settings['record_kinds']:continue
            i=row['segment_index'];at=mp.mpf(row['time_s']);w=(at-knots[i])/(knots[i+1]-knots[i])
            def interpolate(values):return (1-w)*mp.mpf(values[i])+w*mp.mpf(values[i+1])
            t,pressure,wall=[interpolate(program[k]) for k in ('gas_temperature_k','total_pressure_pa','radiation_temperature_k')]
            x=interpolate([v[ci] for v in program['mole_fractions']]);ref={'temperature_k':t,'pressure_pa':pressure,'co2_mol':x,'nitrogen_mol':1-x}
            for label,name,phase,fraction in [('carbon','co2',cell.gas,x),('nitrogen','nitrogen',cell.nitrogen,1-x)]:
                h,s=standard(phase,t);ref[name+'_partial_pressure_pa']=pressure*fraction
                ref[name+'_partial_enthalpy_j_mol']=h;ref[label+'_chemical_potential_j_mol']=h-t*s+r*t*mp.log(pressure*fraction/p0)
            recorded=row['reservoir'];differences={k:float(abs(mp.mpf(recorded[k])-value)) for k,value in ref.items()}
            surface=header['surface_parameters'];radiation=surface['radiation']
            q=mp.mpf(surface['area_m2'])*mp.mpf(radiation['emissivity'])*mp.mpf(radiation['stefan_boltzmann_w_m2_k4'])*(wall**4-mp.mpf(row['contact']['surface']['temperature_k'])**4)
            differences['radiation_in_w']=float(abs(q-mp.mpf(row['contact']['radiation_in_w'])))
            for key,error in differences.items():
                if error>maxima[key]:maxima[key]=error;worst[key]={'time_s':row['time_s'],'segment_index':i,'kind':row['kind']}
            count+=1
    flags={key:value<=settings['absolute_budgets'][key] for key,value in maxima.items()}
    flags['completed']=terminal['kind']=='summary' and terminal['status']=='completed'
    result={'settings':settings,'trajectory':str(args.trajectory),'observations':count,'maximum_absolute_differences':maxima,
        'worst_observations':worst,'within_budgets':flags,'all_requested_budgets_met':all(flags.values()),
        'material_qualified':False,'training_eligible':False,
        'scope':'Every requested recorded reservoir and radiation flux reconstructed from absolute time, independent affine arithmetic and source h/s polynomials at high precision. No measured schedule or actual kiln accuracy.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'observations':count,'within_budgets':flags}),flush=True)


if __name__=='__main__':main()
