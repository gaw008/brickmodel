from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from pathlib import Path
import unittest
from sludge_sandbox.water_interval_eos import Interval, I, Jet, pressure_interval

ROOT = Path(__file__).parent/'fixtures/water-interval-primitives-v1'
SHA = 'a10a0da6c55e623cccc1f56a70cb348c772d8fc1710a6a142b459abb0dec4586'


class Intervals(unittest.TestCase):
    def inside(self, value, interval):
        self.assertLessEqual(F(interval.lo), F(value))
        self.assertLessEqual(F(value), F(interval.hi))

    def test_rational_corners_and_division(self):
        with localcontext() as ctx:
            ctx.prec = 12
            for aa in ((-9, -2), (-2, 3), (1, 7)):
                for bb in ((-8, -1), (2, 11)):
                    a = Interval(*map(D, aa)); b = Interval(*map(D, bb))
                    for x in aa:
                        for y in bb:
                            for value, out in ((F(x)+F(y), a+b), (F(x)-F(y), a-b),
                                               (F(x)*F(y), a*b), (F(x)/F(y), a/b)):
                                self.inside(value, out)
            with self.assertRaises(ValueError):
                I(1)/Interval(D(-1), D(1))

    def test_exp_log_against_higher_precision(self):
        for x in (D('0.123456789'), D(2), D(19)):
            with localcontext() as ctx:
                ctx.prec = 30
                e = I(x).exp(); log = I(x).ln()
            with localcontext() as ctx:
                ctx.prec = 90
                self.inside(x.exp(), e); self.inside(x.ln(), log)

    def test_jet_analytic_derivatives(self):
        with localcontext() as ctx:
            ctx.prec = 50
            x = Jet(I(9), I(1), I(0))
            root = x**D('0.5')
            self.inside(F(3), root.value)
            self.inside(F(1, 6), root.first)
            self.inside(-F(1, 108), root.second)
            poly = 3*x**4-2*x**2+7*x+1
            self.inside(3*9**4-2*9**2+7*9+1, poly.value)
            self.inside(12*9**3-4*9+7, poly.first)
            self.inside(36*9**2-4, poly.second)

    def test_water_rectangles_contain_dense_point_evaluations(self):
        for t0, rho0 in ((300, 55360), (305, 55250)):
            t = Interval(D(t0)-D('0.000001'), D(t0)+D('0.000001'))
            r = Interval(D(rho0)-D('0.000001'), D(rho0)+D('0.000001'))
            p, derivative = pressure_interval(ROOT/'heos-water.json', SHA, t, r)
            self.assertGreater(derivative.lo, 0)
            for tv in (t.lo, D(t0), t.hi):
                for rv in (r.lo, D(rho0), r.hi):
                    pp, dd = pressure_interval(ROOT/'heos-water.json', SHA, I(tv), I(rv), precision=90)
                    self.inside(pp.lo, p); self.inside(pp.hi, p)
                    self.inside(dd.lo, derivative); self.inside(dd.hi, derivative)

    def test_water_against_separate_iapws_scalar_formula(self):
        # This is scalar mathematical evaluation, never a flash/state/EOS solve.
        from iapws.iapws95 import IAPWS95, _phird
        import json
        e = json.loads((ROOT/'heos-water.json').read_bytes())[0]['EOS'][0]
        for t, rho in ((300., 55360.), (305., 55250.), (310., 55200.)):
            p, _ = pressure_interval(ROOT/'heos-water.json', SHA, I(t), I(rho))
            delta = rho/e['STATES']['reducing']['rhomolar']
            tau = e['STATES']['reducing']['T']/t
            scalar = rho*e['gas_constant']*t*(1+delta*_phird(tau, delta, IAPWS95._constants))
            self.assertLess(abs(float(p.lo)-scalar), 1e-4)

    def test_source_and_domain_rejections(self):
        with self.assertRaisesRegex(ValueError, 'source_bytes'):
            pressure_interval(ROOT/'heos-water.json', 'wrong', I(300), I(55000))
        with self.assertRaisesRegex(ValueError, 'positive_T'):
            pressure_interval(ROOT/'heos-water.json', SHA, I(0), I(55000))
        with self.assertRaises(ValueError):
            pressure_interval(ROOT/'heos-water.json', SHA, I(300), I(17873.72799560906))


if __name__ == '__main__':
    unittest.main()
