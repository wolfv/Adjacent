#ifndef ADJACENT_HYPERBEZIER_HPP
#define ADJACENT_HYPERBEZIER_HPP

#include <array>
#include <cstddef>
#include <vector>

namespace adjacent
{

using HyperPoint = std::array<double, 2>;

struct HyperBezierResult
{
    double theta0{};
    double theta1{};
    double chord{};
    double curvature0{};
    double curvature1{};
};

class HyperBezier
{
public:
    double k0{};
    double bias0{ 1.0 };
    double k1{};
    double bias1{ 1.0 };

    HyperBezier() = default;
    HyperBezier(double k0, double bias0, double k1, double bias1);

    double theta(double s) const;
    HyperPoint integrate(double start, double end) const;
    HyperBezierResult measure() const;
    HyperPoint point(double s) const;
    std::vector<HyperPoint> samples(std::size_t count = 64) const;

    static HyperBezier for_tangents(
        double theta0, double bias0, double theta1, double bias1);
    static HyperBezier from_control_points(const HyperPoint& p1, const HyperPoint& p2);
    static std::array<double, 2> parameters_for_arm(const HyperPoint& vector);
    static HyperPoint arm_for_parameters(double theta, double bias);
};

struct HyperSegment
{
    HyperPoint start{};
    HyperPoint end{};
    HyperBezier curve{};
    double theta0{};
    double theta1{};

    HyperPoint point(double s) const;
    std::vector<HyperPoint> samples(std::size_t count = 64) const;
    std::array<HyperPoint, 2> auto_handles() const;
    std::array<double, 2> endpoint_curvatures() const;

private:
    HyperPoint world(const HyperPoint& point) const;
};

class AutoHyperSpline
{
public:
    explicit AutoHyperSpline(const std::vector<HyperPoint>& points);

    const std::vector<HyperPoint>& points() const { return m_points; }
    const std::vector<double>& tangents() const { return m_tangents; }
    std::vector<HyperSegment> segments() const;
    void set_point(std::size_t index, const HyperPoint& point);
    void solve(std::size_t iterations = 12);

private:
    std::vector<HyperPoint> m_points;
    std::vector<double> m_tangents;

    std::vector<double> initial_tangents() const;
    HyperSegment segment(std::size_t index) const;
    static HyperBezier curve_for_relative(double theta0, double theta1);
    static double curvature_error(double left_length, const HyperBezierResult& left,
                                  double right_length, const HyperBezierResult& right);
};

} // namespace adjacent

#endif
