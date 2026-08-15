// Hyperbezier mathematics adapted from linebender/spline.
// Copyright (c) 2020 Raph Levien; used under the MIT license.

#include "hyperbezier.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace adjacent
{
namespace
{
constexpr double pi = 3.141592653589793238462643383279502884;
constexpr double tau = 2.0 * pi;
constexpr std::array<std::array<double, 2>, 8> gl16 = { {
    { 0.09501250983763744, 0.1894506104550685 },
    { 0.2816035507792589, 0.1826034150449236 },
    { 0.4580167776572274, 0.16915651939500254 },
    { 0.6178762444026438, 0.14959598881657673 },
    { 0.7554044083550030, 0.12462897125553387 },
    { 0.8656312023878318, 0.09515851168249278 },
    { 0.9445750230732326, 0.062253523938647894 },
    { 0.9894009349916499, 0.027152459411754095 },
} };

double mod_tau(double value)
{
    value = std::fmod(value + pi, tau);
    if (value < 0.0)
        value += tau;
    return value - pi;
}

HyperPoint subtract(const HyperPoint& a, const HyperPoint& b)
{
    return { a[0] - b[0], a[1] - b[1] };
}

double length(const HyperPoint& value) { return std::hypot(value[0], value[1]); }
double angle(const HyperPoint& value) { return std::atan2(value[1], value[0]); }

double integrate_basis(double bias, double s)
{
    if (bias <= 1.0)
    {
        const double iy0 = 4.0 * s * s * s - 3.0 * s * s * s * s;
        const double iy1 = s * s;
        return iy0 + bias * (iy1 - iy0);
    }
    if (bias < 1.0002)
    {
        const double b = (bias - 1.0) * (4.0 / 3.0);
        return (1.0 - b) * s * s + b * s * s * s;
    }
    const double a = std::min(bias - 1.0, 1.0 - 1e-4);
    const double norm = 1.0 / (1.0 - a) + std::log1p(-a) - 1.0;
    const double q = 1.0 - a * s;
    return (1.0 / q + std::log(q) - 1.0) / norm;
}

double endpoint_curvature(double bias)
{
    if (bias <= 1.0)
        return 2.0 * bias;
    if (bias < 1.0007)
    {
        const double a = bias - 1.0;
        return 2.0 + 4.0 * a / 3.0 + 11.0 * a * a / 9.0;
    }
    const double a = std::min(bias - 1.0, 1.0 - 1e-4);
    const double reciprocal = a * a / (1.0 / (1.0 - a) + std::log1p(-a) - 1.0);
    return reciprocal / ((1.0 - a) * (1.0 - a));
}

double bias_for_theta(double theta)
{
    constexpr double euler_limit = 0.3 * pi;
    theta = std::abs(theta);
    if (theta < euler_limit)
        return 1.0;
    const double len = 1.0 - (theta - euler_limit) / (0.5 * pi - euler_limit);
    return std::clamp(2.0 - len * len, -0.9, 1.9999);
}
} // namespace

HyperBezier::HyperBezier(double k0_, double bias0_, double k1_, double bias1_)
    : k0(k0_), bias0(bias0_), k1(k1_), bias1(bias1_)
{
}

double HyperBezier::theta(double s) const
{
    return k1 * integrate_basis(bias1, s) - k0 * integrate_basis(bias0, 1.0 - s);
}

HyperPoint HyperBezier::integrate(double start, double end) const
{
    const double midpoint = 0.5 * (start + end);
    const double half = 0.5 * (end - start);
    HyperPoint result{ 0.0, 0.0 };
    for (const auto& coefficient : gl16)
    {
        for (double sign : { -1.0, 1.0 })
        {
            const double th = theta(midpoint + sign * half * coefficient[0]);
            result[0] += coefficient[1] * std::cos(th);
            result[1] += coefficient[1] * std::sin(th);
        }
    }
    result[0] *= half;
    result[1] *= half;
    return result;
}

HyperBezierResult HyperBezier::measure() const
{
    const auto vector = integrate(0.0, 1.0);
    const double chord_angle = angle(vector);
    const double chord = length(vector);
    return {
        chord_angle - theta(0.0),
        theta(1.0) - chord_angle,
        chord,
        chord * k0 * endpoint_curvature(bias0),
        chord * k1 * endpoint_curvature(bias1),
    };
}

HyperPoint HyperBezier::point(double s) const
{
    s = std::clamp(s, 0.0, 1.0);
    const auto raw = integrate(0.0, s);
    const auto full = integrate(0.0, 1.0);
    const double denominator = full[0] * full[0] + full[1] * full[1];
    if (denominator < 1e-20)
        return { s, 0.0 };
    return {
        (raw[0] * full[0] + raw[1] * full[1]) / denominator,
        (-raw[0] * full[1] + raw[1] * full[0]) / denominator,
    };
}

std::vector<HyperPoint> HyperBezier::samples(std::size_t count) const
{
    count = std::max<std::size_t>(1, count);
    std::vector<HyperPoint> result;
    result.reserve(count + 1);
    for (std::size_t i = 0; i <= count; ++i)
        result.push_back(point(static_cast<double>(i) / static_cast<double>(count)));
    return result;
}

HyperBezier HyperBezier::for_tangents(
    double theta0, double bias0, double theta1, double bias1)
{
    double delta_theta = 0.0;
    double previous_x = 0.0;
    double previous_error = 0.0;
    bool has_previous = false;
    HyperBezier candidate;
    for (std::size_t iteration = 0; iteration < 12; ++iteration)
    {
        candidate = HyperBezier(theta0 + 0.5 * delta_theta, bias0,
                                theta1 - 0.5 * delta_theta, bias1);
        const auto measured = candidate.measure();
        const double error = mod_tau(theta0 - theta1 - (measured.theta0 - measured.theta1));
        if (std::abs(error) < 1e-9)
            break;
        double inverse_slope = -0.5;
        if (has_previous && std::abs(error - previous_error) > 1e-12)
            inverse_slope = (delta_theta - previous_x) / (error - previous_error);
        previous_x = delta_theta;
        previous_error = error;
        has_previous = true;
        delta_theta -= inverse_slope * error;
    }
    return candidate;
}

std::array<double, 2> HyperBezier::parameters_for_arm(const HyperPoint& vector)
{
    const double theta = angle(vector);
    const double a = length(vector) * 1.5 * (std::cos(theta) + 1.0);
    const double bias = a < 1.0 ? 2.0 - a * a
                                : 1.0 + 2.0 * std::tanh(0.5 * (1.0 - a));
    return { theta, std::clamp(bias, -0.9, 1.9999) };
}

HyperBezier HyperBezier::from_control_points(const HyperPoint& p1, const HyperPoint& p2)
{
    const auto first = parameters_for_arm(p1);
    const auto second = parameters_for_arm({ 1.0 - p2[0], -p2[1] });
    return for_tangents(-first[0], first[1], second[0], second[1]);
}

HyperPoint HyperBezier::arm_for_parameters(double theta, double bias)
{
    double a;
    if (bias >= 1.0)
        a = std::sqrt(std::max(1e-8, 2.0 - bias));
    else
        a = 1.0 - 2.0 * std::atanh(0.5 * (bias - 1.0));
    const double arm_length = a / std::max(1e-8, 1.5 * (std::cos(theta) + 1.0));
    return { arm_length * std::cos(theta), arm_length * std::sin(theta) };
}

HyperPoint HyperSegment::world(const HyperPoint& value) const
{
    const auto delta = subtract(end, start);
    return {
        start[0] + delta[0] * value[0] - delta[1] * value[1],
        start[1] + delta[1] * value[0] + delta[0] * value[1],
    };
}

HyperPoint HyperSegment::point(double s) const { return world(curve.point(s)); }

std::vector<HyperPoint> HyperSegment::samples(std::size_t count) const
{
    count = std::max<std::size_t>(1, count);
    std::vector<HyperPoint> result;
    result.reserve(count + 1);
    for (std::size_t i = 0; i <= count; ++i)
        result.push_back(point(static_cast<double>(i) / static_cast<double>(count)));
    return result;
}

std::array<HyperPoint, 2> HyperSegment::auto_handles() const
{
    const auto first = HyperBezier::arm_for_parameters(theta0, curve.bias0);
    const auto second = HyperBezier::arm_for_parameters(-theta1, curve.bias1);
    return { world(first), world({ 1.0 - second[0], -second[1] }) };
}

std::array<double, 2> HyperSegment::endpoint_curvatures() const
{
    const auto result = curve.measure();
    const double scale = 1.0 / std::max(1e-12, length(subtract(end, start)));
    return { result.curvature0 * scale, result.curvature1 * scale };
}

AutoHyperSpline::AutoHyperSpline(const std::vector<HyperPoint>& points)
    : m_points(points), m_tangents(initial_tangents())
{
    solve();
}

std::vector<double> AutoHyperSpline::initial_tangents() const
{
    std::vector<double> result(m_points.size(), 0.0);
    if (m_points.size() < 2)
        return result;
    if (m_points.size() == 2)
    {
        const double tangent = angle(subtract(m_points[1], m_points[0]));
        return { tangent, tangent };
    }
    for (std::size_t i = 1; i + 1 < m_points.size(); ++i)
    {
        const double before = angle(subtract(m_points[i], m_points[i - 1]));
        const double after = angle(subtract(m_points[i + 1], m_points[i]));
        result[i] = before + 0.5 * mod_tau(after - before);
    }
    result.front() = angle(subtract(m_points[1], m_points[0]));
    result.back() = angle(subtract(m_points.back(), m_points[m_points.size() - 2]));
    return result;
}

HyperBezier AutoHyperSpline::curve_for_relative(double theta0, double theta1)
{
    return HyperBezier::for_tangents(
        -theta0, bias_for_theta(theta0), -theta1, bias_for_theta(theta1));
}

HyperSegment AutoHyperSpline::segment(std::size_t index) const
{
    const auto& start = m_points.at(index);
    const auto& end = m_points.at(index + 1);
    const double chord_angle = angle(subtract(end, start));
    const double theta0 = mod_tau(m_tangents[index] - chord_angle);
    const double theta1 = mod_tau(chord_angle - m_tangents[index + 1]);
    return { start, end, curve_for_relative(theta0, theta1), theta0, theta1 };
}

std::vector<HyperSegment> AutoHyperSpline::segments() const
{
    std::vector<HyperSegment> result;
    if (m_points.size() < 2)
        return result;
    result.reserve(m_points.size() - 1);
    for (std::size_t i = 0; i + 1 < m_points.size(); ++i)
        result.push_back(segment(i));
    return result;
}

double AutoHyperSpline::curvature_error(double left_length, const HyperBezierResult& left,
                                        double right_length, const HyperBezierResult& right)
{
    const double left_angle = std::atan(left.curvature1);
    const double right_angle = std::atan(right.curvature0);
    const double left_root = std::sqrt(left_length);
    const double right_root = std::sqrt(right_length);
    const double a0 = std::atan2(std::sin(left_angle) * right_root,
                                 std::cos(left_angle) * left_root);
    const double a1 = std::atan2(std::sin(right_angle) * left_root,
                                 std::cos(right_angle) * right_root);
    return a0 - a1;
}

void AutoHyperSpline::solve(std::size_t iterations)
{
    if (m_points.size() < 3)
        return;
    for (std::size_t iteration = 0; iteration < iterations; ++iteration)
    {
        auto first = segment(0);
        m_tangents.front() += 0.5 * std::sin(2.0 * first.theta1) - first.theta0;
        auto last = segment(m_points.size() - 2);
        m_tangents.back() -= 0.5 * std::sin(2.0 * last.theta0) - last.theta1;

        std::vector<double> changes;
        changes.reserve(m_points.size() - 2);
        for (std::size_t join = 0; join + 2 < m_points.size(); ++join)
        {
            const auto left = segment(join);
            const auto right = segment(join + 1);
            const double left_length = length(subtract(left.end, left.start));
            const double right_length = length(subtract(right.end, right.start));
            const double error = curvature_error(left_length, left.curve.measure(),
                                                 right_length, right.curve.measure());
            constexpr double epsilon = 1e-3;
            const auto left_perturbed = curve_for_relative(left.theta0, left.theta1 + epsilon);
            const auto right_perturbed = curve_for_relative(right.theta0 - epsilon, right.theta1);
            const double perturbed = curvature_error(left_length, left_perturbed.measure(),
                                                     right_length, right_perturbed.measure());
            const double derivative = (perturbed - error) / epsilon;
            changes.push_back(std::abs(derivative) > 1e-9 ? error / derivative : 0.0);
        }
        const double damping = std::tanh(0.25 * static_cast<double>(iteration + 1));
        for (std::size_t i = 0; i < changes.size(); ++i)
            m_tangents[i + 1] += damping * changes[i];
    }
}

void AutoHyperSpline::set_point(std::size_t index, const HyperPoint& value)
{
    if (index >= m_points.size())
        throw std::out_of_range("Hyper spline point index out of range");
    m_points[index] = value;
    m_tangents = initial_tangents();
    solve();
}

} // namespace adjacent
