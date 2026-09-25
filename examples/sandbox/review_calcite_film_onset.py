"""Compare frozen source equilibrium with separately digitized film onset data."""
import argparse
from itertools import product
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from calcite_rigid_setup import build_rigid
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture


def coordinate(pixel,ticks):
    (p0,x0),(p1,x1)=ticks
    return x0+(pixel-p0)*(x1-x0)/(p1-p0)


def reading_interval(pixel,ticks,center_error,axis_error):
    return minmax([coordinate(pixel+dc,[[ticks[0][0]+a,ticks[0][1]],[ticks[1][0]+b,ticks[1][1]]])
        for dc,a,b in product((-center_error,center_error),(-axis_error,axis_error),(-axis_error,axis_error))])


def minmax(values):return [min(values),max(values)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    config=json.loads((root/settings['model_parameters']).read_text());reaction,nitrogen,affinity,source,facts,nsource,volume=build_rigid(root,config)
    model=RigidCalciteMixture(reaction,nitrogen,volume,config,config['cell']);policy=settings['comparison'];reading=settings['digitization']
    total_pressure=settings['conditions']['total_pressure_atm']*policy['pressure_pa_per_atm'];scale=policy['inverse_temperature_axis_scale_k']
    def potential(t,pc,pressure_correction):
        return reaction.standard(t)['reaction']['gibbs_j_mol']-(total_pressure-model.p0)*model.dv*pressure_correction+reaction.gas_constant_j_mol_k*t*math.log(pc/model.p0)
    records=[]
    for pressure,center in zip(settings['pressure_points_atm'],reading['marker_centers_xy'],strict=True):
        x,y=center;value=coordinate(x,reading['x_axis_ticks']);onset=scale/value
        ix=reading_interval(x,reading['x_axis_ticks'],reading['marker_center_allowance_pixels'],reading['axis_position_allowance_pixels'])
        iy=reading_interval(y,reading['y_axis_ticks'],reading['marker_center_allowance_pixels'],reading['axis_position_allowance_pixels'])
        it=minmax([scale/v for v in ix]);pc=pressure*policy['pressure_pa_per_atm']
        temperatures=[brentq(lambda t:potential(t,pc,correction),*policy['evaluation_temperature_interval_k'],
            xtol=policy['root_temperature_absolute_k'],rtol=policy['root_temperature_relative'],maxiter=policy['root_iterations']) for correction in (0.,1.)]
        eq=temperatures[1]
        records.append({'pressure_atm':pressure,'pressure_pa':pc,'marker_center_xy':center,'digitized_onset_temperature_k':onset,
            'onset_pixel_reading_interval_k':it,'log_pressure_pixel_interval':iy,'printed_pressure_in_pixel_interval':iy[0]<=math.log(pressure)<=iy[1],
            'equilibrium_temperature_k':eq,'model_minus_onset_k':eq-onset,'model_minus_reading_interval_k':minmax([eq-t for t in it]),
            'outside_pixel_reading_interval':not it[0]<=eq<=it[1],'solid_pressure_correction_k':temperatures[1]-temperatures[0],
            'root_reaction_potential_residual_j_mol':potential(eq,pc,1.)})
    curve=[]
    for t in np.linspace(*policy['evaluation_temperature_interval_k'],policy['curve_samples']):
        t=float(t);dg=reaction.standard(t)['reaction']['gibbs_j_mol'];pc=model.p0*math.exp(((total_pressure-model.p0)*model.dv-dg)/(reaction.gas_constant_j_mol_k*t))
        curve.append({'temperature_k':t,'co2_pressure_pa':pc,'co2_pressure_atm':pc/policy['pressure_pa_per_atm']})
    result={'settings':settings,'records':records,'source_equilibrium_curve':curve,
        'maximum_absolute_offset_k':max(abs(r['model_minus_onset_k']) for r in records),
        'mean_absolute_offset_k':sum(abs(r['model_minus_onset_k']) for r in records)/len(records),
        'outside_pixel_reading_interval_count':sum(r['outside_pixel_reading_interval'] for r in records),
        'all_pressure_labels_match_reading':all(r['printed_pressure_in_pixel_interval'] for r in records),
        'formal_material_pass':None,'material_qualified':False,'training_eligible':False,
        'scope':'Independent finite-ramp experimental onset comparison, no thermochemical fitting; pixel intervals are not physical uncertainty.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
    print(json.dumps({k:result[k] for k in ('maximum_absolute_offset_k','mean_absolute_offset_k','outside_pixel_reading_interval_count','all_pressure_labels_match_reading','formal_material_pass')}))


if __name__=='__main__':main()
