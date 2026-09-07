"""Reproduce finite manual Figure 4 picks; never infer unpicked curve samples.

Requires poppler pdfimages and Pillow, and the hash-matched locally cached PDF.
Run from any directory. --check verifies CSV/JSON without overwriting them.
"""
import argparse
import csv
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_EVEN
from fractions import Fraction as F
import hashlib
import io
import itertools
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
CACHE=ROOT/'runs/sandbox/source-cache/areias2025-20260907'
PDF=CACHE/'minerals-15-00879.pdf'
PDF_SHA='9c59141a717cb3b062aed6f28b48ed6005c5564aa3ce5a86de1c083bb6eae8a6'


def transform(pixel,first,last):
    x0,v0=map(F,first);x1,v1=map(F,last)
    return v0+(F(pixel)-x0)*(v1-v0)/(x1-x0)


def enclosure(pixel,ticks,halfwidth,tick_error):
    first,last=ticks[0],ticks[-1]
    nominal=transform(pixel,first,last)
    residual=max(abs(transform(x,first,last)-F(v)) for x,v in ticks)
    corners=[transform(F(pixel)+dp,(F(first[0])+d0,first[1]),(F(last[0])+d1,last[1]))
             for dp,d0,d1 in itertools.product((-F(halfwidth),F(halfwidth)),
                 (-F(tick_error),F(tick_error)),(-F(tick_error),F(tick_error)))]
    return nominal,min(corners)-residual,max(corners)+residual,residual


def decimal(value,places,rounding=ROUND_HALF_EVEN):
    with localcontext() as ctx:
        ctx.prec=60
        return str((Decimal(value.numerator)/Decimal(value.denominator)).quantize(Decimal(places),rounding=rounding))


def generate(record):
    rows=[];checks={}
    widths=record['coordinate_halfwidth_pixels']
    for name,panel in record['panels'].items():
        checks[name]={}
        for number,(x,y) in enumerate(panel['points'],1):
            tx,tlo,thi,tr=enclosure(x,panel['x_ticks'],widths['curve_x'],widths['tick_center'])
            sy,slo,shi,sr=enclosure(y,panel['y_ticks'],widths['curve_y']+widths['additional_tile_y_geometry'],widths['tick_center'])
            rows.append(dict(point_id=f'{name}{number:02}',panel=name,mixture=panel['mixture'],
                pixel_x=x,pixel_y=y,temperature_c=decimal(tx,'.1'),
                temperature_lower_c=decimal(tlo,'.1',ROUND_FLOOR),temperature_upper_c=decimal(thi,'.1',ROUND_CEILING),
                relative_length_change_percent=decimal(sy,'.001'),
                relative_length_change_lower_percent=decimal(slo,'.001',ROUND_FLOOR),
                relative_length_change_upper_percent=decimal(shi,'.001',ROUND_CEILING),
                relative_length_change_fraction=decimal(sy/100,'.00001')))
            checks[name]={'x_tick_max_residual_c':float(tr),'y_tick_max_residual_percentage_points':float(sr)}
    buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    return buf.getvalue(),dict(schema_version=1,method_id=record['method_id'],points=rows,
        calibration_residuals=checks,material_qualified=False,training_eligible=False,
        qualification=record['error_qualification'],experimental_uncertainty=None)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if hashlib.sha256(PDF.read_bytes()).hexdigest()!=PDF_SHA:raise ValueError('original_pdf_hash_mismatch')
    record=json.loads((HERE/'picks.json').read_text())
    csv_text,data=generate(record)
    outputs={'points.csv':csv_text,'points.json':json.dumps(data,indent=2,ensure_ascii=False)+'\n'}
    for name,content in outputs.items():
        path=HERE/name
        if args.check:
            if path.read_text()!=content:raise ValueError('derived_content_mismatch: '+name)
        else:path.write_text(content)
    if not args.check:
        cache=CACHE/'digitization';cache.mkdir(exist_ok=True)
        subprocess.run(['pdfimages','-f','9','-l','9','-png',str(PDF),str(cache/'tile')],check=True)
        for name,indices in record['tile_order'].items():
            tiles=[Image.open(cache/f'tile-{i:03}.png').convert('RGB') for i in indices]
            panel=Image.new('RGB',(tiles[0].width,sum(t.height for t in tiles)),'white')
            top=0
            for tile in tiles:panel.paste(tile,(0,top));top+=tile.height
            panel.save(cache/f'panel-{name}.png')
            draw=ImageDraw.Draw(panel)
            for row in data['points']:
                if row['panel']!=name:continue
                x,y=row['pixel_x'],row['pixel_y'];draw.ellipse((x-10,y-10,x+10,y+10),outline='red',width=3)
                draw.text((x+12,y-22),row['point_id'],fill='red')
            panel.save(HERE/f'panel-{name}-picks.png')
    print(json.dumps({'points':len(data['points']),'check':args.check,'calibration_residuals':data['calibration_residuals']}))


if __name__=='__main__':main()
