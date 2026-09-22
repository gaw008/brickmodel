"""Derive bounded product accounting from ENEA's reported tables and bars.

Intervals are printed spreads and analyst raster envelopes, not confidence
intervals. No yield renormalization, molecular products, kinetic constants or
unmeasured aqueous/char compositions are supplied.
"""
import argparse
from fractions import Fraction
from itertools import product
import json
from pathlib import Path

def number(value):
    return Fraction(str(value))


def printed_interval(record):
    center=number(record['nominal'])
    width=number(record['printed_plus_minus'])
    return center-width,center+width


def serial(value):
    if isinstance(value,Fraction):
        return {'numerator':value.numerator,'denominator':value.denominator,'decimal':float(value)}
    raise TypeError(type(value).__name__)


def extract_pixels(config, root):
    """Preparation only: read the locally acquired original embedded figure."""
    import numpy as np
    from PIL import Image

    figure = config['figure']
    pixels = np.array(Image.open(root/figure['image']).convert('RGB'))
    x0,y0,x1,y1 = figure['plot_bounds_xyxy']
    picture = pixels[y0:y1,x0:x1]
    records = []
    for series in figure['series']:
        mask = np.all(picture == np.array(series['rgb']), axis=2)
        occupied = np.where(mask.any(axis=0))[0]
        groups = np.split(occupied, np.where(np.diff(occupied)>1)[0]+1)
        for name,columns in zip(figure['product_order'], groups, strict=True):
            left,right = int(columns[0]+x0),int(columns[-1]+x0)
            top = int(np.where(mask[:,columns].any(axis=1))[0][0]+y0)
            center = (left+right)//2
            half = figure['error_bar_center_half_width_px']
            radius = figure['error_bar_search_radius_px']
            error_pixels = pixels[top-radius:top+radius+1,center-half:center+half+1]
            gray = ((error_pixels[:,:,0] == error_pixels[:,:,1]) &
                    (error_pixels[:,:,1] == error_pixels[:,:,2]) &
                    (error_pixels[:,:,0] < figure['gray_threshold']))
            gray_rows = np.where(gray.any(axis=1))[0]
            records.append({'temperature_C':series['temperature_C'], 'product':name,
                'native_bar_bounds_px':[left,top,right,figure['axis']['low_y_px']],
                'error_extent_y_px':[int(gray_rows.min()+top-radius),int(gray_rows.max()+top-radius)]})
    return {'source':config['source'], 'figure_policy':figure, 'bar_pixels':records,
            'classification':'digitized_source_coordinates_not_measured_precision'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',required=True,type=Path)
    parser.add_argument('--mode',required=True,choices=('extract','account'))
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    config=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    if args.mode == 'extract':
        with args.output.open('x') as stream:
            json.dump(extract_pixels(config,root),stream,indent=2,allow_nan=False)
            stream.write('\n')
        return
    source_pixels=json.loads((root/config['source_bar_pixels_file']).read_text())
    figure=config['figure'];axis=figure['axis']
    baseline,upper=axis['low_y_px'],axis['high_y_px']
    low_value,high_value=number(axis['low_value_wt_percent']),number(axis['high_value_wt_percent'])
    def coordinate(y,zero=baseline,top=upper):
        return low_value+(high_value-low_value)*Fraction(zero-y,zero-top)
    def envelope(top,bottom):
        anchor=axis['anchor_read_half_width_px'];edge=figure['bar_edge_read_half_width_px']
        values=[coordinate(y,z,u) for y,z,u in product((top-edge,bottom+edge),(baseline-anchor,baseline+anchor),(upper-anchor,upper+anchor))]
        return min(values),max(values)
    yields=[]
    for row in source_pixels['bar_pixels']:
        top=row['native_bar_bounds_px'][1]
        bounds=envelope(*row['error_extent_y_px'])
        yields.append({**row,'classification':'digitized_reported_product_yield',
            'nominal_wt_percent':coordinate(top),'printed_error_with_read_envelope_wt_percent':bounds,
            'bar_only_read_envelope_wt_percent':envelope(top,top)})
    accounting=[]
    for series in figure['series']:
        temp=series['temperature_C'];group=[r for r in yields if r['temperature_C']==temp]
        oil=next(r for r in group if r['product']=='bio_oil')
        y=oil['nominal_wt_percent']/100;yl,yu=(v/100 for v in oil['printed_error_with_read_envelope_wt_percent'])
        element_records=[]
        for element in config['accounting']['elements_for_feed_remainder']:
            f=config['feed_printed_wt_percent'][element];o=config['oil_printed_wt_percent'][str(temp)][element]
            fl,fu=(v/100 for v in printed_interval(f));ol,ou=(v/100 for v in printed_interval(o))
            recovered=y*number(o['nominal'])/100
            lo,hi=yl*ol,yu*ou
            element_records.append({'element':element,'bio_oil_element_kg_per_nominal_feed_kg':recovered,
                'bio_oil_element_outer_envelope_kg_per_kg':[lo,hi],
                'aggregate_unassigned_element_kg_per_kg':number(f['nominal'])/100-recovered,
                'aggregate_unassigned_outer_envelope_kg_per_kg':[fl-hi,fu-lo],
                'allocation_to_char_gas_aqueous_and_unrecovered':None})
        total=sum(r['nominal_wt_percent'] for r in group)
        total_bounds=[sum(r['printed_error_with_read_envelope_wt_percent'][i] for r in group) for i in (0,1)]
        lhv=config['oil_LHV_MJ_kg']['reported_range']
        accounting.append({'temperature_C':temp,'sum_reported_product_yields_wt_percent':total,
            'reported_product_sum_outer_envelope_wt_percent':total_bounds,'nominal_mass_remainder_wt_percent':100-total,
            'oil_LHV_content_outer_envelope_MJ_per_nominal_feed_kg':[yl*number(lhv[0]),yu*number(lhv[1])],
            'elements':element_records})
    sums={name:sum(number(config['feed_printed_wt_percent'][k]['nominal']) for k in keys)
        for name,keys in {'proximate_wt_percent':['moisture','volatile_matter','fixed_carbon','ash'],
                         'CHONS_plus_ash_plus_Cl_wt_percent':['C','H','N','S','O','ash','Cl']}.items()}
    sums['oil_CHONS_wt_percent']={t:sum(number(r['nominal']) for r in elements.values())
        for t,elements in config['oil_printed_wt_percent'].items()}
    result={'settings':config,'source_pixel_record':source_pixels,'yields':yields,'accounting':accounting,
        'unadjusted_printed_composition_sums':sums,
        'qualification':'Conditional source arithmetic. Source normalization and total recovery uncertainty remain unresolved; no dynamic reaction or brick validation.',
        'finite_time_reaction_law':None,'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,default=serial,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'accounting':accounting},default=serial,indent=2))


if __name__=='__main__':
    main()
