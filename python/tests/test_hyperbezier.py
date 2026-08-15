import math
import unittest

from adjacent.hyperbezier import AutoHyperSpline, HyperBezier


class HyperBezierTests(unittest.TestCase):
    def test_endpoints_and_requested_tangents(self):
        curve = HyperBezier.for_tangents(-0.4, 1.0, 0.3, 1.0)
        self.assertEqual(curve.point(0.0), (0.0, 0.0))
        self.assertAlmostEqual(curve.point(1.0)[0], 1.0, places=12)
        self.assertAlmostEqual(curve.point(1.0)[1], 0.0, places=12)
        measured = curve.measure()
        self.assertAlmostEqual(measured.theta0, -0.4, places=7)
        self.assertAlmostEqual(measured.theta1, 0.3, places=7)

    def test_high_tension_stays_finite(self):
        curve = HyperBezier.for_tangents(-1.1, 1.8, -0.8, 1.6)
        for point in curve.samples(20):
            self.assertTrue(all(math.isfinite(value) for value in point))

    def test_auto_spline_is_g2_continuous(self):
        spline = AutoHyperSpline([(0, 0), (1, 2), (3, 1), (4, 3)])
        segments = spline.segments()
        for left, right in zip(segments, segments[1:]):
            self.assertAlmostEqual(left.endpoint_curvatures()[1],
                                   right.endpoint_curvatures()[0], places=6)

    def test_moving_on_curve_point_resolves_auto_points(self):
        spline = AutoHyperSpline([(0, 0), (1, 1), (2, 0)])
        before = spline.segments()[0].auto_handles()
        spline.set_point(1, (1, 2))
        after = spline.segments()[0].auto_handles()
        self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
