"""Focused offline tests; no legacy solver or scientific dependencies."""
import importlib.util
import json
import math
import unittest


def config(**changes):
    data = dict(schema_version=1,
                scope="dimensionless_reaction_transport_benchmark",
                scenario_id="test", K=1.0, Gamma=2.0, Bi=1.0,
                boundary_mode="infinite", reservoir_ratio=None,
                n_cells=15, tau_end=20.0, diagnostic_thresholds=[0.95, 0.99])
    data.update(changes)
    return data


class ConfigTests(unittest.TestCase):
    def test_strict_dimensionless_contract(self):
        self.assertIsNotNone(importlib.util.find_spec("model"), "B1 model not implemented")
        from model import Config
        self.assertEqual(Config.from_dict(config()).Gamma, 2)
        self.assertEqual(Config.from_dict(config(boundary_mode="sealed")).reservoir_ratio, None)
        self.assertEqual(Config.from_dict(config(boundary_mode="finite", reservoir_ratio=.25)).reservoir_ratio, .25)
        invalid = [dict(K=-1), dict(Gamma=0), dict(Bi=-1), dict(tau_end=0),
                   dict(n_cells=1), dict(n_cells=7.5), dict(n_cells=True),
                   dict(reservoir_ratio=1), dict(boundary_mode="finite"),
                   dict(boundary_mode="sealed", reservoir_ratio=1),
                   dict(boundary_mode="dirichlet"), dict(scope="recipe"),
                   dict(schema_version=True), dict(schema_version=2),
                   dict(diagnostic_thresholds=[.9, .99]), dict(K=True),
                   dict(scenario_id="../escape"), dict(tolerance=1),
                   dict(K="1"), dict(Gamma=float("inf")), dict(Bi=float("nan"))]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                Config.from_dict(config(**change))
        for key in config():
            data = config()
            del data[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                Config.from_dict(data)
        with self.assertRaises(ValueError):
            Config.from_json('{"K":1,"K":2}')
        with self.assertRaises(ValueError):
            Config.from_json(json.dumps(config(K=float("nan"))))


class SolverTests(unittest.TestCase):
    def test_robin_half_cell_sign_and_reservoir_never_resets(self):
        from model import Config
        from solver import State, boundary_flux, conductance, simulate, surface_oxygen
        cfg = Config.from_dict(config(n_cells=7, boundary_mode="finite", reservoir_ratio=.25))
        g = conductance(cfg.Bi, 1/7)
        state = State([.2]*7, [.8]*7, [1.0]*7, u_res=.6, v_res=.4)
        ju, jv = boundary_flux(state, cfg, g)
        self.assertLess(ju, 0)
        self.assertGreater(jv, 0)
        self.assertAlmostEqual(ju, cfg.Bi*(surface_oxygen(state, cfg)-.6))
        # Reverse exchange is supported, not clamped to outward-only flux.
        state.u_res, state.v_res = .1, .9
        self.assertGreater(boundary_flux(state, cfg, g)[0], 0)
        result = simulate(cfg)
        for record in result.records:
            s = record.state
            assert s.u_res is not None and s.v_res is not None
            self.assertAlmostEqual(sum(s.u)/7 + s.generated + s.net_u, 1, places=10)
            self.assertAlmostEqual(sum(s.v)/7 + s.net_v, s.generated, places=10)
            self.assertAlmostEqual(.25*(s.u_res-1), s.net_u, places=10)
            self.assertAlmostEqual(.25*s.v_res, s.net_v, places=10)
            self.assertAlmostEqual(s.u_res+s.v_res, 1, places=11)
        last_u_res = result.records[-1].state.u_res
        assert last_u_res is not None
        self.assertLess(last_u_res, .01)
        self.assertGreaterEqual(sum(result.records[-1].state.f)/7, .375-1e-10)

    def test_no_reaction_and_zero_film_are_exact_invariant_cases(self):
        from model import Config
        from solver import simulate
        for mode, rho in (("infinite", None), ("sealed", None), ("finite", 1)):
            cfg = Config.from_dict(config(K=0, n_cells=7, tau_end=1, boundary_mode=mode, reservoir_ratio=rho))
            state = simulate(cfg).records[-1].state
            self.assertEqual(state.u, [1]*7)
            self.assertEqual(state.v, [0]*7)
            self.assertEqual(state.f, [1]*7)
            self.assertEqual(state.generated, 0)
        cfg = Config.from_dict(config(Bi=0, n_cells=7, tau_end=1))
        state = simulate(cfg).records[-1].state
        self.assertEqual(state.net_u, 0)
        self.assertEqual(state.net_v, 0)

    def test_independent_dirichlet_diffusion_series_cell_averages(self):
        import solver
        from model import Config
        self.assertTrue(hasattr(solver, "simulate_diffusion_test"), "explicit diffusion-test mode absent")
        errors = []
        for n in (7, 15, 31):
            cfg = Config.from_dict(config(K=0, n_cells=n, tau_end=.2))
            result = solver.simulate_diffusion_test(cfg, boundary="dirichlet_limit")
            expected = []
            for i in range(n):
                # Initial u=0, core Neumann, surface u=1; Fourier cell average.
                deficit = 0
                for m in range(80):
                    lam = (m+.5)*math.pi
                    avg_cos = n*(math.sin(lam*(i+1)/n)-math.sin(lam*i/n))/lam
                    deficit += 2*(-1)**m/lam*avg_cos*math.exp(-lam*lam*.2)
                expected.append(1-deficit)
            actual = result.records[-1].state.u
            errors.append(max(abs(a-b) for a, b in zip(actual, expected)))
        self.assertLess(errors[2], 3e-4)
        self.assertLess(errors[1], errors[0]/3)
        self.assertLess(errors[2], errors[1]/3)

    def test_closed_reaction_preserves_stoichiometry_and_oxygen_limit(self):
        self.assertIsNotNone(importlib.util.find_spec("solver"), "B1 solver not implemented")
        from model import Config
        from solver import simulate
        for gamma in (.25, 2):
            cfg = Config.from_dict(config(boundary_mode="sealed", Gamma=gamma, n_cells=7))
            result = simulate(cfg)
            for record in result.records:
                state = record.state
                for u, v, f in zip(state.u, state.v, state.f):
                    self.assertGreaterEqual(min(u, v, f), 0)
                    self.assertLessEqual(f, 1)
                    self.assertAlmostEqual(u + v, 1, places=11)
                    self.assertAlmostEqual(gamma * f + v, gamma, places=11)
                    self.assertAlmostEqual(1 - u, v, places=11)
                self.assertEqual(state.net_u, 0)
                self.assertEqual(state.net_v, 0)
                self.assertAlmostEqual(state.generated, gamma * (1-sum(state.f)/7), places=11)
            burned = 1 - sum(result.records[-1].state.f)/7
            self.assertLessEqual(burned, min(1, 1/gamma) + 1e-12)
            self.assertAlmostEqual(burned, min(1, 1/gamma), delta=1e-5)


if __name__ == "__main__":
    unittest.main()
