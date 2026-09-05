import importlib.util
import unittest
from test_model import config
from model import Config
from solver import simulate


class DiagnosticTests(unittest.TestCase):
    def test_oxygen_starvation_is_not_burnout_and_absent_event_is_null(self):
        self.assertIsNotNone(importlib.util.find_spec("diagnostics"), "diagnostics not implemented")
        from diagnostics import summarize
        poor = summarize(simulate(Config.from_dict(config(boundary_mode="finite", reservoir_ratio=.25, n_cells=7))))
        rich = summarize(simulate(Config.from_dict(config(n_cells=7))))
        self.assertEqual(poor["status"], "oxygen_budget_limited")
        self.assertEqual(poor["t_burn95"], None)
        self.assertEqual(poor["t_burn99"], None)
        self.assertEqual(poor["t_burn95_status"], "oxygen_budget_limited")
        self.assertGreaterEqual(poor["final"]["carbon_mean"], .375-1e-10)
        self.assertLess(poor["final"]["co2_source_rate"], 1e-5)
        self.assertAlmostEqual(poor["budget"]["max_conversion_upper_bound"], .625)
        self.assertEqual(rich["status"], "reached_diagnostic_threshold")
        self.assertGreater(rich["t_burn99"], rich["t_burn95"])
        self.assertGreaterEqual(rich["t_local_burn99"], rich["t_burn99"])
        self.assertLess(rich["final"]["carbon_max"], .01)
        self.assertEqual(rich["not_modelled"]["t_close"], "not_modelled")
        self.assertEqual(rich["not_modelled"]["energy_conservation"], "not_modelled")
        slow = summarize(simulate(Config.from_dict(config(K=0, tau_end=1, n_cells=7))))
        self.assertIsNone(slow["t_burn95"])
        self.assertEqual(slow["t_burn95_status"], "not_reached_by_horizon")
        self.assertEqual(slow["t_gen"]["species"], "CO2_only")


if __name__ == "__main__":
    unittest.main()
