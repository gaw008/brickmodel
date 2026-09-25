"""Read the original high-W heat curve and compare the conditional free branch."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_sorption_free_water import RecordedSorptionFreeWater


def number(value):
    return Fraction(int(value['numerator']),int(value['denominator']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();p=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    axes=json.loads((root/p['axis_facts_file']).read_text())['calibration'][p['figure_key']]
    record=json.loads((root/p['sorption_record_file']).read_text());provider=RecordedSorptionFreeWater(record)
    image=Image.open(root/p['image_file']).convert('RGB');half=Fraction(str(p['pixel_half_width']))
    def vertices(axis):
        return [tuple(map(number,pair)) for pair in axes[axis]['feasible_pixel_endpoint_vertices']]
    xphysical=tuple(map(Fraction,axes['x']['physical_endpoints']))
    yphysical=tuple(map(Fraction,axes['y']['physical_endpoints']))
    observations=[]
    for moisture in p['moisture_levels_kg_kg']:
        w=Fraction(str(moisture));fraction=(w-xphysical[0])/(xphysical[1]-xphysical[0])
        xvalues=[left+fraction*(right-left) for left,right in vertices('x')]
        columns=range(math.ceil(min(xvalues)-half),math.floor(max(xvalues)+half)+1)
        pixels=[]
        for x in columns:
            for y in range(p['curve_roi_pixel_rows_inclusive'][0],p['curve_roi_pixel_rows_inclusive'][1]+1):
                rgb=image.getpixel((x,y))
                if list(rgb)!=p['white_rgb'] and rgb[0]==rgb[1]==rgb[2]:
                    pixels.append({'x':x,'y':y,'rgb':list(rgb)})
        ymin,ymax=min(v['y'] for v in pixels)-half,max(v['y'] for v in pixels)+half
        physical=[yphysical[0]+(y-bottom)*(yphysical[1]-yphysical[0])/(top-bottom)
                  for bottom,top in vertices('y') for y in (ymin,ymax)]
        nominal_bottom,nominal_top=map(number,axes['y']['nominal_pixel_endpoints'])
        nominal_y=(ymin+ymax)/2
        nominal=yphysical[0]+(nominal_y-nominal_bottom)*(yphysical[1]-yphysical[0])/(nominal_top-nominal_bottom)
        state=provider.evaluate(p['temperature_k'],moisture)
        predicted=record['reference_ideal_vapor_minus_liquid_enthalpy_j_kg']-state['partial_h_j_mol']/record['water_molar_mass_kg_mol']
        observations.append({'moisture_kg_kg':moisture,'pixel_columns':list(columns),'retained_pixels':pixels,
            'nominal_total_desorption_heat_j_kg_water':float(nominal),
            'digitization_interval_j_kg_water':[float(min(physical)),float(max(physical))],
            'conditional_model_total_heat_j_kg_water':predicted,
            'model_minus_nominal_j_kg_water':predicted-float(nominal),
            'within_original_curve_digitization_interval':min(physical)<=predicted<=max(physical),
            'model_phase':state['branch']})
    result={'parameters':p,'observations':observations,
        'all_within_original_curve_digitization_intervals':all(x['within_original_curve_digitization_interval'] for x in observations),
        'scope':'Original curve intersection readings, not raw experiment markers or experimental confidence intervals. A failure rejects source-curve agreement of this continuation, not thermodynamic consistency or all possible wet models.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'observations':[{k:v for k,v in row.items() if k!='retained_pixels'} for row in observations],
                      'all_within_original_curve_digitization_intervals':result['all_within_original_curve_digitization_intervals']},indent=2))


if __name__=='__main__':
    main()
