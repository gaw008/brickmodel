"""Independent vector-coordinate audit, with no model or EOS calls."""
import hashlib
import json
import math
from pathlib import Path
import runpy
from fractions import Fraction as Q
from itertools import product
import xml.etree.ElementTree as ET

BASE = Path('/Users/wanggaoying/Desktop/brickmodel-github/data/sandbox/research/agar2018-heat/figure3')

def points(data: str) -> list[tuple[Q, Q]]:
    """Parse this fixed SVG's whitespace-separated absolute commands."""
    tokens = iter(data.split())
    pairs = []
    for item in tokens:
        if item in ('M', 'L', 'C', 'Z'):
            continue
        pairs.append((Q(item), Q(next(tokens))))
    return pairs

def hull(indices: list[int], paths: list[ET.Element]) -> list[Q]:
    coords = [xy for index in indices for xy in points(paths[index].attrib['d'])]
    return [min(x for x,y in coords), max(x for x,y in coords), min(y for x,y in coords), max(y for x,y in coords)]

def mapped(coords: list[Q], origin: list[Q], end: list[Q], first: int, last: int) -> list[Q]:
    vals = []
    for start, stop in product(origin, end):
        slope = Q(last-first)/(stop-start)
        vals.extend(first+slope*(coord-start) for coord in coords)
    return [min(vals), max(vals)]

def verify() -> dict[str, object]:
    saved = json.loads((BASE/'observations.json').read_bytes())
    paths = list(ET.parse(BASE/'page5.svg').iter('{http://www.w3.org/2000/svg}path'))
    # Axis and grid bands extracted from separate fixed original SVG objects.
    horizontal = [points(part) for part in paths[205].attrib['d'].split('Z') if len(points(part))>1]
    vertical = [points(part) for part in paths[206].attrib['d'].split('Z') if len(points(part))>1]
    assert len(horizontal)==8 and len(vertical)==15
    x0 = hull([207],paths)[:2]
    x30 = [min(x for x,y in vertical[-1]), max(x for x,y in vertical[-1])]
    y100 = hull([208],paths)[2:]
    y900 = [min(y for x,y in horizontal[-1]), max(y for x,y in horizontal[-1])]
    grids = []
    for axis,groups,start,end,lo,hi,labels in [('time',vertical[:-1],x0,x30,0,30,range(2,30,2)),('temperature',horizontal[:-1],y100,y900,100,900,range(200,900,100))]:
        for group,label in zip(groups,labels,strict=True):
            values = [xy[0 if axis=='time' else 1] for xy in group]
            bounds = mapped([min(values),max(values)],start,end,lo,hi)
            assert bounds[0] <= label <= bounds[1]
            grids.append({'axis':axis,'label':label,'bounds':list(map(str,bounds))})
    rows=saved['observations']; assert len(rows)==180
    counts={}; prior={}; used=[]
    for row in rows:
        run=row['run_id']; counts[run]=counts.get(run,0)+1
        bb=hull(row['path_indices'],paths)
        assert bb==list(map(Q,row['bbox_page_points']))
        assert all(paths[i].get('fill')==row['color'] for i in row['path_indices'])
        used.extend(row['path_indices'])
        assert row['marker_index']==counts[run]-1
        for field,coords,start,end,lo,hi in [('time_min',bb[:2],x0,x30,0,30),('temperature_c',bb[2:],y100,y900,100,900)]:
            bounds=mapped(coords,start,end,lo,hi); emitted=row[field]
            assert bounds==list(map(Q,emitted['rational_bounds']))
            decimals=list(map(Q,emitted['decimal_bounds']))
            assert decimals[0]<=bounds[0]<=bounds[1]<=decimals[1]
            assert 0<=bounds[0]-decimals[0]<Q('0.000001')
            assert 0<=decimals[1]-bounds[1]<Q('0.000001')
            assert emitted['representative_midpoint']==float(sum(bounds)/2)
            if field=='time_min':
                enclosed=list(range(math.ceil(bounds[0]),math.floor(bounds[1])+1))
                assert enclosed==[row['nominal_minute_enclosed']]==[counts[run]]
                assert row['time_envelope_extends_beyond_plot']==(bounds[0]<0 or bounds[1]>30)
                assert run not in prior or prior[run]<bounds[0]
                prior[run]=bounds[1]
    assert counts=={str(k):30 for k in range(15,21)}
    for run,legend in saved['legends_excluded'].items():
        assert hull(legend['path_indices'],paths)==list(map(Q,legend['bbox_page_points']))
        color=next(r['color'] for r in rows if r['run_id']==run)
        indices=[i for i,p in enumerate(paths) if p.get('fill')==color]
        actual=[i for r in rows if r['run_id']==run for i in r['path_indices']]+legend['path_indices']
        assert indices==actual
        used.extend(legend['path_indices'])
    assert len(used)==len(set(used))
    for field,path in [('source_pdf_sha256',BASE.parent/'source.pdf'),('svg_sha256',BASE/'page5.svg'),('extractor_sha256',BASE/'extract.py')]:
        assert saved[field]==hashlib.sha256(path.read_bytes()).hexdigest()
    # Replay is separate from independent truth reconstruction above.
    assert runpy.run_path(str(BASE/'extract.py'))['extract'](BASE)==saved
    return {'status':'passed','observations_checked':len(rows),'coordinate_intervals_checked':360,'series_counts':counts,'internal_grid_checks':grids,'replay_equal':True,'scope':'Fixed vector hull geometry and conditional calibration only; no instrument uncertainty or external validation','observations_sha256':hashlib.sha256((BASE/'observations.json').read_bytes()).hexdigest(),'verification_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
