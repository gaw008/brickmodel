"""Nominal endpoint propagation of published-curve digitization readings.

These are finite readout envelopes, not certified floating-point intervals,
experimental confidence limits or bounds on the real material/model error.
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path

import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent
    settings=json.loads(args.parameters.read_text())
    facts=json.loads((root/settings['source_facts_file']).read_text())
    model=json.loads((root/settings['nominal_sorption_record_file']).read_text())
    number=lambda item:float(Fraction(int(item['numerator']),int(item['denominator'])))
    curves={};source_rows=[]
    for figure,key in [(1,'activity'),(2,'heat')]:
        rows=[]
        for selected in model['source_curves'][key]:
            w=selected['moisture_kg_kg']
            original=next(p for p in facts['observations'] if p['figure']==figure and float(p['requested_moisture_kg_water_per_kg_dry_matter'])==w)
            low,high=map(number,original['digitization_bounds']);nominal=number(original['value'])
            rows.append([w,low,nominal,high])
            source_rows.append({'figure':figure,'moisture_kg_kg':w,'source_status':original['status'],
                'reading_role':original['reading_role'],'nominal':nominal,'digitization_endpoints':[low,high],
                'source_value':original['value'],'source_digitization_bounds':original['digitization_bounds'],
                'experimental_uncertainty':original['experimental_uncertainty'],'unit':original['unit']})
        curves[key]=np.array(rows)
    r,mass,t0,latent=(model[k] for k in ('gas_constant_j_mol_k','water_molar_mass_kg_mol',
        'reference_temperature_k','reference_ideal_vapor_minus_liquid_enthalpy_j_kg'))
    join=model['join']['moisture_kg_kg'];points=[]
    for t in settings['temperatures_k']:
        for w in settings['moisture_kg_kg']:
            anchor=max(w,join);a=curves['activity'];q=curves['heat']
            log_a=[float(np.interp(anchor,a[:,0],np.log(a[:,i]))) for i in (1,2,3)]
            heat=[float(np.interp(anchor,q[:,0],q[:,i])) for i in (1,2,3)]
            dilution=math.log(w/join) if w<join else 0.
            # t<=t0 in this study: mu increases with ln(aw) and decreases
            # with q. Reversing these endpoint pairings would be incorrect.
            mu_low=r*t*(log_a[0]+dilution)+mass*(1-t/t0)*(latent-heat[2])
            mu=r*t*(log_a[1]+dilution)+mass*(1-t/t0)*(latent-heat[1])
            mu_high=r*t*(log_a[2]+dilution)+mass*(1-t/t0)*(latent-heat[0])
            activities=[math.exp(value/(r*t)) for value in (mu_low,mu,mu_high)]
            points.append({'temperature_k':t,'moisture_kg_kg':w,
                'nominal_activity':activities[1],'activity_reading_envelope':[activities[0],activities[2]],
                'relative_activity_deviations':[activities[0]/activities[1]-1,activities[2]/activities[1]-1],
                'nominal_excess_mu_j_mol':mu,'excess_mu_reading_envelope_j_mol':[mu_low,mu_high],
                'nominal_reference_total_desorption_heat_j_kg':heat[1],
                'reference_heat_reading_envelope_j_kg':[heat[0],heat[2]],
                'activity_reconstruction':'declared_low_W_shape' if w<join else 'piecewise_ln_interpolation_of_selected_readings',
                'heat_reconstruction':'declared_constant_low_W_heat' if w<join else 'piecewise_interpolation_of_selected_readings'})
    a,q=curves['activity'],curves['heat'];wr=model['reference_moisture_kg_kg']
    integrate=lambda nodes,column:float(np.trapezoid(nodes[:,column],nodes[:,0]))
    h_low=latent*(join-wr)+integrate(q,1);h_high=latent*(join-wr)+integrate(q,3)
    g_low=-r/mass*t0*float(np.trapezoid(np.log(a[:,3]),a[:,0]))
    g_high=-r/mass*t0*float(np.trapezoid(np.log(a[:,1]),a[:,0]))
    result={'settings':settings,'source_doi':facts['doi'],'source_rows':source_rows,'points':points,
        'join_reference_reading_envelopes':{'h_j_kg_dry':[h_low,h_high],
            'g_at_reference_j_kg_dry':[g_low,g_high],
            's_j_kg_dry_k':[(h_low-g_high)/t0,(h_high-g_low)/t0]},
        'unmeasured_heat_locations_preserved':[p['requested_moisture_kg_water_per_kg_dry_matter'] for p in facts['observations'] if p['figure']==2 and p['status']=='unknown'],
        'limitations':['Readings are intersections of a published continuous curve, not original measured markers.',
            'Only declared interpolation and temperature/low-W assumptions are propagated. Their model error, digitization correlation and experimental uncertainty remain unknown.',
            'Endpoint arithmetic uses nominal log/exp, without certified floating-point interval bounds.',
            'An envelope of individual outputs does not establish thermodynamic admissibility of every jointly perturbed curve.',
            'No bound on real drying time, transport coefficients, hysteresis or brick-material prediction follows.'],
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'selected_330k_points':[p for p in points if p['temperature_k']==330. and p['moisture_kg_kg'] in (.1,.3)],
                      'join_reference_reading_envelopes':result['join_reference_reading_envelopes']},indent=2))


if __name__=='__main__':
    main()
