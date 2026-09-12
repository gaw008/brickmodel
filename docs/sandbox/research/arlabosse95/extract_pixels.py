"""Original-raster intersection candidates, without smoothing or a physical fit."""
from fractions import Fraction as F
from itertools import combinations, product
from pathlib import Path
import hashlib
import json
import math
import sys

from PIL import Image
import PIL
import numpy as np

ROOT = Path(__file__).resolve().parent
LEVEL_LABELS = ('0.10','0.15','0.20','0.30','0.40','0.50','0.60','0.70','0.80')
LEVELS = tuple(map(F, LEVEL_LABELS))
LEVEL_TEXT = dict(zip(LEVELS, LEVEL_LABELS))
SOURCES = {
    1: ('arlabosse-figure1.gif', '2b412d289852c58ff2e44a67467399dad4be5075543d701a79031a7966f4362d',
        'https://minio.scielo.br/documentstore/1678-4383/mxGLvLxqCvys7VX4DpCyNvM/6d8dcfb6a4b9934e2b5d73607ca3fe16743dda77.gif'),
    2: ('arlabosse-figure2.gif', 'f3526cbd15b416b82ca0421869c4bc83f14f24d10a7a73066e137483af4738e7',
        'https://minio.scielo.br/documentstore/1678-4383/mxGLvLxqCvys7VX4DpCyNvM/c3ab8637e8acb6c1bceeb2e97717df761c5e1ea6.gif'),
}


def encoded(value):
    value=F(value)
    return {'numerator':str(value.numerator),'denominator':str(value.denominator),
            'approximate':float(value)}


def encoded_pair(values):
    return [encoded(v) for v in values]


def ticks(values, groups):
    return tuple((F(v),tuple(g),v) for v,g in zip(values,groups))


FIG1_X=ticks(('0.0','0.2','0.4','0.6','0.8','1.0'),((65,),(148,),(231,),(314,),(397,398),(481,)))
FIG1_Y=ticks(('0.0','0.1','0.2','0.3','0.4','0.5','0.6','0.7','0.8','0.9','1.0'),
    ((244,),(221,),(197,),(173,),(149,150),(126,),(102,),(78,),(54,),(30,31),(7,)))
FIG2_X=ticks(('0.0','0.5','1.0','1.5','2.0','2.5','3.0'),((83,),(150,151),(218,),(285,286),(353,),(420,421),(488,)))
FIG2_Y=ticks(('2.0E+06','2.2E+06','2.4E+06','2.6E+06','2.8E+06','3.0E+06','3.2E+06','3.4E+06','3.6E+06','3.8E+06'),
    ((242,243),(216,),(190,),(164,),(137,138),(111,),(85,),(59,),(32,33),(6,)))


def calibration(entries, raster, axis, stub):
    values=[t[0] for t in entries]
    declared={c for _,centers,_ in entries for c in centers}
    observed=set()
    for center in range(min(declared),max(declared)+1):
        pixels=(raster[center,stub[0]:stub[1]] if axis=='y'
                else raster[stub[0]:stub[1],center])
        if np.any(pixels<255): observed.add(center)
    if observed!=declared:
        raise ValueError('declared_tick_centers_do_not_cover_original_stub_strip')
    constraints=[]
    records=[]
    for value,centers,printed in entries:
        r=(value-values[0])/(values[-1]-values[0])
        lo,hi=F(min(centers))-F(1,2),F(max(centers))+F(1,2)
        for center in centers:
            pixels=(raster[center,stub[0]:stub[1]] if axis=='y'
                    else raster[stub[0]:stub[1],center])
            if not np.all(pixels<255):
                raise ValueError('declared_tick_footprint_not_present')
        constraints.extend(((1-r,r,hi),(-(1-r),-r,-lo)))
        records.append({'printed_label':printed,'numeric_value':encoded(value),'pixel_centers':centers,'pixel_footprint':encoded_pair((lo,hi))})
    vertices=set()
    for (a,b,c),(d,e,f) in combinations(constraints,2):
        determinant=a*e-b*d
        if determinant==0:
            continue
        u,v=(c*e-b*f)/determinant,(a*f-c*d)/determinant
        if all(aa*u+bb*v<=cc for aa,bb,cc in constraints):
            vertices.add((u,v))
    if not vertices:
        raise ValueError('no_affine_axis_compatible_with_full_printed_tick_footprints')
    vertices=tuple(sorted(vertices))
    nominal=tuple(sum((p[i] for p in vertices),F())/len(vertices) for i in (0,1))
    if any((p[1]-p[0])*(nominal[1]-nominal[0])<=0 for p in vertices):
        raise ValueError('axis_direction_not_identified')
    for record,(value,centers,printed) in zip(records,entries):
        r=(value-values[0])/(values[-1]-values[0])
        predicted=(1-r)*nominal[0]+r*nominal[1]
        center=F(min(centers)+max(centers),2)
        record['nominal_position_px']=encoded(predicted)
        record['nominal_minus_stroke_center_px']=encoded(predicted-center)
    return dict(values=(values[0],values[-1]),vertices=vertices,nominal=nominal,records=records,
                stub_axis=axis,stub_region=stub)


def position(axis,value):
    r=(value-axis['values'][0])/(axis['values'][1]-axis['values'][0])
    points=[(1-r)*a+r*b for a,b in axis['vertices']]
    return min(points),max(points)


def inverse(axis,pixel,ends):
    a,b=ends
    return axis['values'][0]+(pixel-a)/(b-a)*(axis['values'][1]-axis['values'][0])


def inverse_bounds(axis,pixels):
    values=[inverse(axis,p,v) for p,v in product(pixels,axis['vertices'])]
    return min(values),max(values)


def footprint_groups(points):
    pending=set(points)
    groups=[]
    while pending:
        front=[pending.pop()]
        group=[]
        while front:
            point=front.pop()
            group.append(point)
            x,y=point
            for xx,yy in product(range(x-1,x+2),range(y-1,y+2)):
                if (xx,yy) in pending:
                    pending.remove((xx,yy));front.append((xx,yy))
        groups.append(sorted(group))
    return groups


def reading(figure,level,raster,axes,grid_rows):
    target_axis=axes['y'] if figure==1 else axes['x']
    output_axis=axes['x'] if figure==1 else axes['y']
    p_lo,p_hi=position(target_axis,level)
    indices=list(range(math.ceil(p_lo-F(1,2)),math.floor(p_hi+F(1,2))+1))
    points=[]
    if figure==1:
        for y in indices:
            points.extend((x,y) for x in range(67,481) if raster[y,x]<255)
    else:
        for x in indices:
            points.extend((x,y) for y in range(7,242) if y not in grid_rows and raster[y,x]<255)
    groups=footprint_groups(points)
    flags=[]
    if not points: flags.append('no_curve_pixels_visible_off_grid')
    if len(groups)>1: flags.append('multiple_disconnected_visible_components')
    if figure==2 and any(abs(y-g)<=1 for x,y in points for g in grid_rows):
        flags.append('curve_pixel_footprint_touches_horizontal_grid_footprint')
    coordinates=[p[0] if figure==1 else p[1] for p in points]
    result={'figure':figure,'requested_moisture_kg_water_per_kg_dry_matter':LEVEL_TEXT[level],
        'status':'unknown' if flags else 'candidate_reading', 'unknown_reasons':flags,
        'reading_role':'intersection_of_published_continuous_curve_not_original_experimental_marker',
        'target_pixel_band_px':encoded_pair((p_lo,p_hi)),'sampled_pixel_rows_or_columns':indices,
        'raw_visible_pixels':[{'x':x,'y':y,'rgb':[int(raster[y,x])]*3} for x,y in sorted(points)],
        'visible_component_count':len(groups),'value':None,'digitization_bounds':None,
        'unit':'dimensionless water activity' if figure==1 else 'J per kg removed water',
        'experimental_uncertainty':None}
    if coordinates:
        span=F(min(coordinates))-F(1,2),F(max(coordinates))+F(1,2)
        bounds=inverse_bounds(output_axis,span)
        nominal=inverse(output_axis,F(min(coordinates)+max(coordinates),2),output_axis['nominal'])
        result['visible_output_pixel_footprint_px']=encoded_pair(span)
        if not flags:
            if not bounds[0]<=nominal<=bounds[1]:
                raise ValueError('nominal_not_in_pixel_and_calibration_bounds')
            result['value']=encoded(nominal)
            result['digitization_bounds']=encoded_pair(bounds)
        else:
            result['visible_part_only_not_full_curve_bound']={
                'nominal':encoded(nominal),'range':encoded_pair(bounds)}
    return result


def serial_calibration(axis):
    return {'physical_endpoints':list(map(str,axis['values'])),
        'feasible_pixel_endpoint_vertices':[encoded_pair(p) for p in axis['vertices']],
        'nominal_pixel_endpoints':encoded_pair(axis['nominal']),
        'nominal_choice':'arithmetic_mean_of_feasible_axis_vertices_not_a_material_fit',
        'ticks':axis['records'],'stub_axis':axis['stub_axis'],
        'stub_sampling_other_coordinate_half_open_range':axis['stub_region']}


def main():
    figures={}
    sources=[]
    for n,(name,expected,url) in SOURCES.items():
        p=ROOT.parent/name
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        if digest!=expected: raise ValueError('original_raster_identity_mismatch')
        a=np.asarray(Image.open(p).convert('RGB'))
        if not np.array_equal(a[:,:,0],a[:,:,1]) or not np.array_equal(a[:,:,0],a[:,:,2]):
            raise ValueError('expected_original_grayscale_figure')
        figures[n]=a[:,:,0]
        sources.append({'figure':n,'path':str(p),'sha256':digest,'bytes':p.stat().st_size,
            'width_px':int(a.shape[1]),'height_px':int(a.shape[0]),'url':url})
    axes={1:dict(x=calibration(FIG1_X,figures[1],'x',(245,248)),
                 y=calibration(FIG1_Y,figures[1],'y',(62,65))),
          2:dict(x=calibration(FIG2_X,figures[2],'x',(244,247)),
                 y=calibration(FIG2_Y,figures[2],'y',(80,83)))}
    # Full-width horizontal strokes, including anti-aliased pale gray grids.
    grid=[y for y in range(6,244) if np.count_nonzero(figures[2][y,84:489]<255)>=401]
    observations=[reading(n,w,figures[n],axes[n],grid if n==2 else ()) for n in (1,2) for w in LEVELS]
    common=[LEVEL_TEXT[w] for w in LEVELS if all(o['status']=='candidate_reading'
            for o in observations if o['requested_moisture_kg_water_per_kg_dry_matter']==LEVEL_TEXT[w])]
    result={'schema':'arlabosse95_published_curve_pixel_candidates_v1','temperature_c':'95',
        'material_identity':'Arlabosse2005 characterized unincinerated activated sludge from 85% industrial/15% municipal wastewater; flotation and centrifugation; not MIA3',
        'source_id':'SRC_ARLABOSSE_2005_CONTACT_DRYING','doi':'10.1590/S0104-66322005000200009',
        'publisher_html_sha256':'7dc682647cc70503820e6738b806b052ddccc9f1bc14650178e8813c7e203816',
        'original_figure_license':'publisher CC BY-NC 4.0 per existing source.json; originals retained in private scratch',
        'locators':['Sludge Characterization / Sorption Isotherm / Figure1 caption','Total Heat of Desorption / Figure2 caption'],
        'sources':sources,'calibration':{str(n):{a:serial_calibration(v) for a,v in xy.items()} for n,xy in axes.items()},
        'figure2_horizontal_grid_rows_masked_for_localization':grid,
        'observations':observations,'common_candidate_reading_levels_kg_water_per_kg_dry_matter':common,
        'continuous_moisture_domain_admitted':None,
        'method':{'protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest(),
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'python':sys.version,'pillow':PIL.__version__,'numpy':np.__version__,
            'pixel_footprints':'all nonwhite grayscale pixels, closed +/-0.5 px rectangles',
            'bounds':'conditional original-raster footprint plus complete affine tick-feasible polygon; not experimental uncertainty',
            'uncertainty_not_included':['experimental scatter and calibration error','dynamic-method bias','cross-observation correlations','subpixel behavior beyond the visible-stroke interpretation']},
        'heat_semantics':{'quantity':'total desorption heat, includes pure-water latent contribution',
            'mass_basis':'kg removed water, interpreted from referenced calorimetric heat-flow divided by mass-loss rate',
            'upstream_method_doi':'10.1016/j.ces.2004.01.002','upstream_locators':['printed1366 Eq4','printed1368-1369 Eqs21-23'],
            'add_another_latent_heat':False},
        'qualification':{'raw_candidates_for_independent_review':True,'digitized_points_are_original_measurement_markers':False,
            'original_curve_confirmed_fitted_function':False,'physical_function_fitted':False,
            'source_material_qualified':False,'runtime_model_admitted':False,'full_cycle_qualified':False,
            'new_source_searches':0,'simulations':0}}
    output=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'facts.json'
    with output.open('x') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print('wrote',output)
    for n in (1,2):
        for obs in observations:
            if obs['figure']!=n:continue
            print(n,obs['requested_moisture_kg_water_per_kg_dry_matter'],obs['status'],
                None if obs['value'] is None else obs['value']['approximate'],
                None if obs['digitization_bounds'] is None else [x['approximate'] for x in obs['digitization_bounds']],
                obs['unknown_reasons'])


if __name__=='__main__':main()
