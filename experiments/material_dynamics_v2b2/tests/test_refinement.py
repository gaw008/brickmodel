"""Numeric orchestration must be present before the committed evidence run."""
import importlib.util
import unittest

class NumericHarnessTests(unittest.TestCase):
    def test_frozen_runner_interface(self):
        self.assertIsNotNone(importlib.util.find_spec('verification'),'numeric runner absent')
        from verification import compare_events, refinement_metrics
        a={'e':{'tau':None,'bracket_tau':None}}
        self.assertEqual(compare_events(a,a)['e']['time_error'],None)
        self.assertEqual(compare_events(a,{'e':{'tau':1.,'bracket_tau':[.9,1.]}})['e']['status'],'event_convergence_unresolved')

if __name__=='__main__': unittest.main()
