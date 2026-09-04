"""Read-only exploration of the imported study for report drafting."""
import json
from pipeline import Study, DEFAULT_INPUT
from zipfile import ZipFile
import xml.etree.ElementTree as ET

s = Study(DEFAULT_INPUT)
s.import_xrf()
s.import_tga()
s.import_psd()
s.import_pellets()
print('COUNTS', len(s.materials), len(s.observations), len(s.derivations))
print('RECALC', {sid: {'total':len([d for d in s.derivations if d['source_id']==sid]),
    'mismatch':len([d for d in s.derivations if d['source_id']==sid and not d['verified']])}
    for sid in s.books})
for g in s.summarize():
    print(g['group_id'], 'D_shrink=%0.4f water=%0.4f porosity=%0.4f density=%0.2f' %
        (g['diameter_shrinkage_mean'],g['water_absorption_mean']*100,g['open_porosity_mean']*100,g['dry_density_mean']))
print('TGA TABLES')
path=DEFAULT_INPUT / s.files['30157066']
with ZipFile(path) as z:
    for name in z.namelist():
        if name.startswith('xl/worksheets/_rels/'):
            print('RELS',name,[(n.attrib.get('Id'),n.attrib.get('Target')) for n in ET.fromstring(z.read(name))])
        if name.startswith('xl/tables/table') and name.endswith('.xml'):
            node=ET.fromstring(z.read(name))
            print(name,node.attrib)
print('TGA CONDITION',json.dumps(s.conditions[:7],ensure_ascii=False))
print('PSD crossing 50% (size coordinate, NOT an interpolated D50)')
for label in ['#0262','Pilot-8','#0263','Pilot-10']:
    rows=[r for r in s.materials if r['source_id']=='30156970' and r['original_label']==label and r['property']=='psd_cumulative_volume']
    high=next(r for r in rows if r['value']>=50)
    print(label, high['cell'], high['value'], s.books['30156970']['Sheet2'].value('E'+high['cell'][1:]))
