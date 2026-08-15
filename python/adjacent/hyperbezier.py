"""Experimental hyperbezier curves and automatic G2 splines.

This is a Python adaptation of the mathematics in linebender/spline, originally
Copyright (c) 2020 Raph Levien and licensed under MIT/Apache-2.0. See
HYPERBEZIER_LICENSE-MIT. It lives on the experimental branch while the API and
its integration with Adjacent's symbolic solver are evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

# Positive half of the 16-point Gauss-Legendre rule.
_GL16 = (
    (0.09501250983763744, 0.1894506104550685),
    (0.2816035507792589, 0.1826034150449236),
    (0.4580167776572274, 0.16915651939500254),
    (0.6178762444026438, 0.14959598881657673),
    (0.755404408355003, 0.12462897125553387),
    (0.8656312023878318, 0.09515851168249278),
    (0.9445750230732326, 0.062253523938647894),
    (0.9894009349916499, 0.027152459411754095),
)
_TAU = 2.0 * math.pi


def _mod_tau(value):
    return (value + math.pi) % _TAU - math.pi


def _add(a, b):
    return a[0] + b[0], a[1] + b[1]


def _sub(a, b):
    return a[0] - b[0], a[1] - b[1]


def _mul(value, scale):
    return value[0] * scale, value[1] * scale


def _length(value):
    return math.hypot(*value)


def _angle(value):
    return math.atan2(value[1], value[0])


def _integrate_basis(bias, s):
    """Normalized integral of one endpoint's curvature basis."""
    if bias <= 1.0:
        iy0 = 4.0 * s**3 - 3.0 * s**4
        iy1 = s * s
        return iy0 + bias * (iy1 - iy0)
    if bias < 1.0002:
        b = (bias - 1.0) * (4.0 / 3.0)
        return (1.0 - b) * s * s + b * s**3
    a = min(bias - 1.0, 1.0 - 1e-4)
    norm = 1.0 / (1.0 - a) + math.log1p(-a) - 1.0
    q = 1.0 - a * s
    return (1.0 / q + math.log(q) - 1.0) / norm


def _endpoint_curvature(bias):
    if bias <= 1.0:
        return 2.0 * bias
    if bias < 1.0007:
        a = bias - 1.0
        return 2.0 + 4.0 * a / 3.0 + 11.0 * a * a / 9.0
    a = min(bias - 1.0, 1.0 - 1e-4)
    reciprocal_integral = a * a / (1.0 / (1.0 - a) + math.log1p(-a) - 1.0)
    return reciprocal_integral / (1.0 - a) ** 2


def _bias_for_theta(theta):
    euler_limit = 0.3 * math.pi
    theta = abs(theta)
    if theta < euler_limit:
        return 1.0
    length = 1.0 - (theta - euler_limit) / (0.5 * math.pi - euler_limit)
    return max(-0.9, min(1.9999, 2.0 - length * length))


@dataclass(frozen=True)
class HyperBezierResult:
    theta0: float
    theta1: float
    chord: float
    curvature0: float
    curvature1: float


@dataclass
class HyperBezier:
    """Unit hyperbezier parameterized by endpoint curvature and tension."""

    k0: float
    bias0: float
    k1: float
    bias1: float

    def theta(self, s):
        return (self.k1 * _integrate_basis(self.bias1, s)
                - self.k0 * _integrate_basis(self.bias0, 1.0 - s))

    def integrate(self, start, end):
        midpoint = 0.5 * (start + end)
        half = 0.5 * (end - start)
        x = y = 0.0
        for node, weight in _GL16:
            for sign in (-1.0, 1.0):
                theta = self.theta(midpoint + sign * half * node)
                x += weight * math.cos(theta)
                y += weight * math.sin(theta)
        return half * x, half * y

    def measure(self):
        chord_vector = self.integrate(0.0, 1.0)
        chord_angle = _angle(chord_vector)
        chord = _length(chord_vector)
        return HyperBezierResult(
            chord_angle - self.theta(0.0),
            self.theta(1.0) - chord_angle,
            chord,
            chord * self.k0 * _endpoint_curvature(self.bias0),
            chord * self.k1 * _endpoint_curvature(self.bias1),
        )

    @classmethod
    def for_tangents(cls, theta0, bias0, theta1, bias1):
        """Solve endpoint curvature contributions for tangent angles."""
        delta_theta = 0.0
        previous = None
        candidate = None
        for _ in range(12):
            candidate = cls(theta0 + 0.5 * delta_theta, bias0,
                            theta1 - 0.5 * delta_theta, bias1)
            measured = candidate.measure()
            error = _mod_tau(theta0 - theta1 - (measured.theta0 - measured.theta1))
            if abs(error) < 1e-9:
                break
            if previous is None:
                slope_inverse = -0.5
            else:
                denominator = error - previous[1]
                slope_inverse = ((delta_theta - previous[0]) / denominator
                                 if abs(denominator) > 1e-12 else -0.5)
            previous = delta_theta, error
            delta_theta -= slope_inverse * error
        return candidate

    @classmethod
    def from_control_points(cls, p1, p2):
        """Construct from cubic-like controls in the unit chord coordinate system."""
        theta0, bias0 = cls.parameters_for_arm(p1)
        theta1, bias1 = cls.parameters_for_arm((1.0 - p2[0], -p2[1]))
        return cls.for_tangents(-theta0, bias0, theta1, bias1)

    @staticmethod
    def parameters_for_arm(vector):
        theta = _angle(vector)
        a = _length(vector) * 1.5 * (math.cos(theta) + 1.0)
        bias = 2.0 - a * a if a < 1.0 else 1.0 + 2.0 * math.tanh(0.5 * (1.0 - a))
        return theta, max(-0.9, min(1.9999, bias))

    @staticmethod
    def arm_for_parameters(theta, bias):
        if bias >= 1.0:
            a = math.sqrt(max(1e-8, 2.0 - bias))
        else:
            a = 1.0 - 2.0 * math.atanh(0.5 * (bias - 1.0))
        length = a / max(1e-8, 1.5 * (math.cos(theta) + 1.0))
        return length * math.cos(theta), length * math.sin(theta)

    def point(self, s):
        """Evaluate in unit-chord coordinates, with exact (0,0)/(1,0) endpoints."""
        raw = self.integrate(0.0, max(0.0, min(1.0, s)))
        full = self.integrate(0.0, 1.0)
        denominator = full[0] ** 2 + full[1] ** 2
        return ((raw[0] * full[0] + raw[1] * full[1]) / denominator,
                (-raw[0] * full[1] + raw[1] * full[0]) / denominator)

    def samples(self, count=64):
        return [self.point(i / count) for i in range(count + 1)]


@dataclass
class HyperSegment:
    start: tuple[float, float]
    end: tuple[float, float]
    curve: HyperBezier
    theta0: float
    theta1: float

    def _world(self, point):
        delta = _sub(self.end, self.start)
        return (self.start[0] + delta[0] * point[0] - delta[1] * point[1],
                self.start[1] + delta[1] * point[0] + delta[0] * point[1])

    def point(self, s):
        return self._world(self.curve.point(s))

    def samples(self, count=64):
        return [self.point(i / count) for i in range(count + 1)]

    def auto_handles(self):
        first = HyperBezier.arm_for_parameters(self.theta0, self.curve.bias0)
        second = HyperBezier.arm_for_parameters(-self.theta1, self.curve.bias1)
        return self._world(first), self._world((1.0 - second[0], -second[1]))

    def endpoint_curvatures(self):
        result = self.curve.measure()
        scale = 1.0 / max(1e-12, _length(_sub(self.end, self.start)))
        return result.curvature0 * scale, result.curvature1 * scale


class AutoHyperSpline:
    """An open interpolating hyperbezier spline with automatically solved G2 joins."""

    def __init__(self, points):
        self.points = [tuple(map(float, point)) for point in points]
        self.tangents = self._initial_tangents()
        self.solve()

    def _initial_tangents(self):
        count = len(self.points)
        if count < 2:
            return [0.0] * count
        tangents = [0.0] * count
        if count == 2:
            angle = _angle(_sub(self.points[1], self.points[0]))
            return [angle, angle]
        for i in range(1, count - 1):
            before = _angle(_sub(self.points[i], self.points[i - 1]))
            after = _angle(_sub(self.points[i + 1], self.points[i]))
            tangents[i] = before + 0.5 * _mod_tau(after - before)
        tangents[0] = _angle(_sub(self.points[1], self.points[0]))
        tangents[-1] = _angle(_sub(self.points[-1], self.points[-2]))
        return tangents

    def _segment(self, index):
        start, end = self.points[index:index + 2]
        chord_angle = _angle(_sub(end, start))
        theta0 = _mod_tau(self.tangents[index] - chord_angle)
        theta1 = _mod_tau(chord_angle - self.tangents[index + 1])
        curve = HyperBezier.for_tangents(-theta0, _bias_for_theta(theta0),
                                         -theta1, _bias_for_theta(theta1))
        return HyperSegment(start, end, curve, theta0, theta1)

    def segments(self):
        return [self._segment(i) for i in range(len(self.points) - 1)]

    @staticmethod
    def _curve_for_relative(theta0, theta1):
        return HyperBezier.for_tangents(-theta0, _bias_for_theta(theta0),
                                         -theta1, _bias_for_theta(theta1))

    @staticmethod
    def _curvature_error(left_length, left_result, right_length, right_result):
        # Compare curvature after scaling both chords by their geometric mean.
        left_angle = math.atan(left_result.curvature1)
        right_angle = math.atan(right_result.curvature0)
        left_root = math.sqrt(left_length)
        right_root = math.sqrt(right_length)
        a0 = math.atan2(math.sin(left_angle) * right_root,
                        math.cos(left_angle) * left_root)
        a1 = math.atan2(math.sin(right_angle) * left_root,
                        math.cos(right_angle) * right_root)
        return a0 - a1

    def solve(self, iterations=12):
        if len(self.points) < 3:
            return
        for iteration in range(iterations):
            # Natural endpoint tangents, matching the reference simple spline.
            first = self._segment(0)
            self.tangents[0] += 0.5 * math.sin(2.0 * first.theta1) - first.theta0
            last = self._segment(len(self.points) - 2)
            self.tangents[-1] -= 0.5 * math.sin(2.0 * last.theta0) - last.theta1

            changes = []
            for join in range(len(self.points) - 2):
                left = self._segment(join)
                right = self._segment(join + 1)
                left_length = _length(_sub(left.end, left.start))
                right_length = _length(_sub(right.end, right.start))
                error = self._curvature_error(left_length, left.curve.measure(),
                                               right_length, right.curve.measure())

                epsilon = 1e-3
                left_perturbed = self._curve_for_relative(left.theta0,
                                                          left.theta1 + epsilon)
                right_perturbed = self._curve_for_relative(right.theta0 - epsilon,
                                                           right.theta1)
                perturbed_error = self._curvature_error(
                    left_length, left_perturbed.measure(),
                    right_length, right_perturbed.measure())
                derivative = (perturbed_error - error) / epsilon
                changes.append(error / derivative if abs(derivative) > 1e-9 else 0.0)

            damping = math.tanh(0.25 * (iteration + 1))
            for index, change in enumerate(changes, 1):
                self.tangents[index] += damping * change

    def set_point(self, index, point):
        self.points[index] = tuple(map(float, point))
        self.tangents = self._initial_tangents()
        self.solve()
