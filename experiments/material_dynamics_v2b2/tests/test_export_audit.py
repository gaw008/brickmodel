"""Export and fixed-tolerance audit tracer using actual one-step FV data."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from scenarios import expand_frozen_manifest
from solver import initial_state, step, RunResult
from model import ROOT
from test_support import fixture_root


class ExportTests(unittest.TestCase):
    def test_raw_export_audit_and_mutations(self):
        self.assertIsNotNone(importlib.util.find_spec('exports'),'exports absent')
        from exports import write_raw
        from audit import audit_exports
        from model import Scenario
        import json
        s=next(s for s in expand_frozen_manifest() if s.id=='C02')
        d=s.to_dict(); d['numerics']['tau_end']=.0001; d['temperature']['knots']=[{'tau':0,'T_K':450},{'tau':.0001,'T_K':450}]
        s=Scenario.from_dict(d); a=initial_state(s); b=step(s,a,0,.0001)
        result=RunResult(s,[(0,a),(.0001,b)],1,0,.0001,.0001,[0,.0001])
        out=Path(tempfile.mkdtemp(prefix='export-',dir=fixture_root()))
        write_raw(out,[result])
        self.assertTrue(audit_exports(str(out.relative_to(ROOT)))['passed'])
        p=out/'profiles.csv'; original=p.read_text(); p.write_text(original.replace(',1,0,1\n',',0.9,0,1\n',1))
        self.assertFalse(audit_exports(str(out.relative_to(ROOT)))['passed'])
        p.write_text(original)
        self.assertTrue(audit_exports(str(out.relative_to(ROOT)))['passed'])

if __name__=='__main__': unittest.main()
