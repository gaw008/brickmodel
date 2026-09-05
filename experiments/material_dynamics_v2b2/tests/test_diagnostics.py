"""Event, exposure, scope and resource semantics without extra solves."""
import importlib.util
import unittest
from scenarios import expand_frozen_manifest


class DiagnosticTests(unittest.TestCase):
    def test_events_screening_and_budget(self):
        self.assertIsNotNone(importlib.util.find_spec('diagnostics'),'diagnostics absent')
        from diagnostics import event, numerical_label
        from screening import paired_status
        from resources import Budget
        e=event([0,.1,.2],[1,.02,.005],.01,1)
        self.assertEqual(e['bracket_tau'],[.1,.2]); self.assertAlmostEqual(e['tau'],1/6)
        e=event([0,.1],[1,.4],.01,.625)
        self.assertIsNone(e['tau']); self.assertIsNone(e['bracket_tau']); self.assertEqual(e['status'],'excluded_by_oxygen_budget')
        self.assertEqual(event([0,.1],[0,0],.01,1)['status'],'initially_reached')
        self.assertEqual(numerical_label(True,'integrated',True,'missing'),'not_run')
        self.assertEqual(numerical_label(True,'integrated',True,'bound'),'passed_frozen_suite')
        self.assertEqual(numerical_label(True,'integrated',False,'bound'),'failed')
        self.assertEqual(numerical_label(True,'partial_timeout',None,'bound'),'not_run')
        self.assertEqual(numerical_label(False,'numerical_failure',False,'bound'),'not_verified_for_custom_case')
        self.assertEqual(paired_status([.001,.002],['passed_frozen_suite']*2),'sampled_candidate_under_assumptions')
        self.assertEqual(paired_status([.02,.03],['passed_frozen_suite']*2),'not_reached_in_sampled_domain')
        for vals, labels in [([.001,.02],['passed_frozen_suite']*2),([.008,.001],['passed_frozen_suite']*2),([.001,.002],['not_run']*2)]:
            self.assertEqual(paired_status(vals,labels),'unresolved_in_assumption_envelope')
        self.assertEqual(paired_status([.001,.02],['failed','passed_frozen_suite']),'unknown_numerical')
        b=Budget(.000001,180,'demo')
        with self.assertRaises(TimeoutError):
            for _ in range(10000): b.check()
        r=b.snapshot('partial_timeout')
        self.assertEqual(r['active_budget_seconds'],.000001); self.assertEqual(r['ceiling_budget_seconds'],180)

if __name__=='__main__': unittest.main()
