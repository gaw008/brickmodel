"""Contract-first tests; standard library only."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_frozen_expansion_and_strict_rejection(self):
        self.assertIsNotNone(importlib.util.find_spec('model'), 'B2 strict input implementation absent')
        from model import Scenario, strict_json
        from scenarios import expand_frozen_manifest
        matrix = json.loads((ROOT / 'B2_ACCEPTANCE_MATRIX.json').read_text())
        cases = expand_frozen_manifest(matrix)
        self.assertEqual(len(cases), 22)
        w = next(s for s in cases if s.id == 'W03')
        self.assertEqual(w.to_dict()['temperature']['knots'], matrix['scenario_manifest']['programs']['P_EARLY'])
        for text in ['{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', '['*9+'0'+']'*9]:
            with self.subTest(text_kind=text[:4]):
                with self.assertRaises(ValueError):
                    strict_json(text)
        for group, key, value in [('reaction','Gamma',True), ('reaction','K_ref','1'),
                                  ('reaction','theta',7), ('transport','m',2),
                                  ('boundary','reservoir_ratio',1), ('numerics','n_cells',15.0),
                                  ('temperature','T_ref_K',599), ('initial','u',0)]:
            d = w.to_dict(); d[group][key] = value
            with self.subTest(group=group, key=key):
                with self.assertRaises(ValueError):
                    Scenario.from_dict(d)
        for mutation in ['missing','unknown','duplicate_knot','missing_end','unsupported','coefficient_overflow']:
            d = w.to_dict()
            if mutation == 'missing': del d['initial']
            if mutation == 'unknown': d['password'] = 'not-a-secret-test-payload'
            if mutation == 'duplicate_knot': d['temperature']['knots'][1]['tau'] = 0
            if mutation == 'missing_end': d['temperature']['knots'].pop()
            if mutation == 'unsupported': d['scope'] = 'energy'
            if mutation == 'coefficient_overflow': d['reaction']['K_ref'] = 10
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError): Scenario.from_dict(d)
        d = w.to_dict(); d['reaction']['Gamma'] = 3
        self.assertNotEqual(Scenario.from_dict(d).canonical(), w.canonical())
        # Returned dictionaries cannot mutate the immutable Scenario.
        d = w.to_dict(); d['reaction']['Gamma'] = 8
        self.assertEqual(w.to_dict()['reaction']['Gamma'], 2)


if __name__ == '__main__':
    unittest.main()
