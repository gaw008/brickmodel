"""Read-only workbook probe; stdlib only, no evaluation or Excel rewrite."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path('/home/ubuntu/.hermes/reports/sludge-material-design-v2')
N = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def sheets(path):
    with ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(t.itertext()) for t in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rel = {r.attrib['Id']: r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        sheet_list = ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', N)
        assert sheet_list is not None
        for s in sheet_list:
            target = rel[s.attrib['{' + R + '}id']]
            target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            tree = ET.fromstring(z.read(target))
            rows = []
            for row in tree.findall('.//m:sheetData/m:row', N):
                cells = []
                for c in row:
                    v = c.find('m:v', N)
                    f = c.find('m:f', N)
                    val = v.text if v is not None else None
                    if c.attrib.get('t') == 's' and val is not None:
                        val = shared[int(val)]
                    if c.attrib.get('t') == 'inlineStr':
                        inline = c.find('m:is', N)
                        assert inline is not None
                        val = ''.join(inline.itertext())
                    if val is not None or f is not None:
                        cells.append((c.attrib['r'], val, (f.text or 'SHARED:'+str(f.attrib)) if f is not None else None))
                if cells:
                    rows.append(cells)
            yield s.attrib['name'], rows


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', default='all')
    p.add_argument('--sheet')
    p.add_argument('--rows', type=int, default=12)
    p.add_argument('--start', type=int, default=1)
    p.add_argument('--headers', action='store_true')
    args = p.parse_args()
    for entry in json.loads((ROOT / 'download-manifest.json').read_text()):
        if not entry['name'].endswith('.xlsx') or args.dataset not in ('all', str(entry['dataset_id'])):
            continue
        print('\nFILE', entry['dataset_id'], entry['name'])
        for name, rows in sheets(entry['path']):
            if args.sheet and name != args.sheet:
                continue
            print('SHEET', name, 'nonempty_rows', len(rows), 'cells', sum(map(len, rows)), 'formulas', sum(c[2] is not None for r in rows for c in r))
            for row in rows[args.start-1:args.start-1+args.rows]:
                if args.headers:
                    row = [c for c in row if c[0].rstrip('0123456789') in ('A', 'B', 'C', 'L', 'M', 'N') and c[1] and any(t in c[1] for t in ('#', 'Raw', 'ED', '1020', '1030', '1050', 'A2P')) and c[2] is None]
                    if not row:
                        continue
                print(' | '.join(f'{c[0]}={c[1]}' + (f' [={c[2]}]' if c[2] is not None else '') for c in row))
