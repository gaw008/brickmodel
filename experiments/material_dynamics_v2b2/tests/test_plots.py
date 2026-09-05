"""Static SVG coordinate correspondence from a real conservative-step export."""
import importlib.util
import tempfile
from pathlib import Path
import unittest
from model import ROOT, Scenario
from test_support import fixture_root
from scenarios import expand_frozen_manifest
from solver import initial_state, step, RunResult
from diagnostics import compute
from exports import write_raw, write_json, write_csv
from screening import evaluate
from scenarios import matrix

class PlotTests(unittest.TestCase):
    def test_static_coordinates(self):
        self.assertIsNotNone(importlib.util.find_spec('plots'),'plotting absent')
        from plots import generate, verify
        s=next(s for s in expand_frozen_manifest() if s.id=='W03')
        d=s.to_dict(); d['numerics']['tau_end']=.0001; d['temperature']['knots']=[{'tau':0,'T_K':450},{'tau':.0001,'T_K':450}]
        s=Scenario.from_dict(d); a=initial_state(s); b=step(s,a,0,.0001)
        result=RunResult(s,[(0,a),(.0001,b)],1,0,.0001,.0001,[0,.0001])
        diag=compute(s,result); diag.update(verification_scope='audit_only',numerical_validation='not_verified_for_custom_case')
        out=Path(tempfile.mkdtemp(prefix='plot-',dir=fixture_root())); write_raw(out,[result])
        rows=evaluate(matrix(),[diag],{})
        write_csv(out/'screening.csv',matrix()['screening_output_required_fields'],rows)
        generate(out,'test_scope_only')
        self.assertTrue(verify(out)['passed'])

if __name__=='__main__': unittest.main()
