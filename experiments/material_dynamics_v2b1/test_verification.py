import importlib.util
from pathlib import Path
import time
import unittest

from model import Config
from solver import simulate
from test_model import config

HERE = Path(__file__).resolve().parent


class NumericalVerificationTests(unittest.TestCase):
    def test_three_frozen_convergence_cases_and_independent_references(self):
        self.assertIsNotNone(importlib.util.find_spec("verification"), "numerical verification not implemented")
        from verification import verify_numerics
        baseline = {}
        for sid in ("base", "reaction_fast", "finite_small"):
            cfg = Config.from_json((HERE/"inputs"/(sid+".json")).read_text())
            baseline[sid] = simulate(cfg)
        verification = verify_numerics(baseline, deadline=time.monotonic()+120)
        self.assertEqual(verification["status"], "passed")
        self.assertEqual(set(verification["convergence"]), set(baseline))
        for row in verification["convergence"].values():
            self.assertEqual([r["n_cells"] for r in row["space_runs"]], [7, 15, 31])
            self.assertEqual([r["dt_scale"] for r in row["time_runs"]], [1, .5, .25])
            self.assertTrue(row["passed"])
        missing = verification["convergence"]["finite_small"]["space_comparisons"][1]["events"]["t_burn95"]
        self.assertEqual(missing["status"], "not_comparable_not_reached")
        self.assertIsNone(missing["delta"])
        for boundary in ("robin", "dirichlet_limit"):
            self.assertLess(verification["diffusion"][boundary][-1]["max_cell_average_error"], 3e-4)
        self.assertEqual(verification["normalization"]["status"], "passed")
        self.assertEqual(verification["closed_reaction"]["status"], "passed")

    def test_numerical_and_resource_failures_do_not_become_physical_status(self):
        cfg = Config.from_dict(config(n_cells=7))
        for scale in (0, -1, float("nan"), 2):
            with self.assertRaises(ValueError):
                simulate(cfg, dt_scale=scale)
        with self.assertRaises(TimeoutError):
            simulate(cfg, deadline=time.monotonic()-1)
        with self.assertRaises(TimeoutError):
            simulate(Config.from_dict(config(tau_end=1e100)))
        with self.assertRaises(ArithmeticError):
            simulate(Config.from_dict(config(K=1e308, Gamma=1e308)))


if __name__ == "__main__":
    unittest.main()
