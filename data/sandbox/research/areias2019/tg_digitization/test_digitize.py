"""Small numerical regressions for the coordinate converter; no EOS or fitting."""

from decimal import ROUND_CEILING, ROUND_FLOOR
from fractions import Fraction as F
import unittest

from digitize import axis_interval, decimal


class CoordinateTests(unittest.TestCase):
    def test_tiny_offsets_do_not_round_intervals_inward(self):
        tiny = F(1, 10**100)
        for center in (F(-1), F(0), F(1)):
            for value in (center - tiny, center + tiny):
                with self.subTest(value=value):
                    lower = F(decimal(value, ROUND_FLOOR))
                    upper = F(decimal(value, ROUND_CEILING))
                    self.assertLessEqual(lower, value)
                    self.assertGreaterEqual(upper, value)
                    self.assertEqual(upper - lower, F(1, 100))

    def test_exact_cents_are_not_widened(self):
        for value in (F(-123, 100), F(0), F(9876, 100)):
            self.assertEqual(F(decimal(value, ROUND_FLOOR)), value)
            self.assertEqual(F(decimal(value, ROUND_CEILING)), value)

    def test_nominal_halfway_rounds_to_even(self):
        for value, expected in ((F(1, 200), "0.00"), (F(3, 200), "0.02"),
                                (F(-1, 200), "0.00"), (F(-3, 200), "-0.02")):
            self.assertEqual(decimal(value), expected)

    def test_known_linear_center_interval(self):
        axis = {"ticks": [{"pixel_center": str(p), "value": str(p),
                           "conditional_pixel_halfwidth": "1"} for p in (0, 50, 100)],
                "max_abs_tick_residual_exact": "0"}
        # At the center, worst shifts are point +/-2 and both tick centers -/+1.
        self.assertEqual(axis_interval(F(50), axis), (F(50), F(47), F(53)))


if __name__ == "__main__":
    unittest.main()
