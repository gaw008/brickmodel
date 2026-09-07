"""Regression for the actual W07/L01 prescribed-temperature audit failure."""
import unittest

from model import Scenario
from reference.oracle import exposure
from resources import Budget
from scenarios import expand_frozen_manifest
import solver


class ExposureAccuracyTests(unittest.TestCase):
    def test_historical_failed_ramps_meet_original_audit_tolerance(self):
        cases = {scenario.id: scenario for scenario in expand_frozen_manifest()}
        for case_id in ('W07', 'L01'):
            # Preserve the original ramp and truncate only its subsequent hold.
            # These remain synthetic B2 scenarios, not material measurements.
            values = cases[case_id].to_dict()
            values['numerics']['tau_end'] = 2
            values['temperature']['knots'] = values['temperature']['knots'][:2]
            scenario = Scenario.from_dict(values)
            result = solver.integrate(scenario, Budget(30, 30, 'exposure_regression'))
            errors = []
            for tau, state in result.records:
                reference, _ = exposure(
                    values['temperature']['knots'], tau,
                    values['reaction']['K_ref'], values['reaction']['theta'],
                )
                errors.append(abs(state.H - reference) / max(1, reference))
                self.assertAlmostEqual(
                    values['reaction']['Gamma'] * (1 - sum(state.f) / len(state.f)),
                    state.generated, places=11,
                )
            with self.subTest(case_id=case_id):
                # The original audit threshold is retained; the solver uses a
                # tighter numerical quadrature budget, not a relaxed audit.
                self.assertLessEqual(max(errors), 1e-6)


if __name__ == '__main__':
    unittest.main()
