"""Actual CLI rejection and timeout paths; no extra successful solver case."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from model import ROOT
from test_support import fixture_root
from scenarios import expand_frozen_manifest


class CLITests(unittest.TestCase):
    def test_cli_failure_telemetry(self):
        self.assertTrue((ROOT/'run.py').exists(),'CLI absent')
        base=Path(tempfile.mkdtemp(prefix='cli-',dir=fixture_root()))
        rel=str(base.relative_to(ROOT))
        trials=[(['--suite','frozen','--out',rel+'/short','--budget-seconds','0.000001'],3,.000001),
                (['--suite','frozen','--out','../escape','--budget-seconds','12'],2,12.),
                (['--suite','frozen','--out',rel+'/bad_budget','--budget-seconds','not-a-number'],2,None),
                (['--suite','frozen','--out',rel+'/schema','--verification','B2_VALIDATION_STATUS_FIXTURES.json'],2,180.)]
        d=next(s for s in expand_frozen_manifest() if s.id=='W03').to_dict(); d['reaction']['Gamma']=3
        (base/'custom.json').write_text(json.dumps(d))
        trials.append((['--config',rel+'/custom.json','--out',rel+'/custom_short','--budget-seconds','0.000001'],3,.000001))
        for i,(args,expected,active) in enumerate(trials):
            p=subprocess.run([sys.executable,'-B','run.py',*args],cwd=ROOT,capture_output=True,text=True,timeout=15)
            (base/f'{i}.json').write_text(json.dumps({'command':['python3','-B','run.py',*args],'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}))
            self.assertEqual(p.returncode,expected,p.stdout+p.stderr)
            telemetry=json.loads(p.stdout.strip())
            self.assertEqual(telemetry['resources']['active_budget_seconds'],active)
            self.assertEqual(telemetry['resources']['ceiling_budget_seconds'],180)
            self.assertNotIn('not-a-number',p.stdout+p.stderr)
        self.assertEqual(json.loads((base/'custom_short'/'failure.json').read_text())['numerical_validation'],'not_verified_for_custom_case')

    def test_forced_real_inventory_failure_telemetry(self):
        import contextlib
        import io
        from unittest.mock import patch
        from binding import capture_identity
        from solver import State, check
        import run
        base=Path(tempfile.mkdtemp(prefix='forced-',dir=fixture_root()))
        def reject_inventory(*args,**kwargs):
            check(State([-1.],[0.],[1.]))
        stream=io.StringIO()
        # Harness-only entry injection exercises a real negative-inventory check;
        # no CLI force flag, fake scientific trajectory, or additional solve.
        with patch('run.capture_identity',return_value=capture_identity(require_commit=False)), patch('run.integrate',side_effect=reject_inventory), contextlib.redirect_stdout(stream):
            code=run.main(['--suite','frozen','--out',str((base/'out').relative_to(ROOT)),'--budget-seconds','13'])
        data=json.loads(stream.getvalue()); (base/'result.json').write_text(json.dumps({'exit_code':code,'output':data,'control':'harness_injected_real_negative_inventory_check'}))
        self.assertEqual(code,1); self.assertEqual(data['execution_status'],'numerical_failure')
        self.assertEqual(data['numerical_validation'],'failed'); self.assertEqual(data['resources']['active_budget_seconds'],13)

if __name__=='__main__': unittest.main()
