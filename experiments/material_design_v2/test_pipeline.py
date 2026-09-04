"""Focused, offline tests; run with python3 -m unittest discover -s this_directory."""
import importlib.util
import unittest
import json
import tempfile
import sys
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = Path('/home/ubuntu/.hermes/reports/sludge-material-design-v2')


class WorkbookTests(unittest.TestCase):
    def test_xrf_shared_formulas_and_cache_are_not_lost(self):
        self.assertIsNotNone(importlib.util.find_spec('pipeline'), 'read-only pipeline is not implemented')
        import pipeline as p
        sheet = p.read_workbook(INPUT / 'public-data/30156127/XRF DTU Data.xlsx')['Sheet1']
        self.assertEqual(sum(c.formula is not None for c in sheet.cells.values()), 259)
        self.assertEqual(sheet['B1'].value, '#0250')
        self.assertAlmostEqual(sheet['D30'].value, 2.5215)
        self.assertEqual(sheet['D30'].formula, '0.7*$B3+0.3*E3')
        self.assertEqual(sheet['B13'].value, None)
        self.assertEqual(sheet['C6'].value, 0)


class MaterialTests(unittest.TestCase):
    def test_identity_and_dry_basis_are_fail_unknown(self):
        import pipeline as p
        self.assertTrue(hasattr(p, 'resolve_identity'), 'identity gate not implemented')
        self.assertEqual(p.resolve_identity('#0262'), ('SSA-P1-Raw', 'sewage_sludge_ash', 'resolved'))
        for label in ('#0179', 'SSA-P1-A2P', 'SSA-P2-A2P', 'Silica Sand', 'new-label'):
            self.assertEqual(p.resolve_identity(label)[2], 'identity_ambiguous')
        self.assertAlmostEqual(p.dry_fraction(17.5, 7.5, basis='dry', unit='g'), 0.3)
        self.assertIsNone(p.dry_fraction(17.5, 7.5, basis='wet', unit='g'))
        self.assertIsNone(p.dry_fraction(17.5, None, basis='dry', unit='g'))
        self.assertIsNone(p.dry_fraction(17.5, 7.5, basis='dry', unit='unknown'))

    def test_xrf_preserves_loi_blanks_and_source_mixtures(self):
        import pipeline as p
        self.assertTrue(hasattr(p, 'Study'), 'material importer not implemented')
        study = p.Study(INPUT)
        study.import_xrf()
        rows = study.materials
        raw = [r for r in rows if r['property'] == 'xrf_CaO']
        self.assertEqual(len(raw), 7)
        self.assertTrue(all(r['basis'] == 'source_oxide_plus_LOI1050_total_pct' for r in raw))
        y = next(r for r in raw if r['material_id'] == 'Y')
        self.assertAlmostEqual(y['value'], 11.318)
        cu = next(r for r in rows if r['material_id'] == 'Y' and r['property'] == 'xrf_CuO')
        self.assertIsNone(cu['value'])
        mix = next(r for r in study.observations if r['specimen_id'] == 'mix:Y-P1-Raw' and r['property'] == 'mixture_xrf_CaO')
        self.assertEqual(mix['evidence_status'], 'source_derived')
        self.assertAlmostEqual(mix['value'], 12.845)
        self.assertEqual(sum(d['verified'] for d in study.derivations), 139)
        self.assertTrue(all(e['evidence_status']=='source_derived' for e in study.material_evidence if e['cell'].endswith('20')))
        self.assertTrue(all(r['evidence_status'] == 'identity_ambiguous' for r in study.observations if 'A2P' in r['specimen_id']))


class ThermalAndPSDTests(unittest.TestCase):
    def test_tga_is_seven_curves_not_independent_temperature_samples(self):
        import pipeline as p
        self.assertTrue(hasattr(p.Study, 'import_tga'), 'TGA importer not implemented')
        study = p.Study(INPUT)
        study.import_tga()
        self.assertEqual(len(study.conditions), 7)
        self.assertTrue(all(c['atmosphere'] == 'N2' and c['heating_rate_K_min'] == 10 for c in study.conditions))
        self.assertTrue(all(c['kinetic_identifiability'] == 'unknown_single_heating_rate' for c in study.conditions))
        self.assertEqual(len({r['material_id'] for r in study.materials}), 7)
        mass = next(r for r in study.materials if r['sheet'] == '#0250' and r['cell'] == 'B17')
        self.assertAlmostEqual(mass['value'], 30.1207)  # differs from generic metadata 35–40 mg
        bad = next(d for d in study.derivations if d['sheet'] == 'Pilot-8' and d['cell'] == 'D33')
        self.assertFalse(bad['verified'])  # source cache is not local C33/B17*100
        dtg = next(e for e in study.material_evidence if e['sheet']=='#0250' and e['cell']=='F33')
        self.assertEqual(dtg['evidence_status'], 'source_derived')
        self.assertEqual(dtg['method_status'], 'unknown_instrument_algorithm')

    def test_psd_identity_and_cumulative_are_separate(self):
        import pipeline as p
        self.assertTrue(hasattr(p.Study, 'import_psd'), 'PSD importer not implemented')
        study = p.Study(INPUT)
        study.import_psd()
        distributions = {r['original_label'] for r in study.materials}
        self.assertEqual(len(distributions), 6)
        self.assertTrue(all(r['identity_status'] == 'identity_ambiguous' for r in study.materials if '#0179' in r['original_label']))
        self.assertTrue(all(d['verified'] for d in study.derivations))
        self.assertTrue(all(r['basis'] == 'volume_distribution_ethanol_dried_milled_as_labeled' for r in study.materials))
        cumulative = {(r['sheet'],r['cell']) for r in study.materials if r['property']=='psd_cumulative_volume'}
        self.assertTrue(all(e['evidence_status']=='source_derived' for e in study.material_evidence if (e['sheet'],e['cell']) in cumulative))


class PelletTests(unittest.TestCase):
    def test_changed_additive_label_fails_join(self):
        import pipeline as p
        study = p.Study(INPUT)
        ws = study.books['30157108']['High and Diameter']
        ws.cells['A60'] = p.Cell('#0250-#0263')
        with self.assertRaisesRegex(ValueError, 'additive'):
            study.import_pellets()

    def test_reference_cannot_silently_become_thirty_percent_ash(self):
        import pipeline as p
        study = p.Study(INPUT)
        ws = study.books['30157108']['Mixing']
        ws.cells['D43'], ws.cells['E43'] = p.Cell(17.5), p.Cell(7.5)
        with self.assertRaisesRegex(ValueError, 'fraction'):
            study.import_pellets()

    def test_source_recomputation_and_same_specimen_join(self):
        import pipeline as p
        self.assertTrue(hasattr(p.Study, 'import_pellets'), 'pellet importer not implemented')
        study = p.Study(INPUT)
        study.import_pellets()
        rows = study.observations
        shrink = [r for r in rows if r['property'] == 'diameter_shrinkage']
        porosity = [r for r in rows if r['property'] == 'open_porosity']
        self.assertEqual(len(shrink), 252)
        self.assertEqual(len(porosity), 108)
        self.assertEqual(len({r['specimen_id'] for r in rows}), 252)
        self.assertEqual(len([r for r in shrink if r['evidence_status'] == 'identity_ambiguous']), 42)
        self.assertEqual(len(study.conditions), 36)
        self.assertTrue(all(r['additive_fraction_dry'] in (0, 0.3) for r in rows))
        self.assertFalse(any('Figures' in r['sheet'] or r['sheet'] == 'P&D 2' for r in rows))
        y = next(r for r in porosity if r['cell'] == 'M14')
        self.assertAlmostEqual(y['value'], (3.364-2.8395)/(3.364-1.803))
        y_shrink = next(r for r in shrink if r['specimen_id'] == y['specimen_id'])
        self.assertEqual(y_shrink['cell'], 'W9')
        self.assertEqual(y_shrink['unit'], '%')
        self.assertEqual(y['unit'], 'm3/m3')
        self.assertTrue(all(d['verified'] for d in study.derivations))
        groups = study.summarize()
        self.assertEqual(len(groups), 30)  # 36 source series minus 6 ambiguous A2P
        self.assertTrue(all(g['n_shrinkage'] == 7 and g['n_water'] == 3 for g in groups))
        self.assertTrue(all('A2P' not in g['additive_id'] for g in groups))
        imputed_group=next(g for g in groups if g['group_id']=='R|P2-ED|1030')
        self.assertEqual(imputed_group['n_volume'],6)
        self.assertEqual(len(study.imputations),3)
        self.assertNotIn('R|P2-ED|1030|G',imputed_group['volume_specimens'])


class ExportTests(unittest.TestCase):
    def test_command_evidence_preserves_failure_exit_code(self):
        self.assertIsNotNone(importlib.util.find_spec('verify'), 'verification recorder not implemented')
        from verify import run_command
        result = run_command([sys.executable, '--definitely-invalid-option'], cwd=HERE)
        self.assertNotEqual(result['exit_code'], 0)
        self.assertGreaterEqual(result['elapsed_seconds'], 0)
        self.assertTrue(result['output'])

    def test_all_sheets_reconcile_and_figures_do_not_add_samples(self):
        import pipeline as p
        self.assertTrue(hasattr(p, 'run'), 'complete export not implemented')
        with tempfile.TemporaryDirectory(dir=HERE, prefix='.test-') as directory:
            out = Path(directory)
            result = p.run(INPUT, out)
            import csv
            with (out/'materials.csv').open() as stream:
                self.assertEqual(next(csv.reader(stream)),p.MATERIAL_FIELDS)
            with (out/'observations.csv').open() as stream:
                observations=list(csv.DictReader(stream))
            self.assertEqual(list(observations[0]),p.OBSERVATION_FIELDS)
            derivations=json.loads((out/'derivations.json').read_text())
            lineage={(d['source_id'],d['sheet'],d['cell']) for d in derivations}
            self.assertTrue(all((r['source_id'],r['sheet'],r['cell']) in lineage for r in observations if r['evidence_status']=='source_derived'))
            self.assertEqual(result['counts']['sheets'], 19)
            self.assertEqual(result['counts']['pellet_specimens'], 252)
            inventory = json.loads((INPUT / 'workbook-inventory.json').read_text())
            audit = json.loads((out / 'sheet_audit.json').read_text())
            for book in inventory:
                for sheet in book['sheets']:
                    actual = next(a for a in audit if a['source_id'] == str(book['dataset_id']) and a['sheet'] == sheet['name'])
                    self.assertEqual(actual['nonempty_rows'], sheet['nonempty_rows'])
                    self.assertEqual(actual['formula_cells'], sheet['formula_cells'])
                    self.assertEqual(actual['nonempty_cells'], actual['selected_cells'] + actual['excluded_cells'])
            for fig in ['observation_comparison.svg', 'treatment_tradeoff.svg']:
                root = ET.parse(out / fig).getroot()
                series = [n for n in root.iter() if n.attrib.get('data-series')]
                self.assertEqual(len(series), 30)
                self.assertEqual(len({s.attrib['data-series'] for s in series}), 30)
                for node in root.iter():
                    if node.tag.endswith('circle'):
                        self.assertTrue(0<float(node.attrib['cx'])<1200)
                        self.assertTrue(0<float(node.attrib['cy'])<790)
                    self.assertFalse(node.tag.endswith('script'))
                    self.assertFalse(any('href' in k for k in node.attrib))
                self.assertNotIn('A2P', '|'.join(s.attrib['data-series'] for s in series))
                text = (out / fig).read_text()
                self.assertIn('CC BY 4.0', text)
                self.assertIn('10.11583/DTU', text)
            self.assertTrue(result['input_hashes_unchanged'])
            for report in ['DATA_AUDIT.md','DIRECTION_REPORT.md','MODEL_GAP_PRIORITY.md']:
                self.assertTrue((out/report).is_file(), 'report rendering not implemented')
                text=(out/report).read_text()
                self.assertNotIn('{{',text)
                self.assertIn('## Sources',text)
            direction=(out/'DIRECTION_REPORT.md').read_text()
            for hypothesis in ('H1','H2','H3','H4'):
                self.assertIn('假说 '+hypothesis,direction)
            before = hashlib.sha256((out/'observations.csv').read_bytes()).hexdigest()
            p.run(INPUT, out)
            self.assertEqual(before, hashlib.sha256((out/'observations.csv').read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
